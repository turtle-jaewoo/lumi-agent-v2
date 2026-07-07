"""
FastAPI 엔드포인트 테스트

pytest를 사용하여 API 엔드포인트를 테스트합니다.

실행 방법:
    uv run pytest tests/test_api.py -v
"""

from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient
from langchain_core.messages import AIMessage, HumanMessage

from app.main import app


@pytest.fixture
def client():
    """FastAPI 테스트 클라이언트를 생성합니다."""
    return TestClient(app)


class TestRootEndpoint:
    """루트 엔드포인트 테스트"""

    def test_root(self, client):
        """루트 엔드포인트 테스트 (Gradio UI로 리다이렉트)"""
        response = client.get("/", follow_redirects=False)
        assert response.status_code == 307  # RedirectResponse
        assert "/ui" in response.headers.get("location", "")


class TestChatEndpoints:
    """채팅 API 엔드포인트 테스트"""

    @patch("app.api.routes.chat.get_lumi_graph")
    def test_chat_success(self, mock_get_graph, client):
        """채팅 성공 테스트 (Mock 사용)"""
        # Mock Graph 설정
        mock_graph = AsyncMock()
        mock_get_graph.return_value = mock_graph

        # Mock 실행 결과 설정
        mock_graph.ainvoke.return_value = {
            "messages": [
                HumanMessage(content="안녕"),
                AIMessage(content="반가워! 루미야~"),
            ],
            "tool_name": None,
        }

        response = client.post(
            "/api/v1/chat/",
            json={
                "message": "안녕",
                "session_id": "test-session",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "반가워! 루미야~"
        assert data["tool_used"] is None

    def test_chat_validation_error(self, client):
        """유효성 검사 오류 테스트"""
        # message 누락
        response = client.post(
            "/api/v1/chat/",
            json={
                "session_id": "test-session",
            },
        )
        assert response.status_code == 422  # Validation Error

        # session_id 누락
        response = client.post(
            "/api/v1/chat/",
            json={
                "message": "안녕!",
            },
        )
        assert response.status_code == 422


class TestHealthEndpoints:
    """헬스체크 엔드포인트 테스트"""

    def test_health_check(self, client):
        """기본 헬스체크 테스트"""
        response = client.get("/api/v1/health/")
        assert response.status_code == 200

        data = response.json()
        assert data["status"] == "healthy"
        assert "timestamp" in data
        assert data["service"] == "lumi-agent"
