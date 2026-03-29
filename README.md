# ABuddy

AWS Certified Generative AI Developer Professional (AIP-C01) 자격증 준비용 **스페이스드 리피티션** 학습 웹앱.

에빙하우스 망각 곡선 기반으로 최적 타이밍에 문제를 반복 출제하고, 틀린 문제는 연관 개념까지 함께 복습시킵니다.

---

## 사용자 가이드 (End User)

### 처음 접속하면

1. Cognito 로그인 화면에서 **이메일로 계정 생성** 또는 기존 계정으로 로그인
2. 대시보드에서 현재 복습 대기 문제 수, 마스터 수, 전체 문제 수 확인
3. **문제 풀기** 버튼을 눌러 시작

### 문제 풀이 흐름

```
문제 표시
  ↓
답 선택 → 제출
  ↓
즉시 피드백 (정답/오답 + 해설)
  ↓
궁금한 점 질문 (AI 답변)   ← 이 질문은 향후 문제 은행에 추가됩니다
  ↓
다음 문제
```

**문제 유형**
- **Multiple Choice**: 4지선다, 1개 정답
- **Multiple Response**: 5지선다, 2-3개 정답 (문제에 "Choose N answers." 표시)

### 복습 스케줄

정답을 맞히면 다음 복습 시점이 자동으로 잡힙니다.

| 상태 | 다음 복습 |
|------|-----------|
| 정답 (미확인) | 10분 후 재확인 |
| 정답 + "확실히 이해했어요" | 1일 → 7일 → 30일 순으로 늘어남 |
| 오답 | 1일 후 리셋, 연관 개념 문제 10분 후 추가 출제 |
| 마스터 | 난이도별 연속 정답 달성 시 (EASY 2회 / MEDIUM 3회 / HARD 4회) |

> **복습 대기** 수가 0이면 오늘 할 학습은 끝입니다. 매일 조금씩 꾸준히 하는 것이 핵심입니다.

### AI 질문 기능

답변 화면 하단의 **"궁금한 점이 있으신가요?"** 입력창에 자유롭게 질문할 수 있습니다.

- 해당 개념 + 문제 컨텍스트를 인식해 답변
- 한국어 질문 → 한국어 답변, 영어 질문 → 영어 답변
- 추가 질문도 이어서 가능
- 질문 내용은 운영자가 새 문제를 생성하는 데 활용됩니다

### 진도 확인

상단 **"진도 확인"** 메뉴에서 확인 가능:

| 항목 | 설명 |
|------|------|
| 마스터한 문제 | 완전히 익힌 문제 수 |
| 지금 복습 대기 | 지금 풀어야 할 문제 수 |
| 학습 시작한 문제 | 한 번이라도 풀어본 문제 수 |
| 전체 문제 수 | 문제 은행 전체 크기 |
| 마스터 진행률 | 학습 시작 문제 중 마스터 비율 |

---

## 운영자 가이드 (Operator)

### 아키텍처

```
┌─────────────────────────────────────────────────┐
│ 사용자 브라우저                                   │
│  FastAPI + HTMX (서버사이드 렌더링, Jinja2)       │
└───────────────┬─────────────────────────────────┘
                │
┌───────────────▼─────────────────────────────────┐
│ EC2 (Docker)                                     │
│  abuddy FastAPI app (:8002)                      │
└──┬────────┬──────────┬──────────────────────────┘
   │        │          │
   ▼        ▼          ▼
Cognito  DynamoDB    Bedrock
(인증)  (문제/스케줄)  (LLM)
              │
              ▼
             S3
        (개념 그래프)
```

**AWS 서비스**

| 서비스 | 용도 |
|--------|------|
| Cognito | 사용자 인증 (Hosted UI, OAuth2 code flow) |
| Bedrock Claude Haiku | 팔로업 질문 답변 (일상 작업) |
| Bedrock Claude Sonnet | 개념 추출, 문제 생성 (배치 작업) |
| DynamoDB `abuddy-questions` | 전체 공유 문제 은행 |
| DynamoDB `abuddy-schedule` | 유저별 에빙하우스 스케줄 |
| DynamoDB `abuddy-user-questions` | 사용자 팔로업 질문 수집 |
| S3 `abuddy-data` | 개념 그래프 JSON 저장 |

---

### 최초 설정

#### 1. 의존성 설치

```bash
uv sync
```

#### 2. AWS 리소스 생성 (최초 1회)

```bash
uv run scripts/setup_aws.py http://YOUR_EC2_IP
```

생성되는 리소스:
- S3 버킷 `abuddy-data`
- DynamoDB 테이블 3개 (`abuddy-questions`, `abuddy-schedule`, `abuddy-user-questions`)
- Cognito User Pool + App Client
- EC2 IAM 인스턴스 프로파일 `abuddy-ec2-role`

출력되는 Cognito 값을 `.env`에 복사합니다.

#### 3. 환경 변수 설정

`.env.example`을 복사해 `.env` 작성:

```bash
cp .env.example .env
```

| 변수 | 설명 |
|------|------|
| `AWS_REGION` | AWS 리전 (기본: `ap-northeast-2`) |
| `COGNITO_USER_POOL_ID` | `setup_aws.py` 출력값 |
| `COGNITO_CLIENT_ID` | `setup_aws.py` 출력값 |
| `COGNITO_CLIENT_SECRET` | `setup_aws.py` 출력값 |
| `COGNITO_DOMAIN` | `setup_aws.py` 출력값 |
| `APP_BASE_URL` | EC2 공인 IP 또는 도메인 (예: `http://1.2.3.4`) |
| `TAVILY_API_KEY` | AWS 문서 수집 시 필요 ([app.tavily.com](https://app.tavily.com)) |

> EC2 배포 시 IAM 인스턴스 프로파일(`abuddy-ec2-role`)로 인증하므로 `AWS_ACCESS_KEY_ID` 불필요.

---

### 데이터 파이프라인 (최초 1회)

문제 은행을 구축하는 순서입니다.

```
시험 가이드 JSON
  ↓ seed_concept_graph.py
개념 그래프 (S3)
  ↓ fetch_concept_docs.py  (선택)
AWS 문서 청크 (S3)
  ↓ generate_questions.py
문제 은행 (DynamoDB)
```

#### Step 1. 개념 그래프 생성

```bash
uv run scripts/seed_concept_graph.py
```

AIP-C01 시험 가이드에서 259개 개념과 연관 관계를 추출해 `s3://abuddy-data/graph/concept_graph.json`에 저장합니다. Bedrock Sonnet 사용 (1회성).

#### Step 2. AWS 문서 수집 (선택)

```bash
uv run scripts/fetch_concept_docs.py
```

각 개념별 AWS 공식 문서를 수집해 S3에 저장합니다. `TAVILY_API_KEY` 필요.

#### Step 3. 문제 생성

```bash
# 전체 개념 (summary 모드: 개념당 3문제)
uv run scripts/generate_questions.py

# 특정 도메인만
uv run scripts/generate_questions.py --domain 1 --limit 5

# AWS 문서 섹션별 심화 문제 (chunk 모드)
uv run scripts/generate_questions.py --mode chunk

# 전체 모드
uv run scripts/generate_questions.py --mode all
```

---

### 운영 중 문제 은행 확장

사용자들이 질문한 내용을 주기적으로 새 문제로 변환합니다.

```bash
# 미처리 팔로업 질문 확인 (저장만, 생성 안 함)
uv run scripts/generate_from_user_questions.py --dry-run

# 실제 변환 (기본 최대 50개)
uv run scripts/generate_from_user_questions.py

# 처리 개수 지정
uv run scripts/generate_from_user_questions.py --limit 20
```

변환 흐름:
1. `abuddy-user-questions` 테이블에서 미처리 질문 조회
2. 사용자 질문 + 컨텍스트로 Bedrock Sonnet이 MC 문제 생성
3. `abuddy-questions`에 저장 (`source="user_question"`)
4. 처리 완료 표시 (`processed=true`)

---

### 서버 실행

#### 로컬 개발

```bash
uv run uvicorn abuddy.main:app --reload --app-dir src --port 8002
```

#### Docker (로컬)

```bash
docker compose up --build
```

#### EC2 배포

```bash
# EC2에서
git pull
docker compose up -d --build
```

IAM 인스턴스 프로파일이 있으면 `.env`에 AWS 키 불필요합니다.

---

### 코드 품질

```bash
uv run ruff check src/
uv run ruff format src/
```

---

### DynamoDB 테이블 구조

#### `abuddy-questions`

| 키 | 타입 | 설명 |
|----|------|------|
| `question_id` (PK) | String | UUID |
| `concept_id` | String | 개념 ID |
| `domain` | Number | 시험 도메인 (1-5) |
| `difficulty` | String | `easy` / `medium` / `hard` |
| `question_type` | String | `multiple_choice` / `multiple_response` |
| `question_text` | String | 문제 본문 |
| `options` | List | 선택지 텍스트 배열 |
| `correct_indices` | List | 정답 인덱스 (0-based) |
| `num_correct` | Number | 정답 개수 |
| `explanation` | String | 해설 |
| `source` | String | `generated` / `user_question` / `official` |

#### `abuddy-schedule`

| 키 | 타입 | 설명 |
|----|------|------|
| `user_id` (PK) | String | Cognito sub |
| `question_id` (SK) | String | UUID |
| `interval_step` | Number | 0=10분, 1=1일, 2=7일, 3=30일, 4=마스터 |
| `next_review_at` | Number | Unix timestamp |
| `consecutive_correct` | Number | 연속 정답 수 |
| `is_mastered` | Boolean | 마스터 여부 |

#### `abuddy-user-questions`

| 키 | 타입 | 설명 |
|----|------|------|
| `uq_id` (PK) | String | UUID |
| `user_id` | String | 질문한 사용자 |
| `parent_question_id` | String | 문제 풀이 중이던 문제 ID |
| `concept_id` | String | 관련 개념 ID |
| `domain` | Number | 시험 도메인 |
| `parent_question_text` | String | 문제 본문 (컨텍스트) |
| `user_question` | String | 사용자가 남긴 질문 |
| `llm_answer` | String | AI가 답한 내용 |
| `created_at` | String | ISO 8601 타임스탬프 |
| `processed` | Boolean | 문제 은행 변환 완료 여부 |
