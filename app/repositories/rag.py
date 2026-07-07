"""
RAG(Retrieval-Augmented Generation)를 위한 문서 검색 Repository

사용법:
    from app.repositories.rag import RAGRepository

    repo = RAGRepository()

    # 활성 문서만 검색 (기본값, 권장)
    docs = await repo.search_similar("루미 MBTI", filter_status="active")

    # 모든 문서 검색 (테스트용)
    docs = await repo.search_similar("마늘 좋아해?", filter_status="all")
"""

from typing import Literal

from langchain_upstage import UpstageEmbeddings
from loguru import logger
from supabase import Client, create_client

from app.core.config import settings


class RAGRepository:
    """
    RAG를 위한 문서 검색 Repository

    Supabase pgvector를 사용하여 시맨틱 검색을 수행합니다.

    메타데이터 필터링 지원
    - filter_status="active": 활성 문서만 검색 (기본값)
    - filter_status="deprecated": 폐기 문서만 검색 (디버깅용)
    - filter_status="all": 모든 문서 검색 (테스트용)

    Attributes:
        embeddings: Upstage 임베딩 클라이언트
        supabase: Supabase 클라이언트
    """

    def __init__(self):
        """
        RAGRepository 초기화
        """
        self.embeddings = UpstageEmbeddings(
            api_key=settings.upstage_api_key, model="solar-embedding-1-large-passage"
        )

        self.supabase: Client = create_client(
            settings.supabase_url, settings.supabase_key
        )

        logger.info("RAGRepository 초기화 완료 (필터링 지원)")

    async def search_similar(
        self,
        query: str,
        k: int = 3,
        filter_status: Literal["active", "deprecated", "all"] = "active",
    ) -> list[dict]:
        """
        쿼리와 유사한 문서를 검색합니다.

        메타데이터 필터링 추가
        - filter_status="active": v2.5(현행) 문서만 검색
        - filter_status="all": v1.0(폐기) 포함 모든 문서 검색

        Args:
            query: 검색 쿼리
            k: 반환할 문서 수 (기본값: 3)
            filter_status: 필터링 조건 (기본값: "active")

        Returns:
            list[dict]: 검색된 문서 목록
                - id: 문서 ID
                - content: 문서 내용
                - metadata: 메타데이터 (version, status 등)
                - similarity: 유사도 점수 (0~1)

        Example:
            >>> repo = RAGRepository()
            >>> # 활성 문서만 검색 (권장)
            >>> docs = await repo.search_similar("마늘 좋아해?", filter_status="active")
            >>> # 결과: v2.5 기준 "마늘 좋아함" 문서만 반환

            >>> # 모든 문서 검색 (테스트용)
            >>> docs = await repo.search_similar("마늘 좋아해?", filter_status="all")
            >>> # 결과: v1.0 "뱀파이어라 마늘 싫어함"도 포함될 수 있음!
        """
        logger.info(f"RAG 검색: '{query[:30]}...' (k={k}, filter={filter_status})")

        try:
            # Step 1: 쿼리 임베딩
            query_embedding = await self.embeddings.aembed_query(query)

            # Step 2: Supabase RPC로 유사 문서 검색
            # filter_status 파라미터 추가
            result = self.supabase.rpc(
                "match_documents",
                {
                    "query_embedding": query_embedding,
                    "match_count": k,
                    "filter_status": filter_status,  # 필터링!
                },
            ).execute()

            docs = result.data or []

            # 결과 로깅 (디버깅용)
            for doc in docs:
                version = doc.get("metadata", {}).get("version", "?")
                status = doc.get("metadata", {}).get("status", "?")
                similarity = doc.get("similarity", 0)
                logger.debug(f"  - v{version} ({status}): {similarity:.3f}")

            logger.info(f"RAG 검색 결과: {len(docs)}개 문서")

            return docs

        except Exception as e:
            logger.error(f"RAG 검색 실패: {e}")
            return []

    async def search_without_filter(self, query: str, k: int = 3) -> list[dict]:
        """
        필터링 없이 검색 (시연용)

        폐기 문서(v1.0)도 포함하여 검색합니다.
        "필터링 안 하면 이렇게 망한다"를 보여주기 위한 메서드입니다.

        Args:
            query: 검색 쿼리
            k: 반환할 문서 수

        Returns:
            list[dict]: 모든 문서에서 검색 (폐기 문서 포함)
        """
        logger.warning("⚠️ 필터링 없이 검색 중! (시연용)")
        return await self.search_similar(query, k, filter_status="all")

    async def get_document_stats(self) -> dict:
        """
        문서 상태별 통계를 반환합니다.

        Returns:
            dict: 상태별 문서 수
                예: {"active": 45, "deprecated": 30}
        """
        try:
            result = self.supabase.rpc("get_document_stats").execute()
            stats = {row["status"]: row["count"] for row in (result.data or [])}
            logger.info(f"문서 통계: {stats}")
            return stats
        except Exception as e:
            logger.error(f"통계 조회 실패: {e}")
            return {}

    async def get_document_count(self, filter_status: str = "all") -> int:
        """
        저장된 문서(청크) 수를 반환합니다.

        Args:
            filter_status: 필터링 조건 (기본값: "all")

        Returns:
            int: 문서 수
        """
        try:
            if filter_status == "all":
                result = (
                    self.supabase.table("documents")
                    .select("id", count="exact")
                    .execute()
                )
            else:
                result = (
                    self.supabase.table("documents")
                    .select("id", count="exact")
                    .eq("metadata->>status", filter_status)
                    .execute()
                )

            return result.count or 0
        except Exception as e:
            logger.error(f"문서 수 조회 실패: {e}")
            return 0


# 싱글톤 인스턴스
_rag_repository: RAGRepository | None = None


def get_rag_repository() -> RAGRepository:
    """
    RAGRepository 싱글톤 인스턴스를 반환합니다.

    Returns:
        RAGRepository: RAG Repository 인스턴스
    """
    global _rag_repository

    if _rag_repository is None:
        _rag_repository = RAGRepository()

    return _rag_repository
