"""
Supabase에 스케줄 샘플 데이터를 적재하는 스크립트

실행 방법:
    uv run python data/scripts/ingest_data.py

주의:
    - data/supabase_schema.sql을 먼저 Supabase에서 실행하세요
    - .env 파일에 Supabase 설정이 필요합니다
    - 테이블이 이미 존재하면 데이터만 추가합니다
    - RAG 세계관 문서는 ingest_rag.py를 사용하세요
"""

import asyncio
import sys
from datetime import datetime, timedelta
from pathlib import Path

# 프로젝트 루트를 PYTHONPATH에 추가
sys.path.insert(0, str(Path(__file__).parent.parent))

from loguru import logger

# ===== 샘플 데이터 정의 =====

# 루미 스케줄 샘플 데이터
SAMPLE_SCHEDULES = [
    {
        "title": "뮤직뱅크 출연",
        "event_type": "broadcast",
        "start_time": (datetime.now() + timedelta(days=3)).isoformat(),
        "location": "KBS 공개홀",
        "description": "신곡 'Starlight' 첫 무대!",
    },
    {
        "title": "팬사인회",
        "event_type": "fan_meeting",
        "start_time": (datetime.now() + timedelta(days=5)).isoformat(),
        "location": "코엑스 그랜드볼룸",
        "description": "2기 앨범 발매 기념 팬사인회",
    },
    {
        "title": "유튜브 라이브",
        "event_type": "broadcast",
        "start_time": (datetime.now() + timedelta(days=1)).isoformat(),
        "location": "온라인 (YouTube)",
        "description": "팬들과 소통하는 저녁 라이브",
    },
    {
        "title": "음악중심 출연",
        "event_type": "broadcast",
        "start_time": (datetime.now() + timedelta(days=7)).isoformat(),
        "location": "MBC 드림센터",
        "description": "음악중심 컴백 무대",
    },
    {
        "title": "팬미팅 'LUMI DAY'",
        "event_type": "fan_meeting",
        "start_time": (datetime.now() + timedelta(days=14)).isoformat(),
        "location": "올림픽공원 올림픽홀",
        "description": "연말 팬미팅 이벤트",
    },
    {
        "title": "라디오 출연 (볼륨을 높여요)",
        "event_type": "broadcast",
        "start_time": (datetime.now() + timedelta(days=2)).isoformat(),
        "location": "KBS 라디오 스튜디오",
        "description": "볼륨을 높여요 게스트 출연",
    },
]


async def create_supabase_client():
    """
    Supabase 클라이언트를 생성합니다.

    Returns:
        supabase.Client: Supabase 클라이언트
    """
    from supabase import Client, create_client

    from app.core.config import settings

    if not settings.supabase_url or not settings.supabase_key:
        raise ValueError("Supabase 설정이 완료되지 않았습니다. .env 파일을 확인하세요.")

    client: Client = create_client(settings.supabase_url, settings.supabase_key)
    return client


async def insert_sample_schedules(client) -> int:
    """
    샘플 스케줄 데이터를 삽입합니다.

    Args:
        client: Supabase 클라이언트

    Returns:
        int: 삽입된 레코드 수
    """
    try:
        # 기존 데이터 확인
        existing = client.table("schedules").select("id").execute()

        if existing.data:
            logger.info(f"이미 {len(existing.data)}개의 스케줄이 존재합니다.")
            return 0

        # 데이터 삽입
        result = client.table("schedules").insert(SAMPLE_SCHEDULES).execute()

        logger.info(f"{len(result.data)}개의 스케줄 데이터가 삽입되었습니다.")
        return len(result.data)

    except Exception as e:
        logger.error(f"스케줄 데이터 삽입 실패: {e}")
        logger.info(
            "테이블이 존재하지 않을 수 있습니다. data/supabase_schema.sql을 먼저 실행하세요."
        )
        return 0


async def main():
    """
    메인 실행 함수
    """
    logger.info("=" * 50)
    logger.info("Lumi Agent 스케줄 데이터 적재 스크립트")
    logger.info("=" * 50)

    # Supabase 스케줄 데이터 적재
    logger.info("스케줄 데이터 적재 중...")

    try:
        client = await create_supabase_client()
        inserted_count = await insert_sample_schedules(client)

        if inserted_count > 0:
            logger.success(f"데이터 적재 완료! (스케줄: {inserted_count}개)")
        else:
            logger.info("새로운 데이터가 적재되지 않았습니다.")

    except ValueError as e:
        logger.warning(f"Supabase 연결 실패: {e}")
        logger.info("Supabase 설정 후 다시 실행하세요.")

    except Exception as e:
        logger.error(f"데이터 적재 중 오류 발생: {e}")


if __name__ == "__main__":
    asyncio.run(main())
