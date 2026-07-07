"""
데이터베이스 접근 계층 (Repository Pattern)

이 패키지에서 데이터베이스(Supabase) 접근 로직을 정의합니다.

Repository 패턴을 사용하는 이유:
    1. 비즈니스 로직과 데이터 접근 로직 분리
    2. 테스트 용이성 (Repository를 Mock으로 대체 가능)
    3. 데이터베이스 변경 시 영향 범위 최소화

폴더 구조:
    - fan_letter.py: 팬레터 Repository
    - rag.py: RAG Repository
    - schedule.py: 스케줄 Repository
"""

from loguru import logger

from app.core.config import settings

# Supabase 클라이언트 싱글톤
_supabase_client = None


def get_supabase_client():
    """
    Supabase 클라이언트를 반환합니다 (싱글톤 패턴).

    설정(settings)에 Supabase URL과 Key가 있을 때만 연결을 시도합니다.
    연결 실패 시 None을 반환합니다.
    """
    global _supabase_client

    if _supabase_client is None and settings.supabase_url and settings.supabase_key:
        try:
            from supabase import create_client

            _supabase_client = create_client(
                settings.supabase_url,
                settings.supabase_key,
            )
            logger.info("✅ Supabase 클라이언트 초기화 완료")
        except Exception as e:
            logger.warning(f"Supabase 초기화 실패: {e}")
            _supabase_client = None

    return _supabase_client
