# ABuddy

AI 자격증 준비용 **스페이스드 리피티션** 학습 웹앱.

에빙하우스 망각 곡선 기반으로 최적 타이밍에 문제를 반복 출제하고, 틀린 문제는 연관 개념까지 함께 복습시킵니다.

**지원 자격증**
| ID | 자격증 |
|----|--------|
| `CCA` | Claude Certified Architect – Foundations (CCA-F) |
| `aip-c01` | AWS Certified AI Practitioner (AIP-C01) |

---

## 사용자 가이드 (End User)

### 처음 접속하면

1. Cognito 로그인 화면에서 **이메일로 계정 생성** 또는 기존 계정으로 로그인
2. 로그인 후 30일간 자동 로그인 유지 (재로그인 불필요)
3. 홈 화면에서 **시험일 설정** → D-day 카운트다운 표시
4. **문제 풀기** 버튼을 눌러 시작

### 홈 대시보드

```
[💡 이 내용을 공부하면 좋아요]   ← 매일 다른 자격증 효과 통계 표시
[        문제 풀기 버튼         ]

[🔥 연속 학습 중  |  🎯 오늘의 목표]
[📊 도메인별 숙련도 ▾]            ← 클릭하면 5개 도메인 진행률 펼쳐짐

[복습대기 | 마스터 | 전체문제 | D-day]
```

| 항목 | 설명 |
|------|------|
| 🔥 연속 학습 | 매일 1문제 이상 풀면 스트릭 유지. 하루 빠지면 1로 리셋 |
| 🎯 오늘의 목표 | 하루 5문제 목표 달성 진행률 |
| D-day | 홈 화면에서 시험일 직접 입력 |
| 도메인별 숙련도 | 5개 시험 도메인별 마스터 비율 |
| 동기부여 카드 | 자격증 취득 효과 통계 7개 중 매일 하나씩 표시 |

### 문제 풀이 흐름

```
문제 표시 (선택지 순서는 매번 랜덤)
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

> 복습 문제와 새 문제가 자연스럽게 섞여서 출제됩니다. 별도 복습 모드 없음.

### 복습 스케줄

정답을 맞히면 다음 복습 시점이 자동으로 잡힙니다.

| 상태 | 다음 복습 |
|------|-----------|
| 정답 (미확인) | 10분 후 재확인 |
| 정답 + "확실히 이해했어요" | 1일 → 7일 → 30일 순으로 늘어남 |
| 오답 | 1일 후 리셋, 연관 개념 문제 10분 후 추가 출제 |
| 마스터 | 난이도별 연속 정답 달성 시 (EASY 2회 / MEDIUM 3회 / HARD 4회) |

### AI 질문 기능

답변 화면 하단의 **"궁금한 점이 있으신가요?"** 입력창에 자유롭게 질문할 수 있습니다.

- 해당 개념 + 문제 컨텍스트를 인식해 답변
- 한국어/영어 모두 가능
- 질문 내용은 운영자가 새 문제를 생성하는 데 활용됩니다

### 진도 확인

상단 **"진도 확인"** 메뉴:

| 항목 | 설명 |
|------|------|
| 마스터한 문제 | 완전히 익힌 문제 수 |
| 지금 복습 대기 | 지금 풀어야 할 문제 수 |
| 학습 시작한 문제 | 한 번이라도 풀어본 문제 수 |
| 전체 문제 수 | 문제 은행 전체 크기 |
| 마스터 진행률 | 학습 시작 문제 중 마스터 비율 |
| 도메인별 숙련도 | 5개 시험 도메인별 진행률 |

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
│ AWS Lambda (Docker 이미지, ECR)                  │
│  abuddy FastAPI app (Mangum ASGI 어댑터)         │
└──┬────────┬──────────┬──────────────────────────┘
   │        │          │
   ▼        ▼          ▼
Cognito  DynamoDB    Bedrock
(인증)  (문제/스케줄)  (LLM)
              │
              ▼
             S3
     (개념 그래프 + docs)
```

**AWS 서비스**

| 서비스 | 용도 |
|--------|------|
| Lambda | 앱 서버 (Docker 이미지, Function URL) |
| ECR | Lambda용 Docker 이미지 저장소 |
| CloudFront | Lambda Function URL 앞단 (짧은 URL, HTTPS) |
| Cognito | 사용자 인증 (Hosted UI, OAuth2 code flow) |
| Bedrock Claude Haiku | 팔로업 질문 답변, 문제 생성 (일상 작업) |
| Bedrock Claude Sonnet | 개념 추출, docs 요약 (배치 작업) |
| DynamoDB `abuddy-questions` | 전체 공유 문제 은행 (`exam_id`로 자격증 격리) |
| DynamoDB `abuddy-schedule` | 유저별 에빙하우스 스케줄 |
| DynamoDB `abuddy-user-questions` | 사용자 팔로업 질문 수집 |
| DynamoDB `abuddy-user-profile` | 유저별 스트릭·시험일·오늘 풀이 수 |
| S3 `abuddy-data` | `{exam_id}/graph/`, `{exam_id}/docs/` |

---

### 최초 설정

#### 1. 의존성 설치

```bash
uv sync
```

#### 2. AWS 리소스 생성 (최초 1회)

```bash
uv run scripts/setup_aws.py http://YOUR_DOMAIN
```

생성되는 리소스:
- S3 버킷 `abuddy-data`
- DynamoDB 테이블 4개 (`abuddy-questions`, `abuddy-schedule`, `abuddy-user-questions`, `abuddy-user-profile`)
- Cognito User Pool + App Client
- EC2 IAM 인스턴스 프로파일 `abuddy-ec2-role`

> ⚠️ `.env`에 `COGNITO_USER_POOL_ID`가 이미 있으면 Cognito 재생성을 건너뜁니다.

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
| `APP_BASE_URL` | Lambda Function URL 또는 CloudFront URL |
| `TAVILY_API_KEY` | AWS 문서 수집 시 필요 ([app.tavily.com](https://app.tavily.com)) |
| `ACTIVE_EXAM` | 활성 자격증 ID (예: `CCA`, `aip-c01`) |

> Lambda 배포 시 `ACTIVE_EXAM`을 포함한 환경변수가 자동으로 Lambda에 전달됩니다.

---

### 데이터 파이프라인

자격증별로 독립적으로 실행합니다. `--exam` 인수로 자격증을 지정합니다.

#### CCA (Claude Certified Architect) 파이프라인

```bash
# 1. 개념 그래프 생성 (Bedrock Sonnet, ~5분, 186개 concept)
uv run scripts/seed_concept_graph.py --exam CCA --exam-guide claude-cert-exam-guide.json

# 2. Skilljar 강의 콘텐츠 → S3 docs 변환 (Bedrock Sonnet, ~3분)
#    CCA/skilljar/ 의 강의 MD를 concept별로 집계해 요약 생성
uv run scripts/skilljar_to_docs.py                  # 기본값이 CCA
uv run scripts/skilljar_to_docs.py --dry-run        # 매칭 확인만
uv run scripts/skilljar_to_docs.py --force          # 전체 재생성
uv run scripts/skilljar_to_docs.py --domain 1       # 특정 도메인만 재생성

# 3. 문제 생성 (Bedrock Haiku, 186 concept × 4문제 = ~744문제)
uv run scripts/generate_questions.py --exam CCA
uv run scripts/generate_questions.py --exam CCA --mode all  # chunk 포함 ~10,167문제
```

#### AIP-C01 (AWS AI Practitioner) 파이프라인

```bash
# 1. 개념 그래프 생성
uv run scripts/seed_concept_graph.py --exam aip-c01

# 2. AWS 문서 수집 (Tavily)
uv run scripts/fetch_concept_docs.py --exam aip-c01

# 3. 문제 생성
uv run scripts/generate_questions.py --exam aip-c01
```

#### 공통 옵션

```bash
# 특정 concept만
uv run scripts/generate_questions.py --exam CCA --concept-id d1-agentic-loop

# 도메인 단위
uv run scripts/generate_questions.py --exam CCA --domain 1

# 테스트 (소량)
uv run scripts/generate_questions.py --exam CCA --limit 8
```

---

### Lambda 배포

Docker 이미지를 ECR에 올리고 Lambda에 배포합니다. **최초 실행**과 **코드 업데이트** 모두 동일 명령입니다.

**사전 준비**
- Docker Desktop 실행 중
- AWS CLI 로그인 (`aws configure` 또는 IAM 자격증명)
- `.env` 작성 완료

```bash
# 빌드 → ECR 푸시 → Lambda 생성/업데이트 → Function URL 출력
uv run scripts/deploy_lambda.py
```

최초 실행 시 생성되는 리소스:
- ECR 레포 `abuddy`
- IAM 역할 `abuddy-lambda-role` (DynamoDB / S3 / Bedrock 권한 포함)
- Lambda 함수 `abuddy` (메모리 512MB, 타임아웃 60초)
- Lambda Function URL (공개, 인증 없음)

완료 후 출력되는 **Function URL**을 `.env`의 `APP_BASE_URL`에 복사하고 재배포합니다.

```bash
# .env 수정
APP_BASE_URL=https://xxxx.lambda-url.ap-northeast-2.on.aws

# 환경변수 업데이트 반영
uv run scripts/deploy_lambda.py
```

#### CloudFront로 URL 단축

Lambda Function URL 앞에 CloudFront를 붙이면 짧고 고정된 URL을 사용할 수 있습니다.

```bash
# CloudFront distribution 생성 + Cognito Callback URL 자동 업데이트
uv run scripts/setup_cloudfront.py
```

**전체 배포 흐름**

```
1. uv run scripts/deploy_lambda.py          # Lambda 배포 + Function URL 획득
2. .env: APP_BASE_URL=<Function URL>
3. uv run scripts/deploy_lambda.py          # 환경변수 반영
4. uv run scripts/setup_cloudfront.py       # CloudFront 생성 + Cognito URL 업데이트
5. .env: APP_BASE_URL=<CloudFront URL>
6. uv run scripts/deploy_lambda.py          # 최종 환경변수 반영
```

---

### 로컬 개발

```bash
uv run uvicorn abuddy.main:app --reload --app-dir src --port 8002
```

```bash
docker compose up --build
```

---

### 운영 중 문제 은행 확장

사용자 팔로업 질문을 새 문제로 주기적으로 변환합니다.

```bash
# 미처리 질문 확인 (생성 안 함)
uv run scripts/generate_from_user_questions.py --dry-run

# 실제 변환
uv run scripts/generate_from_user_questions.py --limit 20
```

### S3 데이터 마이그레이션

```bash
# exam_id 이름 변경: claude-cert/ → CCA/ (1회성)
uv run scripts/migrate_exam_id_claude_cert_to_CCA.py             # 드라이런
uv run scripts/migrate_exam_id_claude_cert_to_CCA.py --execute --delete-old
```

### 동기부여 카드 내용 수정

```
src/abuddy/data/motivation_cards.json
```

JSON 배열에 항목을 추가/수정하면 재배포 후 반영됩니다.

---

### 코드 품질

```bash
uv run ruff check src/
uv run ruff format src/
```
