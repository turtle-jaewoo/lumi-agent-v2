"""
핵심 설정 및 공통 모듈

이 패키지에서 애플리케이션 전반에 걸쳐 사용되는
설정, 프롬프트, 유틸리티를 관리합니다.

모듈:
    - config.py: 환경변수 설정 관리
    - prompts.py: LLM 프롬프트 정의
"""

from app.core.config import settings

__all__ = ["settings"]
