# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# 의존성 설치
uv sync

# 개발 서버 실행 (핫리로드)
uv run uvicorn abuddy.main:app --reload --app-dir src

# Lint
uv run ruff check src/
uv run ruff format src/

# AWS 리소스 초기화 (최초 1회, EC2 IP를 인수로 전달)
uv run scripts/setup_aws.py http://YOUR_EC2_IP

# 개념 그래프 생성 (최초 1회, Bedrock Sonnet 사용)
uv run scripts/seed_concept_graph.py

# 문제 생성 (개념 그래프 생성 후)
uv run scripts/generate_questions.py
uv run scripts/generate_questions.py --domain 1 --limit 5

# Docker 로컬 실행
docker compose up --build
```

## Architecture

**목적**: AWS Certified Generative AI Developer Professional (AIP-C01) 자격증 준비용 **멀티유저** 웹앱.

**스택**: FastAPI + HTMX + Jinja2 (서버사이드 렌더링). EC2에 Docker로 배포.

**AWS 서비스**:
- **Cognito**: 사용자 인증 (Hosted UI, OAuth2 authorization code flow)
- **Bedrock**: Claude Haiku (일상 문제 출제/답변 평가) + Sonnet (개념 그래프 최초 생성)
- **DynamoDB**:
  - `abuddy-questions`: PK=`question_id` — 전체 공유 문제 은행
  - `abuddy-schedule`: PK=`user_id`, SK=`question_id` — 유저별 에빙하우스 스케줄
- **S3**: `abuddy-data` 버킷 — `graph/concept_graph.json` (개념 그래프, 공유)

**인증 흐름**:
`/` → 쿠키 없으면 `/auth/login` → Cognito Hosted UI → `/auth/callback?code=` → id_token 쿠키 설정 → `/`
JWT 검증: `services/auth.py::verify_token()` (JWKS 공개키 캐시)

**핵심 흐름**:
1. `seed_concept_graph.py` → Bedrock Sonnet이 시험 가이드에서 개념 추출 → S3 JSON 저장
2. `generate_questions.py` → 개념별 MC/MR 문제 생성 → DynamoDB 저장
3. 웹앱: `quiz_engine.get_next_question(user_id)` → 우선순위 큐 → 문제 표시 → 답변 처리 → 스케줄 업데이트

**에빙하우스 스케줄 우선순위** (`services/quiz_engine.py`):
1. DynamoDB `next_review_at <= now` (10분 리뷰 + 장기 복습 통합)
2. 처음 보는 문제 (해당 유저의 schedule에 없는 것)

**오답 처리**: 1일 후 리셋 + 연관 concept 문제를 10분 후 DynamoDB에 등록.
**정답+미확인**: `interval_step=IN_SESSION`, `next_review_at=now+10min` 으로 재등록.
**마스터 판정**: 난이도별 연속 정답 (EASY=2, MEDIUM=3, HARD=4) + `self_confirmed=True`.

**개념 그래프**: `services/concept_graph.py` — S3에서 로드해 networkx `DiGraph`로 메모리 캐시 (전체 공유).

## Question Format

실제 시험과 동일:
- **Multiple Choice**: 4지선다, 1개 정답
- **Multiple Response**: 5지선다, 2-3개 정답 (문제에 "Choose N answers." 포함)

## Environment

`.env.example` 참고. `setup_aws.py` 실행 시 Cognito 설정값이 출력됩니다.
EC2에서는 IAM 인스턴스 프로파일(`abuddy-ec2-role`)로 인증 (env 키 불필요).
