# ABuddy — 프로젝트 컨텍스트 & 구현 계획

_마지막 업데이트: 2026-03-28_

---

## 다음 작업 (2026-03-29 이어서)

**여기서부터 시작:**
```bash
uv run scripts/generate_questions.py --domain 1 --limit 3
```
소량 테스트 후 전체 생성:
```bash
uv run scripts/generate_questions.py
```

**오늘 완료한 것 (2026-03-28):**
- `aip-c01-exam-guide.json` 생성 (시험 가이드 100% 구조화)
- `seed_concept_graph.py` 개선 (JSON 기반 + Task별 체크포인팅)
- `inspect_graph.py` 추가 (그래프 검사 스크립트)
- Starlette 1.0.0 API 호환 수정 (`TemplateResponse` 인수 순서)
- `StaticFiles` 마운트, HTMX 로컬 파일 적용
- 포트 8000 → 8002 전체 변경
- 앱 정상 기동 확인 (로그인 + 페이지 렌더링 + DynamoDB 연결)
- 개념 그래프 S3 저장 완료

---

---

## 1. 프로젝트 개요

**목적**: AWS Certified Generative AI Developer Professional (AIP-C01) 자격증 준비용 **멀티유저** 웹앱.
**목표 시험**: AIP-C01 (2025-11 출시, 75문항, 750/1000점 합격)
**예산**: ~$20/월

### 기술 스택
| 계층 | 선택 |
|------|------|
| 웹 프레임워크 | FastAPI + HTMX + Jinja2 (SSR) |
| 인증 | Cognito Hosted UI (OAuth2 authorization code flow) |
| LLM | Bedrock Claude Haiku (일상) + Sonnet (1회성 개념 추출) |
| 개념 그래프 | S3 JSON + networkx DiGraph (메모리 캐시) |
| 문제 DB | DynamoDB `abuddy-questions` (PK=question_id) |
| 스케줄 DB | DynamoDB `abuddy-schedule` (PK=user_id, SK=question_id) |
| 배포 | EC2 + Docker (ECS/Lambda 아님) |
| 패키지 관리 | uv |
| Lint | ruff |
| 로깅 | loguru |

### 핵심 아키텍처 흐름
```
seed_concept_graph.py
  → aip-c01-exam-guide.json 로드
  → Bedrock Sonnet으로 개념 추출
  → S3 graph/concept_graph.json 저장

generate_questions.py
  → S3에서 개념 그래프 로드
  → Bedrock Haiku로 MC/MR 문제 생성
  → DynamoDB abuddy-questions 저장

웹앱 (uvicorn)
  → / → 통계 대시보드
  → /quiz → 다음 문제 (에빙하우스 우선순위)
  → POST /quiz/{id}/answer → 채점 + 스케줄 업데이트 (HTMX)
  → POST /quiz/{id}/ask → 팔로업 질문 (Bedrock, HTMX)
  → /stats → 진도 현황
```

### 에빙하우스 스케줄 규칙
- **간격**: IN_SESSION(10분) → DAY_1(1일) → WEEK_1(7일) → MONTH_1(30일) → MASTERED
- **오답**: 1일 후 리셋 + 연관 concept 문제 10분 큐 등록
- **정답+불확실**: 10분 후 재확인 (advance 없음)
- **마스터**: EASY=2, MEDIUM=3, HARD=4 연속 정답 + self_confirmed=True

### 문제 형식 (실제 시험 동일)
- **Multiple Choice**: 4지선다, 1개 정답
- **Multiple Response**: 5지선다, 2-3개 정답 ("Choose N answers." 포함)

---

## 2. 현재 구현 상태

### ✅ 완료
| 파일 | 설명 |
|------|------|
| `src/abuddy/config.py` | pydantic-settings 환경변수 |
| `src/abuddy/main.py` | FastAPI 앱, 라우터, 시작 시 개념 그래프 로드 |
| `src/abuddy/models/question.py` | Question, QuestionType, Difficulty, AnswerSubmission |
| `src/abuddy/models/schedule.py` | ReviewSchedule, IntervalStep, MASTERY_THRESHOLD |
| `src/abuddy/models/concept.py` | Concept, ConceptEdge, ConceptGraph |
| `src/abuddy/db/questions.py` | DynamoDB CRUD (put/get/list/count) |
| `src/abuddy/db/schedule.py` | DynamoDB CRUD + get_due / get_scheduled / get_stats |
| `src/abuddy/services/auth.py` | Cognito JWT 검증, JWKS 캐시, token exchange |
| `src/abuddy/services/bedrock.py` | generate_question / answer_followup / extract_concept_graph |
| `src/abuddy/services/concept_graph.py` | S3 로드/저장, networkx, get_related_concept_ids |
| `src/abuddy/services/quiz_engine.py` | get_next_question, process_answer, _queue_related |
| `src/abuddy/routers/auth.py` | /auth/login, /auth/callback, /auth/logout |
| `src/abuddy/routers/quiz.py` | /, /quiz, /quiz/{id}/answer, /quiz/{id}/ask, /stats |
| `scripts/setup_aws.py` | S3, DynamoDB, Cognito, IAM 초기화 |
| `scripts/seed_concept_graph.py` | 시험 가이드 → 개념 그래프 추출 → S3 저장 |
| `scripts/generate_questions.py` | 개념별 문제 생성 → DynamoDB 저장 |
| `aip-c01-exam-guide.json` | 시험 가이드 완전 구조화 JSON |
| `docker-compose.yml` | 로컬/EC2 Docker 실행 |
| `pyproject.toml` | 의존성, ruff, pytest 설정 |

### ❌ 미완성 (구현 필요)

| 항목 | 우선순위 | 설명 |
|------|----------|------|
| **Jinja2 템플릿 전체** | 🔴 P0 | 앱 실행 자체가 불가 |
| **Dockerfile** | 🔴 P0 | docker-compose가 참조하나 파일 없음 |
| **seed 스크립트 JSON 지원** | 🟡 P1 | .md 파싱 대신 exam-guide.json 직접 사용 |
| **정적 파일 (HTMX, CSS)** | 🔴 P0 | UI 동작에 필수 |
| **테스트** | 🟢 P2 | pytest 설정은 있으나 tests/ 없음 |
| **EC2 배포 가이드** | 🟢 P2 | .env, 방화벽, systemd 등 |

---

## 3. 구현 계획 (우선순위 순)

---

### Phase 1: 앱 실행 가능 상태 만들기 (P0)

#### Task 1-A: Dockerfile 작성
```
Dockerfile
```
- Python 3.12-slim 베이스
- uv로 의존성 설치
- 포트 8000 EXPOSE
- uvicorn 실행

#### Task 1-B: 정적 파일 설정
```
src/abuddy/static/
  htmx.min.js         ← HTMX 2.x CDN 또는 로컬
  style.css           ← 최소한의 스타일 (MVP 수준)
```
- FastAPI StaticFiles 마운트 추가 (`main.py`)

#### Task 1-C: Jinja2 템플릿 작성
```
src/abuddy/templates/
  base.html                      ← 공통 레이아웃 (nav, htmx CDN)
  login.html                     ← Cognito 로그인 버튼
  login_no_cognito.html          ← Cognito 미설정 시 안내
  index.html                     ← 대시보드 (통계 요약 + 시작 버튼)
  quiz.html                      ← 문제 표시 (MC/MR 분기)
  no_questions.html              ← 문제 없을 때 안내
  stats.html                     ← 진도 상세 통계
  partials/
    feedback.html                ← 채점 결과 (HTMX swap 타겟)
    followup_answer.html         ← 팔로업 답변 (HTMX swap 타겟)
```

템플릿 상세 요구사항:

**`base.html`**
- HTMX 스크립트 로드
- 네비게이션: 로고, /quiz 링크, /stats 링크, 로그아웃
- `{% block content %}` 슬롯

**`quiz.html`**
- 문제 텍스트 표시
- QuestionType에 따라 분기:
  - MC: radio 버튼 (A/B/C/D)
  - MR: checkbox (A/B/C/D/E) + "Choose N answers." 안내
- 제출 버튼: `hx-post="/quiz/{id}/answer"` → `#feedback` 교체
- 답변 전까지 팔로업 폼 숨김

**`partials/feedback.html`**
- 정답/오답 표시 (색상 구분)
- 각 선택지 정답 여부 표시
- 해설 (explanation) 출력
- 다음 복습 예정 시간 (schedule.next_review_at)
- self_confirmed 체크박스: `hx-post` → schedule advance
- 팔로업 질문 폼: `hx-post="/quiz/{id}/ask"` → `#followup` 삽입
- "다음 문제" 버튼: `hx-get="/quiz"` → 페이지 교체

**`partials/followup_answer.html`**
- 유저 질문 echo
- Bedrock 답변 (markdown 렌더링 고려)
- 추가 질문 폼 (반복 가능)

**`index.html`**
- 총 문제 수, 마스터 수, 오늘 due 수
- "공부 시작" → /quiz 버튼

**`stats.html`**
- 전체/마스터/due/미시작 카운트
- 도메인별 진도 (추후 확장)

---

### Phase 2: 데이터 파이프라인 개선 (P1)

#### Task 2-A: seed 스크립트 JSON 활용
`scripts/seed_concept_graph.py` 수정:
- `aip-c01-exam-guide.json` 로드 지원 추가
- JSON의 `domains[].tasks[].skills[]` 구조에서 직접 개념 추출
- 기존 .md 파싱 방식은 fallback으로 유지

JSON → 개념 매핑 전략:
- 각 `skill` → 1개 Concept 노드
  - `concept_id`: `"d{domain}-t{task}-s{skill_id}"` (e.g. `"d1-t1.1-s1.1.1"`)
  - `name`: skill description 첫 문장 요약 (Bedrock 불필요, 직접 파싱)
  - `aws_services`: `techniques`에서 "Using {Service}" 패턴 추출
  - `domain`: domain id
- Task 단위 → Skill 간 `part_of` edge 자동 생성
- 도메인 간 공통 서비스 → `similar_to` edge (선택)

또는 기존처럼 Bedrock Sonnet에 JSON 청크를 전달해 개념 추출 (품질 우선).

#### Task 2-B: DynamoDB scan 개선
현재 `list_all_question_ids()`가 full scan → GSI 또는 캐시 고려:
- `abuddy-questions` 테이블에 `domain` GSI 추가 (setup_aws.py 수정)
- 또는 앱 시작 시 question_ids를 메모리 캐시

---

### Phase 3: 품질 & 운영 (P2)

#### Task 3-A: 테스트 작성
```
tests/
  test_quiz_engine.py    ← process_answer, get_next_question (DynamoDB mock)
  test_schedule.py       ← ReviewSchedule.advance, reset, mastery logic
  test_bedrock.py        ← generate_question (Bedrock mock)
```

#### Task 3-B: EC2 배포
1. EC2 인스턴스: t3.micro (Amazon Linux 2023)
2. IAM 인스턴스 프로파일: `abuddy-ec2-role` (S3/DynamoDB/Bedrock)
3. `.env` 파일 배포 방법 (Secrets Manager 또는 직접 scp)
4. `docker compose up -d` 실행
5. 보안 그룹: 포트 8000 오픈
6. (선택) Nginx 리버스 프록시 + 도메인

#### Task 3-C: 모니터링
- CloudWatch 로그 그룹 (`/abuddy/app`)
- 토큰 사용량 추적 (Bedrock Model Invocation Logs)
- 예산 알림 ($20 임계)

---

## 4. 시험 가이드 데이터 활용

`aip-c01-exam-guide.json` 구조:
```json
{
  "exam": { ... },
  "domains": [
    {
      "id": 1, "weight_pct": 31,
      "tasks": [
        {
          "id": "1.1",
          "skills": [
            {
              "id": "1.1.1",
              "description": "...",
              "techniques": ["Using Amazon Bedrock", ...]
            }
          ]
        }
      ]
    }
  ],
  "appendix": { ... }
}
```

- **개념 추출 단위**: skill (총 ~60개 skills → ~60 concepts)
- **문제 생성 계획**: skill당 MC 2개 + MR 1개 = **약 180문제**
- **도메인별 가중치 반영**: 문제 수를 weight_pct에 비례 조정 가능

---

## 5. 파일 구조 (목표 상태)

```
abuddy/
├── aip-c01-exam-guide.json          ✅ 시험 가이드 구조화 JSON
├── aip-c01-exam-guide-structured.md ✅ 원본 마크다운
├── docker-compose.yml               ✅
├── Dockerfile                       ❌ → 작성 필요
├── pyproject.toml                   ✅
├── CLAUDE.md                        ✅
├── PLAN.md                          ✅ 이 파일
├── .env / .env.example              ✅
├── scripts/
│   ├── setup_aws.py                 ✅
│   ├── seed_concept_graph.py        ✅ (JSON 지원 추가 필요)
│   └── generate_questions.py        ✅
├── src/abuddy/
│   ├── config.py                    ✅
│   ├── main.py                      ✅ (StaticFiles 마운트 추가 필요)
│   ├── models/                      ✅ question, schedule, concept
│   ├── db/                          ✅ questions, schedule
│   ├── services/                    ✅ auth, bedrock, concept_graph, quiz_engine
│   ├── routers/                     ✅ auth, quiz
│   ├── static/                      ❌ → htmx.min.js, style.css
│   └── templates/                   ❌ → 전체 작성 필요
└── tests/                           ❌ → P2 작성 예정
```

---

## 6. 실행 순서 (처음 세팅 시)

```bash
# 1. 의존성 설치
uv sync

# 2. AWS 리소스 초기화 (최초 1회)
uv run scripts/setup_aws.py http://YOUR_EC2_IP

# 3. .env 설정 (Cognito 값 복사)
cp .env.example .env
# .env 편집

# 4. 개념 그래프 생성 (Bedrock Sonnet, 최초 1회, ~5분)
uv run scripts/seed_concept_graph.py

# 5. 문제 생성 (Bedrock Haiku, ~180문제)
uv run scripts/generate_questions.py

# 6. 개발 서버
uv run uvicorn abuddy.main:app --reload --app-dir src

# 7. Docker 배포
docker compose up --build
```
