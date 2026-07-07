# Day 2 Mission — Docker 컨테이너화 및 GCE VM 배포

## 환경 설정

```bash
# 의존성 설치
uv sync

# 환경변수 설정
cp .env.example .env
```

## 실행

```bash
# Docker 이미지 빌드
docker build -t lumi-agent .

# Docker Compose로 실행
docker-compose up --build

# 백그라운드 실행
docker-compose up -d

# 로그 확인
docker-compose logs -f

# 종료
docker-compose down
```

## 미션

### 1. `app/api/routes/health.py` - 헬스체크 엔드포인트

| TODO | 내용 |
|------|------|
| TODO 1 | APIRouter 인스턴스 생성 |
| TODO 2 | 헬스체크 엔드포인트 구현 |

### 2. `Dockerfile` - 컨테이너 이미지 구성

| TODO | 내용 |
|------|------|
| TODO 1 | 의존성 설치 명령어 작성 |
| TODO 2 | 보안 설정 - non-root 유저 생성 및 권한 설정 |
| TODO 3 | 헬스체크 설정 |
| TODO 4 | 서버 실행 명령어 작성 (uv run) |

### 3. `docker-compose.yml` - 로컬 실행 환경

| TODO | 내용 |
|------|------|
| TODO 1 | 이미지 및 빌드 설정 |
| TODO 2 | 포트 매핑 (호스트:컨테이너) |
| TODO 3 | 환경변수 설정 |
| TODO 4 | 헬스체크 및 재시작 정책 설정 |

### 4. `.github/workflows/cd.yml` - CD 파이프라인

| TODO | 내용 |
|------|------|
| TODO 1 | 트리거 설정 |
| TODO 2 | GHCR Push 권한 설정 |
| TODO 3 | GHCR 로그인 |
| TODO 4 | 이미지 빌드 & Push |
