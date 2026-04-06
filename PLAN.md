# ABuddy — 프로젝트 컨텍스트 & 구현 계획

_마지막 업데이트: 2026-04-05 (6차)_

---

## 현재 상태 요약

앱 완전 동작 중. CCA 문제 생성 진행 중 (summary 모드, ~744문제 예정).

**활성 자격증**: `CCA` (Claude Certified Architect – Foundations)

**데이터 현황**:
- CCA 개념 그래프: 186 nodes, 243 edges (S3)
- CCA docs: 186/186 완료 (Skilljar 강의 기반, S3)
- CCA 문제: 생성 진행 중

---

## 완료된 기능

### 핵심 학습 기능
- 에빙하우스 스케줄 (IN_SESSION → DAY_1 → WEEK_1 → MONTH_1 → MASTERED)
- 문제 풀이 + 즉시 피드백 + 해설
- 오답 시 연관 개념 문제 10분 후 자동 추가
- AI 팔로업 질문 (Bedrock Haiku)
- 선택지 순서 매번 랜덤 셔플
- 복습 문제 + 새 문제 60:40 랜덤 혼합 출제
- **exam_id 격리**: 자격증별 문제/스케줄 완전 분리 (due 큐 포함)

### 동기부여 기능
- 연속 학습 스트릭 (🔥 N일)
- 오늘의 목표 진행 바 (5문제/일)
- 시험 D-day 카운트다운
- 도메인별 숙련도 (접기/펼치기)
- 동기부여 카드 — 자격증 효과 통계 7개 매일 로테이션 (`src/abuddy/data/motivation_cards.json`)

### 인증
- Cognito OAuth2 로그인
- refresh_token 30일 저장 → 자동 로그인 (id_token 만료 시 자동 갱신)

### 인프라
- DynamoDB 4개 테이블: questions / schedule / user-questions / user-profile
- `setup_aws.py` 재실행 안전 (Cognito 기설정 시 스킵)
- 서버 에러 토스트 알림 (HTMX + 500 에러 페이지)
- **Lambda 배포** (`deploy_lambda.py`): Docker 이미지 → ECR → Lambda Function URL
- **CloudFront** (`setup_cloudfront.py`): Lambda URL 앞단 + Cognito Callback URL 자동 업데이트

### CCA 데이터 파이프라인 ✅
- `seed_concept_graph.py --exam CCA`: claude-cert-exam-guide.json → 186개 concept 추출 → S3
- `skilljar_to_docs.py`: CCA/skilljar/ 강의 MD → concept별 키워드 매칭 → Bedrock 요약 → S3
  - Domain별 코스 매핑 하드코딩 (D1~D5)
  - `--domain`, `--force`, `--dry-run`, `--concept-id` 옵션
- `generate_questions.py --exam CCA`: summary 모드 ~744문제 생성 중

---

## 다음 작업 목록

| # | 항목 | 상태 | 설명 |
|---|------|------|------|
| 1 | **팔로업 질문 → 문제 배치 주기화** | 미착수 | `generate_from_user_questions.py` 주기 실행 방침 결정. |
| 2 | **핸즈프리 음성 모드** | 미착수 | 문제/선택지 TTS + 음성 답변 + 음성 팔로업 질문. 설계 완료 → 아래 상세 참조. |
| TBD | **리더보드** | 미착수 | 주간 풀이 수 기준 멀티유저 랭킹. |
| done | **문제 이중 언어 생성** | ✅ 완료 | 동일 문제를 영어 + 한국어(용어는 영어 유지) 두 버전으로 생성. 언어 선택 UI 추가. |
| done | **AWS / Claude 자격증 데이터 완전 분리** | ✅ 완료 | exam_id로 S3 경로·DynamoDB·스케줄 큐 완전 격리. `ACTIVE_EXAM` env var로 활성 자격증 전환. |
| done | **Claude 자격증 집중 전환** | ✅ 완료 | CCA (Claude Certified Architect Foundations) 중심으로 전환. exam_id=`CCA`. |
| done | **CCA 자료 구조화 및 docs 생성** | ✅ 완료 | 개념 그래프 seed + Skilljar 강의 기반 docs 186개 생성. `skilljar_to_docs.py` 신규 작성. |
| done | **CCA 문제 전체 생성** | ✅ 완료 | summary 모드 ~744문제. `generate_questions.py --exam CCA` |
| done | **버그: 정답+불확실 문제 즉시 재출제** | ✅ 완료 | `quiz_engine.py` — `interval_step=IN_SESSION`으로 저장돼 10분 후 due 재포함 → 방금 푼 문제 다시 출제 가능. |
| done | **버그: self_confirmed 첫 정답 advance** | ✅ 완료 | `self_confirmed=True`이면 첫 정답에서도 advance. 최소 1회 10분 재확인 없이 넘어감. |
| done | **DynamoDB scan 개선** | ✅ 완료 | `list_all_question_ids()` full scan → pagination 처리 + 메모리 캐시. |
| done | **모바일 스타일 개선** | ✅ 완료 | Tailwind CSS 도입. 폰트 크기·선택지 탭 크기 모바일 최적화. |
| done | **테스트** | ✅ 완료 | pytest 설정 있으나 tests/ 없음. quiz_engine, schedule, bedrock 우선. |

---

## 핸즈프리 터치 모드 설계

### 목표
이어폰으로 들으면서 화면을 보지 않고 터치만으로 문제 풀기. 갤럭시(Android Chrome) 우선, 모든 환경 지원.

### 전체 흐름

```
[터치 모드 버튼] 클릭 → Wake Lock 활성화 → 전체화면 오버레이
  → [TTS] 문제 텍스트 읽기 (여성)
  → [TTS] 선택지 A, B, C, D... 읽기 (A/C/E=남성, B/D=여성)
  → [TAP] 답 입력 대기
  → [TTS] "A 선택" 확인 읽기 (여성) → HTMX 제출
  → [TTS] 정답/오답 + 해설 읽기 (남성)
  → [TAP] 1회 → 다음 문제
  → ...
```

### TTS: edge-tts (서버사이드) + S3 영구 캐시

**선택 이유**: 브라우저/OS별 목소리 차이 없음. 모든 환경에서 `<audio>` 태그로 균일하게 재생. 한국어 품질 우수.

```
클라이언트: GET /api/tts?text=...&voice=SunHi
  → 서버: S3 캐시 HIT → presigned URL 반환 (즉시)
         S3 캐시 MISS → edge-tts 생성 → S3 저장 → URL 반환 (~0.5초)
  → <audio src="..."> 재생
```

**목소리 배정**:
| 콘텐츠 | 목소리 |
|--------|--------|
| 문제 텍스트 | 여성 `ko-KR-SunHiNeural` |
| 선택지 A, C, E | 남성 `ko-KR-InJoonNeural` |
| 선택지 B, D | 여성 `ko-KR-SunHiNeural` |
| 피드백 (정답/오답 + 해설) | 남성 `ko-KR-InJoonNeural` |
| 안내 문구 ("A 선택", "다음 선택", "다음 문제" 등) | 여성 `ko-KR-SunHiNeural` |

**캐시 전략**:
| 콘텐츠 | 캐시 키 | 정책 |
|--------|---------|------|
| 문제/선택지 텍스트 | `{exam_id}/tts/q_{id}_{voice}_{lang}.mp3` | 영구 캐시 |
| 고정 안내 문구 | `tts/phrase_{name}.mp3` | 영구 캐시 (사전 생성) |
| 피드백 해설 | `{exam_id}/tts/exp_{id}_{lang}.mp3` | 영구 캐시 |

**사전 생성 고정 문구** (`scripts/prefetch_tts.py`):
- 여성: "A 선택", "B 선택", "C 선택", "D 선택", "E 선택", "모르겠어요", "다음 선택", "다음 문제"
- 남성: "정답입니다", "오답입니다. 정답은"

### Wake Lock (화면 보호 방지)

```javascript
// 터치 모드 진입 시
const wakeLock = await navigator.wakeLock.request('screen');
// 터치 모드 종료 시
await wakeLock.release();
```
Android Chrome, iOS Safari 16.4+ 지원.

### 터치 입력 상태 머신

**탭 판별**: 첫 탭 후 800ms 타임아웃 → 추가 탭 누적 → 최종 횟수 결정  
**스와이프 판별**: touchstart → touchend X 이동 > 80px (왼쪽) → 취소

| 상태 | 탭 1회 | 탭 2회 | 탭 N회 | 왼쪽 스와이프 | 길게 누르기(1.5초) |
|------|--------|--------|--------|--------------|-------------------|
| `TTS_READING` | 현재 문장 스킵 | 현재 문장 다시 읽기 | — | — | — |
| `WAITING_ANSWER` (MC) | A 선택·제출 | B 선택·제출 | N번째 선택·제출 | 취소(재입력) | 모르겠어요·제출 |
| `WAITING_ANSWER` (MR) | 첫 선택지 추가 | — | N번째 선택지 추가 | 직전 선택 취소 | 선택 완료·제출 |
| `MR_SELECTING` | 다음 선택지 추가 | — | N번째 선택지 추가 | 직전 선택 취소 | 선택 완료·제출 |
| `FEEDBACK_READING` | 스킵 | 다시 읽기 | — | — | — |
| `FEEDBACK_DONE` | 다음 문제 | — | — | — | — |

**MR 흐름 예시** (2개 선택 문제):
```
탭 2회 → "B 선택. 다음 선택." (여성) → MR_SELECTING 상태
탭 4회 → "D 선택. B, D. 완료하려면 길게 누르세요." (여성)
길게 누르기 → 제출
```

**MR 중복 선택**: 무시 (이미 선택된 것 재선택 시 아무 동작 없음)

### UI 구조

- **진입**: 퀴즈 화면 상단 이어폰 아이콘 버튼
- **오버레이**: 화면 전체 반투명 레이어 (기존 클릭 인터페이스 모두 차단)
- **상단 좌측**: X 버튼 (항상 활성화, 터치 모드 종료)
- **화면 중앙**: 현재 상태 텍스트 ("읽는 중...", "탭하여 선택", "A, D 선택됨" 등)
- 팔로업 질문: 터치 모드에서 비활성화 (STT 단계에서 구현)

### 새로 필요한 API

```
GET  /api/tts?text=...&voice=SunHi&cache_key=...  → { url: "s3-presigned..." }
```

### 구현 단계

| 단계 | 작업 |
|------|------|
| 1 | `edge-tts` 의존성 추가 + `/api/tts` 엔드포인트 (S3 캐시) |
| 2 | 기존 `window.speechSynthesis` → `<audio>` 태그 교체 (일반 TTS 버튼) |
| 3 | `scripts/prefetch_tts.py` — 고정 안내 문구 사전 생성 |
| 4 | 터치 모드 오버레이 UI + Wake Lock + 상태 머신 (JS) |
| 5 | 문제/선택지/피드백 TTS 자동 재생 연결 |
| 6 | 탭 카운팅 → 선택지 매핑 → HTMX 제출 연결 |
| 7 | 피드백 TTS (정답/오답+해설) → FEEDBACK_DONE → 다음 문제 |

### 환경 변수 추가 필요

```
GROQ_API_KEY=...          # STT fallback용
TTS_VOICE_KO=ko-KR-SunHiNeural
TTS_VOICE_EN=en-US-AriaNeural
TTS_S3_PREFIX=tts/        # s3://abuddy-data/tts/
```

---

## 아키텍처

### 기술 스택
| 계층 | 선택 |
|------|------|
| 웹 프레임워크 | FastAPI + HTMX + Jinja2 (SSR) |
| 인증 | Cognito Hosted UI (OAuth2 authorization code flow) |
| LLM | Bedrock Claude Sonnet (개념 추출, 요약, 문제 생성) + Haiku (팔로업 답변) |
| 개념 그래프 | S3 JSON + networkx DiGraph (메모리 캐시) |
| 문제 DB | DynamoDB `abuddy-questions` (PK=question_id, exam_id 속성으로 격리) |
| 스케줄 DB | DynamoDB `abuddy-schedule` (PK=user_id, SK=question_id) |
| 배포 | Lambda (Docker 이미지) + CloudFront |
| 패키지 관리 | uv |
| Lint | ruff |
| 로깅 | loguru |

### S3 저장 구조

```
s3://abuddy-data/
  CCA/
    graph/concept_graph.json       ← 186 nodes, 243 edges
    docs/{concept_id}.json         ← summary + chunks + pages (Skilljar 기반)
  aip-c01/
    graph/concept_graph.json
    docs/{concept_id}.json         ← summary + chunks + pages (Tavily 기반)
```

**docs JSON 포맷**:
```json
{
  "concept_id": "d1-agentic-loop",
  "concept_name": "Agentic Loop",
  "summary": "...(200-300 words, 시험 핵심 압축)...",
  "chunks": [
    {
      "chunk_id": "d1-agentic-loop_p0_c0",
      "page_index": 0,
      "chunk_index": 0,
      "heading": "...",
      "content": "...(~800자)...",
      "char_count": 650
    }
  ],
  "pages": [
    {"url": "https://anthropic.skilljar.com/...", "title": "...", "content": "..."}
  ],
  "fetched_at": "...",
  "summarized_at": "...",
  "chunked_at": "..."
}
```

### 핵심 흐름

```
skilljar_to_docs.py (CCA)
  → CCA/skilljar/{course}/*.md 로드
  → concept별 키워드 매칭으로 레슨 선택
  → Bedrock Sonnet으로 요약 생성
  → S3 CCA/docs/{concept_id}.json 저장

generate_questions.py
  → S3에서 개념 그래프 + docs(summary/chunks) 로드
  → Bedrock Haiku로 MC/MR 문제 생성
  → DynamoDB abuddy-questions 저장 (exam_id 태깅)

웹앱 (Lambda)
  → /          → 통계 대시보드
  → /quiz      → 다음 문제 (에빙하우스 우선순위, exam_id 격리)
  → POST /quiz/{id}/answer → 채점 + 스케줄 업데이트 (HTMX)
  → POST /quiz/{id}/ask   → 팔로업 질문 (Bedrock, HTMX)
  → /stats     → 진도 현황
```

### 에빙하우스 스케줄 규칙
- **간격**: IN_SESSION(10분) → DAY_1(1일) → WEEK_1(7일) → MONTH_1(30일) → MASTERED
- **오답**: 1일 후 리셋 + 연관 concept 문제 10분 큐 등록
- **정답+불확실**: 10분 후 재확인 (advance 없음)
- **마스터**: EASY=2, MEDIUM=3, HARD=4 연속 정답 + self_confirmed=True

---

## 파일 구조

```
abuddy/
├── claude-cert-exam-guide.json      ✅ CCA 시험 가이드 JSON
├── aip-c01-exam-guide.json          ✅ AIP-C01 시험 가이드 JSON
├── CCA/skilljar/                    ✅ Skilljar 강의 MD/PDF (21개 코스)
├── docker-compose.yml               ✅
├── Dockerfile / Dockerfile.lambda   ✅
├── pyproject.toml                   ✅
├── CLAUDE.md                        ✅
├── PLAN.md                          ✅ 이 파일
├── .env / .env.example              ✅
├── scripts/
│   ├── setup_aws.py                 ✅
│   ├── deploy_lambda.py             ✅ Lambda 배포 (ACTIVE_EXAM 포함)
│   ├── setup_cloudfront.py          ✅
│   ├── seed_concept_graph.py        ✅ --exam CCA / aip-c01
│   ├── skilljar_to_docs.py          ✅ CCA Skilljar → S3 docs (신규)
│   ├── fetch_concept_docs.py        ✅ Tavily → S3 docs (aip-c01용)
│   ├── generate_questions.py        ✅ --exam CCA / aip-c01
│   ├── generate_from_user_questions.py ✅
│   ├── migrate_exam_id_claude_cert_to_CCA.py ✅ S3 경로 마이그레이션 (1회성)
│   └── migrate_questions_exam_id.py ✅
├── src/abuddy/
│   ├── config.py                    ✅ ACTIVE_EXAM 지원
│   ├── main.py                      ✅
│   ├── models/                      ✅ question, schedule, concept
│   ├── db/
│   │   ├── questions.py             ✅ exam_id 격리
│   │   └── schedule.py              ✅ exam_id 격리 (due/scheduled 필터)
│   ├── services/                    ✅ auth, bedrock, concept_graph, concept_docs, quiz_engine
│   ├── routers/                     ✅ auth, quiz
│   ├── static/                      ✅
│   └── templates/                   ✅
└── tests/                           ❌ → 미착수
```
