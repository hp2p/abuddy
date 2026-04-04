# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# 의존성 설치
uv sync

# 개발 서버 실행 (핫리로드)
uv run uvicorn abuddy.main:app --reload --app-dir src --port 8002

# Lint
uv run ruff check src/
uv run ruff format src/

# AWS 리소스 초기화 (최초 1회, EC2 IP를 인수로 전달)
uv run scripts/setup_aws.py http://YOUR_EC2_IP

# 개념 그래프 생성 (최초 1회, Bedrock Sonnet 사용)
uv run scripts/seed_concept_graph.py --exam aip-c01
uv run scripts/seed_concept_graph.py --exam CCA --exam-guide CCA-exam-guide.json

# 문서 수집 (Tavily)
uv run scripts/fetch_concept_docs.py --exam aip-c01
uv run scripts/fetch_concept_docs.py --exam CCA

# 문서 수집 - Skilljar 강의 콘텐츠 → S3 docs (CCA 전용)
uv run scripts/skilljar_to_docs.py --exam CCA           # 전체 실행
uv run scripts/skilljar_to_docs.py --exam CCA --dry-run # 매칭 확인만
uv run scripts/skilljar_to_docs.py --exam CCA --force   # 전체 재생성

# 문제 한글 번역 (1회성, Bedrock Sonnet 사용)
uv run scripts/translate_questions.py --exam CCA --limit 10  # 테스트 (10개)
uv run scripts/translate_questions.py --exam CCA             # 전체 번역
uv run scripts/translate_questions.py --exam aip-c01         # AIP-C01 번역
uv run scripts/translate_questions.py --dry-run              # 번역 결과 미리보기

# 문제 생성 (개념 그래프 생성 후)
uv run scripts/generate_questions.py --exam aip-c01
uv run scripts/generate_questions.py --exam aip-c01 --domain 1 --limit 5

# 사용자 팔로업 질문 → 문제 은행 변환
uv run scripts/generate_from_user_questions.py
uv run scripts/generate_from_user_questions.py --limit 20 --dry-run

# 기존 데이터 마이그레이션 (1회성, 기존 S3/DynamoDB 데이터에 exam_id 추가)
uv run scripts/migrate_s3_exam_prefix.py                         # 드라이런
uv run scripts/migrate_s3_exam_prefix.py --execute               # 실행

# S3 exam_id 이름 변경: claude-cert/ → CCA/ (1회성)
uv run scripts/migrate_exam_id_claude_cert_to_CCA.py             # 드라이런
uv run scripts/migrate_exam_id_claude_cert_to_CCA.py --execute   # 실행
uv run scripts/migrate_exam_id_claude_cert_to_CCA.py --execute --delete-old  # 실행 + 구버전 삭제
uv run scripts/migrate_questions_exam_id.py                      # 드라이런
uv run scripts/migrate_questions_exam_id.py --execute            # 실행

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
- **S3**: `abuddy-data` 버킷 — `{exam_id}/graph/concept_graph.json`, `{exam_id}/docs/{concept_id}.json`

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
