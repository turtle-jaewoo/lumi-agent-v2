"""
LangGraph 그래프의 노드(Node) 정의

노드는 그래프에서 실제 작업을 수행하는 단위입니다.
각 노드는 State를 받아서 업데이트할 필드만 반환합니다.

이 파일에서 정의하는 노드:
    1. router_node: 사용자 의도 분류 (chat/rag/tool)
    2. rag_node: 문서 검색 및 컨텍스트 생성
    3. tool_node: Tool 실행
    4. response_node: 최종 응답 생성
"""

import json
from datetime import datetime
from typing import Literal

from langchain_core.messages import AIMessage, HumanMessage
from langchain_upstage import ChatUpstage
from loguru import logger
from pydantic import BaseModel, Field

from app.core.config import settings
from app.core.prompts import RAG_RESPONSE_PROMPT, RESPONSE_PROMPT, ROUTER_PROMPT
from app.graph.state import LumiState
from app.repositories.rag import get_rag_repository
from app.tools.executor import ToolExecutor


class RouterOutput(BaseModel):
    """
    라우터 노드의 출력 스키마

    LLM이 JSON 파싱 없이 직접 이 형식으로 응답합니다.
    with_structured_output()을 사용하면 자동으로 파싱됩니다.
    """

    intent: Literal["chat", "rag", "tool"] = Field(
        description="사용자 의도: chat(일반대화), rag(정보검색), tool(도구실행)"
    )
    tool_name: str | None = Field(
        default=None, description="실행할 도구 이름 (intent=tool일 때만)"
    )
    tool_args: dict | None = Field(
        default=None, description="도구 실행 인자 (intent=tool일 때만)"
    )


def get_llm() -> ChatUpstage:
    """
    Upstage Solar LLM 클라이언트를 반환합니다.

    Returns:
        ChatUpstage: Upstage Solar LLM 클라이언트
    """
    return ChatUpstage(
        api_key=settings.upstage_api_key,
        model=settings.llm_model,
        timeout=30,
        max_retries=2,
    )


tool_executor = ToolExecutor()


# ============================================================
# 🔀 Router Node: 사용자 의도 분류
# ============================================================
async def router_node(state: LumiState) -> dict:
    """
    🔀 라우터 노드: 사용자 의도를 분류

    사용자의 마지막 메시지를 분석하여 의도를 분류합니다.
    with_structured_output()을 사용하여 JSON 파싱 없이 바로 Pydantic 모델로 받습니다.

    분류 결과:
        - chat: 일반 대화 -> 바로 response 노드로
        - rag: 정보 검색 -> RAG 노드로
        - tool: 도구 실행 -> Tool 노드로

    Args:
        state: 현재 에이전트 상태

    Returns:
        dict: 업데이트할 상태 필드
            - intent: 분류된 의도
            - tool_name: Tool 이름 (intent가 tool인 경우)
            - tool_args: Tool 인자 (intent가 tool인 경우)
    """
    logger.info("🔀 [Router] 의도 분류 시작")

    # Step 1: 마지막 사용자 메시지 추출
    last_message = state["messages"][-1]
    user_input = last_message.content
    logger.debug(f"사용자 입력: {user_input}")

    # Step 2: LLM에 with_structured_output 적용
    # Pydantic 스키마로 자동 파싱 - JSON 수동 파싱 불필요!
    llm = get_llm()
    structured_llm = llm.with_structured_output(RouterOutput)

    # 현재 날짜 정보 추가 (스케줄 조회 시 필요)
    current_date = datetime.now().strftime("%Y-%m-%d")

    messages = [
        HumanMessage(content=f"오늘 날짜: {current_date}\n\n{ROUTER_PROMPT}"),
        HumanMessage(content=f"사용자: {user_input}"),
    ]

    try:
        # with_structured_output 덕분에 result가 RouterOutput 타입!
        result = await structured_llm.ainvoke(messages)

        # tool_name 정리 (따옴표, 여러 도구 나열된 경우 첫 번째만)
        tool_name = result.tool_name
        if tool_name:
            # 🔧 수정: 비정상적으로 긴 tool_name 필터링 (LLM 오작동 방지)
            if len(tool_name) > 50:
                logger.warning(f"⚠️ tool_name이 너무 김 ({len(tool_name)}자), 무시")
                tool_name = None
            else:
                # 🔧 수정: 일반 따옴표 + 유니코드 따옴표 모두 제거
                # LLM이 가끔 유니코드 따옴표('', "", '')를 반환함
                tool_name = tool_name.strip()
                # 다양한 따옴표 문자 제거 (일반 + 유니코드)
                quote_chars = "'\"`'''\"\"「」『』"
                tool_name = tool_name.strip(quote_chars)
                # 중간에 있는 따옴표도 제거 (예: get_schedule')
                for char in quote_chars:
                    tool_name = tool_name.replace(char, "")
                # 쉼표로 나열된 경우 첫 번째만 사용
                if "," in tool_name:
                    tool_name = tool_name.split(",")[0].strip()
                # "tool1?tool2?tool3" 형태면 첫 번째만 사용
                if "?" in tool_name:
                    tool_name = tool_name.split("?")[0].strip()

        # 유효한 tool 목록
        valid_tools = [
            "get_schedule",
            "send_fan_letter",
            "recommend_song",
            "get_weather",
        ]

        # intent가 tool인데 tool_name이 없거나 유효하지 않으면 chat으로 전환
        result_intent = result.intent

        if result_intent == "tool":
            if not tool_name:
                logger.warning("⚠️ intent=tool인데 tool_name이 없음, chat으로 전환")
                result_intent = "chat"
            elif tool_name not in valid_tools:
                logger.warning(f"⚠️ 유효하지 않은 Tool: {tool_name}, chat으로 전환")
                tool_name = None
                result_intent = "chat"

        logger.info(f"🔀 [Router] 의도: {result_intent}, Tool: {tool_name}")

        return {
            "intent": result_intent,
            "tool_name": tool_name,
            "tool_args": result.tool_args,
        }

    except Exception as e:
        logger.warning(f"Router 노드 오류: {e}, 기본값(chat)으로 설정")
        return {
            "intent": "chat",
            "tool_name": None,
            "tool_args": None,
        }


# ============================================================
# 📚 RAG Node: 문서 검색 (실제 구현)
# ============================================================
async def rag_node(state: LumiState) -> dict:
    """
    📚 RAG 노드: 관련 문서 검색

    실제 Supabase pgvector를 사용한 RAG 구현
    - 활성 문서(v2.5)만 검색하여 폐기 문서(v1.0) 제외
    - 메타데이터 필터링으로 세계관 일관성 유지

    Args:
        state: 현재 에이전트 상태

    Returns:
        dict: 업데이트할 상태 필드
            - retrieved_docs: 검색된 문서 내용 목록
    """
    logger.info("📚 [RAG] 문서 검색 시작")

    last_message = state["messages"][-1]
    user_input = last_message.content

    try:
        # RAG Repository로 실제 검색
        rag_repo = get_rag_repository()

        # 핵심: filter_status="active"로 폐기 문서 제외!
        # 이게 없으면 v1.0(뱀파이어 설정)이 섞여서 세계관 붕괴
        docs = await rag_repo.search_similar(
            query=user_input,
            k=3,
            filter_status="active",  # v2.5만 검색!
        )

        # 검색 결과에서 content만 추출
        retrieved_docs = [doc["content"] for doc in docs]

        # 검색 결과 로깅 (디버깅용)
        for i, doc in enumerate(docs):
            version = doc.get("metadata", {}).get("version", "?")
            similarity = doc.get("similarity", 0)
            logger.debug(
                f"  [{i + 1}] v{version} (sim: {similarity:.3f}): {doc['content'][:50]}..."
            )

        logger.info(f"📚 [RAG] 검색 완료: {len(retrieved_docs)}개 문서")

    except Exception as e:
        logger.error(f"📚 [RAG] 검색 실패: {e}")
        # Fallback: 기본 정보 제공
        retrieved_docs = [
            "루미는 프리즘 행성 출신 외계인 공주야.",
            "루미의 팬덤은 '루미너스(Luminous)'야!",
        ]

    return {
        "retrieved_docs": retrieved_docs,
    }


# ============================================================
# 🔧 Tool Node: Tool 실행
# ============================================================
async def tool_node(state: LumiState) -> dict:
    """
    🔧 Tool 노드: Tool 실행

    Router에서 결정된 Tool을 실행합니다.

    Args:
        state: 현재 에이전트 상태

    Returns:
        dict: 업데이트할 상태 필드
            - tool_result: Tool 실행 결과
    """
    tool_name = state["tool_name"]
    tool_args = state["tool_args"] or {}

    # 🔧 방어 코드: tool_name이 None이면 에러 반환
    if not tool_name:
        logger.error("🔧 [Tool] tool_name이 None! (라우터 오류)")
        return {
            "tool_result": {
                "success": False,
                "error": "Tool 이름이 지정되지 않았어요.",
            },
        }

    logger.info(f"🔧 [Tool] Tool 실행: {tool_name}")

    # ToolExecutor를 사용하여 Tool 실행
    result = await tool_executor.execute(
        tool_name=tool_name,
        tool_args=tool_args,
        session_id=state["session_id"],
        user_id=state.get("user_id"),
    )

    logger.info(f"🔧 [Tool] 실행 결과: {result}")

    return {
        "tool_result": result,
    }


# ============================================================
# 💬 Response Node: 최종 응답 생성
# ============================================================
async def response_node(state: LumiState) -> dict:
    """
    💬 응답 노드: 최종 응답 생성

    라우팅 결과에 따라 적절한 응답을 생성합니다:
        - chat: 일반 대화 응답
        - rag: 검색된 문서 기반 응답
        - tool: Tool 결과 기반 응답

    Args:
        state: 현재 에이전트 상태

    Returns:
        dict: 업데이트할 상태 필드
            - messages: AI 응답 메시지 추가
    """
    logger.info(f"💬 [Response] 응답 생성 시작 (intent: {state['intent']})")

    llm = get_llm()
    last_message = state["messages"][-1]
    user_input = last_message.content

    # 의도에 따른 프롬프트 구성
    intent = state["intent"]

    if intent == "rag":
        # RAG 응답: 검색된 문서 컨텍스트 포함
        context = "\n".join(state["retrieved_docs"])
        system_prompt = RAG_RESPONSE_PROMPT.format(context=context)

    elif intent == "tool":
        # Tool 응답: Tool 실행 결과 포함
        tool_result = state["tool_result"]
        tool_name = state["tool_name"]  # noqa: F841

        # Tool 결과를 자연스러운 응답으로 변환하기 위한 컨텍스트
        result_context = f"""
## 📋 조회 결과 (내부 참고용, 절대 그대로 출력하지 마!)
{json.dumps(tool_result, ensure_ascii=False, indent=2)}

## 규칙
- 위 결과를 바탕으로 루미답게 친근하게 안내해줘
- 성공한 경우: 결과를 자연스럽게 전달 (예: "이번 주 금요일에 뮤직뱅크 나와!")
- 실패한 경우: 부드럽게 안내 (예: "흠, 지금은 일정이 없나봐!")
- ❌ "get_schedule", "tool", "실행 결과" 같은 기술 용어 절대 금지!
"""
        system_prompt = RESPONSE_PROMPT + result_context

    else:
        # 일반 대화 응답
        system_prompt = RESPONSE_PROMPT

    # 🔧 수정: 대화 히스토리를 LLM에 전달하여 과거 질문 기억
    # 최근 6개 메시지 (3턴: user+ai 쌍)를 히스토리로 포함
    # 마지막 메시지(현재 질문)는 별도로 추가하므로 제외
    history_messages = state["messages"][:-1][-6:] if len(state["messages"]) > 1 else []

    # 히스토리를 텍스트로 변환
    history_text = ""
    if history_messages:
        history_parts = []
        for msg in history_messages:
            role = "사용자" if isinstance(msg, HumanMessage) else "루미"
            history_parts.append(f"{role}: {msg.content}")
        history_text = "\n".join(history_parts)
        history_text = f"\n\n## 이전 대화:\n{history_text}\n"

    # LLM 호출 (히스토리 포함)
    messages = [
        HumanMessage(content=system_prompt + history_text),
        HumanMessage(content=f"사용자: {user_input}"),
    ]

    try:
        response = await llm.ainvoke(messages)
        ai_response = response.content

        logger.info("💬 [Response] 응답 생성 완료")

    except Exception as e:
        logger.error(f"응답 생성 오류: {e}")
        ai_response = "미안해, 지금 잠깐 문제가 생겼어! 다시 말해줄래? 😅"

    # AI 응답을 messages에 추가
    return {
        "messages": [AIMessage(content=ai_response)],
    }
