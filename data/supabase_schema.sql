-- 1강: Supabase pgvector 스키마
-- 이 SQL을 Supabase SQL Editor에서 실행
-- RAG를 위한 벡터 검색 인프라를 설정
-- 1. schedules 테이블
CREATE TABLE schedules (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  event_type TEXT NOT NULL,
  title TEXT NOT NULL,
  description TEXT,
  start_time TIMESTAMPTZ NOT NULL,
  end_time TIMESTAMPTZ,
  location TEXT,
  created_at TIMESTAMPTZ DEFAULT now()
);

-- 2. fan_letters 테이블
CREATE TABLE fan_letters (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  session_id TEXT NOT NULL,
  user_id TEXT,
  category TEXT NOT NULL DEFAULT 'other',
  message TEXT DEFAULT '',
  created_at TIMESTAMPTZ DEFAULT now()
);

-- pgvector 확장 활성화
CREATE EXTENSION IF NOT EXISTS vector;

-- documents 테이블 생성 : RAG 문서 저장
CREATE TABLE IF NOT EXISTS documents (
    id BIGSERIAL PRIMARY KEY,

    -- 문서 내용 (청크 단위로 저장)
    content TEXT NOT NULL,

    -- 임베딩 벡터 (Upstage solar-embedding-1-large: 4096차원)
    embedding VECTOR(4096),

    -- 메타데이터 (버전, 상태, 태그 등)
    -- 예: {"version": "2.5", "status": "active", "tags": ["루미", "프로필"]}
    metadata JSONB DEFAULT '{}',

    -- 생성 시간
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 메타데이터 인덱스 생성 (필터링 성능)
CREATE INDEX IF NOT EXISTS documents_metadata_idx
ON documents
USING gin (metadata);

-- 검색 함수 생성 (메타데이터 필터링 지원)
CREATE OR REPLACE FUNCTION match_documents(
    query_embedding VECTOR(4096),
    match_count INT DEFAULT 3,
    filter_status TEXT DEFAULT 'active'
)
RETURNS TABLE(
    id BIGINT,
    content TEXT,
    metadata JSONB,
    similarity FLOAT
)
LANGUAGE sql STABLE
AS $$
    SELECT
        id,
        content,
        metadata,
        1 - (embedding <=> query_embedding) AS similarity
    FROM documents
    WHERE
        CASE
            WHEN filter_status = 'all' THEN TRUE
            ELSE metadata->>'status' = filter_status
        END
    ORDER BY embedding <=> query_embedding
    LIMIT match_count;
$$;

-- 문서 통계 함수
CREATE OR REPLACE FUNCTION get_document_stats()
RETURNS TABLE(
    status TEXT,
    count BIGINT
)
LANGUAGE sql STABLE
AS $$
    SELECT
        metadata->>'status' AS status,
        COUNT(*) AS count
    FROM documents
    GROUP BY metadata->>'status';
$$;

-- 데이터 잘 들어갔나 확인하는 쿼리
-- SELECT * FROM documents LIMIT 5;
