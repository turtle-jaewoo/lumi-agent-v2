from datetime import UTC, datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    message: str = Field(
        ...,
        min_length=1,
        max_length=2000,
        description="사용자 메시지",
        examples=["오늘 방송 언제야?", "노래 추천해줘"],
    )

    session_id: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="세션 식별자",
        examples=["user123", "session-abc-123"],
    )

    user_id: str | None = Field(
        default=None,
        max_length=100,
        description="사용자 식별자 (선택)",
    )


class ChatResponse(BaseModel):
    message: str = Field(
        ...,
        description="루미의 응답 메시지",
    )

    tool_used: str | None = Field(
        default=None,
        description="사용된 Tool 이름",
        examples=["get_schedule", "recommend_song", None],
    )

    cached: bool = Field(
        default=False,
        description="캐시된 응답 여부",
    )

    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="응답 생성 시간 (UTC)",
    )


# =============================================================
# 스트리밍 관련 스키마
# =============================================================

# 스트리밍 이벤트 타입
StreamEventType = Literal["thinking", "tool", "token", "response", "error", "done"]


class StreamEvent(BaseModel):
    """
    SSE 스트리밍 이벤트 스키마

    Server-Sent Events로 전송되는 이벤트 형식입니다.
    각 이벤트 타입에 따라 다른 필드가 채워집니다.

    Attributes:
        type: 이벤트 타입
            - thinking: 노드 실행 시작 (어떤 노드가 실행 중인지)
            - tool: Tool 실행 결과
            - token: LLM 토큰 스트리밍
            - response: 최종 응답 완료
            - error: 에러 발생
            - done: 스트리밍 종료
        node: 현재 실행 중인 노드 이름 (thinking, tool 이벤트)
        content: 텍스트 내용 (token, response 이벤트)
        tool_name: 실행된 Tool 이름 (tool 이벤트)
        tool_result: Tool 실행 결과 (tool 이벤트)
        error: 에러 메시지 (error 이벤트)

    Example:
        >>> # 노드 실행 시작 이벤트
        >>> event = StreamEvent(type="thinking", node="router")

        >>> # Tool 실행 결과 이벤트
        >>> event = StreamEvent(
        ...     type="tool",
        ...     node="tool",
        ...     tool_name="get_schedule",
        ...     tool_result={"schedules": [...]}
        ... )

        >>> # 토큰 스트리밍 이벤트
        >>> event = StreamEvent(type="token", content="안녕")

        >>> # 최종 응답 이벤트
        >>> event = StreamEvent(
        ...     type="response",
        ...     content="금요일에 뮤직뱅크 나와!",
        ...     tool_used="get_schedule"
        ... )
    """

    type: StreamEventType = Field(
        ...,
        description="이벤트 타입",
    )

    node: str | None = Field(
        default=None,
        description="현재 실행 중인 노드 이름",
        examples=["router", "rag", "tool", "response"],
    )

    content: str | None = Field(
        default=None,
        description="텍스트 내용 (토큰 또는 최종 응답)",
    )

    tool_name: str | None = Field(
        default=None,
        description="실행된 Tool 이름",
        examples=["get_schedule", "recommend_song"],
    )

    tool_result: Any | None = Field(
        default=None,
        description="Tool 실행 결과",
    )

    tool_used: str | None = Field(
        default=None,
        description="최종 응답에서 사용된 Tool",
    )

    error: str | None = Field(
        default=None,
        description="에러 메시지",
    )

    def to_sse(self) -> str:
        """
        SSE 형식 문자열로 변환

        Returns:
            str: SSE 형식 문자열 (data: {...}\n\n)
        """
        import orjson

        # None 값 제외하고 직렬화
        data = {k: v for k, v in self.model_dump().items() if v is not None}
        json_str = orjson.dumps(data).decode("utf-8")
        return f"data: {json_str}\n\n"
