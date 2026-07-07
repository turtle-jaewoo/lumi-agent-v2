"""
HTTP 엔드포인트 정의

각 라우터는 특정 도메인의 API를 담당합니다:
    - chat.py: 채팅 API
"""

from fastapi import APIRouter

from app.api.routes import chat, health

api_router = APIRouter()
api_router.include_router(health.router, prefix="/health", tags=["Health"])  # 추가
api_router.include_router(chat.router, prefix="/chat", tags=["Chat"])
