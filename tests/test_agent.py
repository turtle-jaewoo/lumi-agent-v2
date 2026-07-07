"""
LangGraph 에이전트 기본 테스트

pytest-asyncio를 사용하여 비동기 테스트를 수행합니다.

실행 방법:
    uv sync --extra dev
    uv run pytest tests/test_agent.py -v
"""

import pytest

from app.graph.edges import route_by_intent
from app.graph.state import LumiState, create_initial_state
from app.tools.executor import ToolExecutor


class TestState:
    """State 관련 테스트"""

    def test_create_initial_state(self):
        """초기 상태 생성 테스트"""
        state = create_initial_state(
            session_id="test-session",
            user_id="test-user",
        )

        assert state["session_id"] == "test-session"
        assert state["user_id"] == "test-user"
        assert state["messages"] == []
        assert state["intent"] is None
        assert state["tool_name"] is None

    def test_create_initial_state_without_user_id(self):
        """user_id 없이 초기 상태 생성"""
        state = create_initial_state(session_id="test-session")

        assert state["session_id"] == "test-session"
        assert state["user_id"] is None


class TestEdges:
    """Edge 라우팅 테스트"""

    def test_route_by_intent_chat(self):
        """chat 의도 라우팅 테스트"""
        state: LumiState = {
            "messages": [],
            "intent": "chat",
            "retrieved_docs": [],
            "tool_name": None,
            "tool_args": None,
            "tool_result": None,
            "session_id": "test",
            "user_id": None,
        }

        result = route_by_intent(state)
        assert result == "response"

    def test_route_by_intent_rag(self):
        """rag 의도 라우팅 테스트"""
        state: LumiState = {
            "messages": [],
            "intent": "rag",
            "retrieved_docs": [],
            "tool_name": None,
            "tool_args": None,
            "tool_result": None,
            "session_id": "test",
            "user_id": None,
        }

        result = route_by_intent(state)
        assert result == "rag"

    def test_route_by_intent_tool(self):
        """tool 의도 라우팅 테스트"""
        state: LumiState = {
            "messages": [],
            "intent": "tool",
            "retrieved_docs": [],
            "tool_name": "get_schedule",
            "tool_args": {},
            "tool_result": None,
            "session_id": "test",
            "user_id": None,
        }

        result = route_by_intent(state)
        assert result == "tool"

    def test_route_by_intent_default(self):
        """기본 의도 라우팅 테스트 (None -> response)"""
        state: LumiState = {
            "messages": [],
            "intent": None,
            "retrieved_docs": [],
            "tool_name": None,
            "tool_args": None,
            "tool_result": None,
            "session_id": "test",
            "user_id": None,
        }

        result = route_by_intent(state)
        assert result == "response"


class TestToolExecutor:
    """Tool Executor 테스트"""

    @pytest.fixture
    def executor(self):
        """ToolExecutor 인스턴스 생성"""
        return ToolExecutor()

    @pytest.mark.asyncio
    async def test_recommend_song_happy(self, executor):
        """노래 추천 테스트 (happy)"""
        result = await executor.execute(
            tool_name="recommend_song",
            tool_args={"mood": "happy"},
            session_id="test-session",
        )

        assert result["success"] is True
        assert "data" in result
        assert "song" in result["data"]
        assert result.get("mock") is True

    @pytest.mark.asyncio
    async def test_recommend_song_sad(self, executor):
        """노래 추천 테스트 (sad)"""
        result = await executor.execute(
            tool_name="recommend_song",
            tool_args={"mood": "sad"},
            session_id="test-session",
        )

        assert result["success"] is True
        assert result["data"]["mood"] == "sad"

    @pytest.mark.asyncio
    async def test_get_weather(self, executor):
        """날씨 조회 테스트"""
        result = await executor.execute(
            tool_name="get_weather",
            tool_args={},
            session_id="test-session",
        )

        assert result["success"] is True
        assert "data" in result
        assert "temperature" in result["data"]
        assert result.get("mock") is True

    @pytest.mark.asyncio
    async def test_unknown_tool(self, executor):
        """알 수 없는 Tool 테스트"""
        result = await executor.execute(
            tool_name="unknown_tool",
            tool_args={},
            session_id="test-session",
        )

        assert result["success"] is False
        assert "error" in result

    @pytest.mark.asyncio
    async def test_get_schedule_real(self, executor):
        """스케줄 조회 테스트 (Real/Empty)"""
        result = await executor.execute(
            tool_name="get_schedule",
            tool_args={
                "start_date": "2025-01-06",
                "end_date": "2025-01-12",
            },
            session_id="test-session",
        )

        # DB 연결 실패 시에도 빈 리스트를 반환하거나 에러를 로깅하고 [] 반환하므로 success는 True여야 함
        assert result["success"] is True
        assert "data" in result
        assert isinstance(result["data"]["schedules"], list)

    @pytest.mark.asyncio
    async def test_send_fan_letter_mock(self, executor):
        """팬레터 저장 테스트 (Mock)"""
        result = await executor.execute(
            tool_name="send_fan_letter",
            tool_args={
                "category": "cheer",
                "message": "항상 응원해!",
            },
            session_id="test-session",
            user_id="test-user",
        )

        assert result["success"] is True
        assert "letter_id" in result["data"]
