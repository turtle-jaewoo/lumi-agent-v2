"""
LangGraph 그래프의 조건부 라우팅 로직

엣지(Edge)는 노드 간의 연결을 정의합니다.
조건부 엣지는 상태에 따라 다른 노드로 분기합니다.

이 파일에서 정의하는 엣지:
    - route_by_intent: Router 노드 이후 의도에 따른 분기
"""

from typing import Literal

from loguru import logger

from app.graph.state import LumiState


def route_by_intent(state: LumiState) -> Literal["rag", "tool", "response"]:
    """
    🔀 의도에 따른 조건부 라우팅

    Router 노드에서 결정된 intent에 따라
    다음 노드를 결정합니다.

    라우팅 규칙:
        - intent == "chat" -> "response" (바로 응답 생성)
        - intent == "rag"  -> "rag" (문서 검색 후 응답)
        - intent == "tool" -> "tool" (Tool 실행 후 응답)

    Args:
        state: 현재 에이전트 상태

    Returns:
        str: 다음 노드 이름 ("rag", "tool", "response" 중 하나)

    Example:
        >>> state = {"intent": "tool", ...}
        >>> next_node = route_by_intent(state)
        >>> print(next_node)
        'tool'
    """
    intent = state.get("intent", "chat")

    logger.debug(f"🔀 [Edge] 라우팅 결정: intent={intent}")

    if intent == "rag":
        logger.info("🔀 [Edge] -> RAG 노드로 이동")
        return "rag"
    elif intent == "tool":
        logger.info("🔀 [Edge] -> Tool 노드로 이동")
        return "tool"
    else:
        # chat 또는 기타 -> 바로 응답 생성
        logger.info("🔀 [Edge] -> Response 노드로 이동")
        return "response"
