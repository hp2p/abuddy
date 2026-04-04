"""Amazon Bedrock Converse API 래퍼"""
import boto3
import orjson
from botocore.config import Config
from loguru import logger

from abuddy.config import settings
from abuddy.models.concept import Concept
from abuddy.models.question import Difficulty, Question, QuestionType


def _client(read_timeout: int = 120):
    return boto3.client(
        "bedrock-runtime",
        region_name=settings.aws_region,
        config=Config(read_timeout=read_timeout, connect_timeout=10),
    )


def _converse(model_id: str, system: str, user: str, max_tokens: int = 2048, read_timeout: int = 120) -> str:
    resp = _client(read_timeout).converse(
        modelId=model_id,
        system=[{"text": system}],
        messages=[{"role": "user", "content": [{"text": user}]}],
        inferenceConfig={"maxTokens": max_tokens, "temperature": 0.3},
    )
    return resp["output"]["message"]["content"][0]["text"]


def _strip_code_fence(raw: str) -> str:
    """Remove markdown ```json ... ``` fences from LLM output."""
    s = raw.strip()
    if s.startswith("```"):
        s = s.split("\n", 1)[1] if "\n" in s else s[3:]
        if s.endswith("```"):
            s = s[: s.rfind("```")]
    return s.strip()


# ──────────────────────────────────────────────
# 문제 생성
# ──────────────────────────────────────────────

_QUESTION_SYSTEM_AIP = """\
You are an expert AWS exam question writer specializing in the AWS Certified \
Generative AI Developer Professional (AIP-C01) exam.
Write questions that match the exact style, difficulty, and format of actual AWS certification exams.
Always respond with valid JSON only, no markdown fences."""

_QUESTION_SYSTEM_CCA = """\
You are an expert exam question writer specializing in the Claude Certified Architect – Foundations (CCA-F) exam.
Write questions that match the exact style, difficulty, and format of the actual CCA-F certification exam.
Questions should focus on Claude APIs, Agent SDK, MCP, prompt engineering, and Claude Code — not AWS services.
Always respond with valid JSON only, no markdown fences."""

_MC_TEMPLATE_AIP = """\
Concept: {concept_name}
Description: {description}
Related AWS services: {services}
Difficulty: {difficulty}
Domain: {domain}
{doc_section}
Write one MULTIPLE CHOICE question (4 options A–D, exactly 1 correct answer).

Return JSON:
{{
  "question_text": "...",
  "options": ["option text A", "option text B", "option text C", "option text D"],
  "correct_indices": [0],
  "explanation": "...",
  "difficulty": "easy|medium|hard"
}}

Rules:
- Options must not include A./B./C./D. prefix — plain text only
- Distractors must be plausible (real AWS services or real concepts)
- Explanation must reference the AWS official recommendation
- For Professional-level: scenario-based questions preferred"""

_MC_TEMPLATE_CCA = """\
Concept: {concept_name}
Description: {description}
Difficulty: {difficulty}
Domain: {domain}
{doc_section}
Write one MULTIPLE CHOICE question (4 options A–D, exactly 1 correct answer).

Return JSON:
{{
  "question_text": "...",
  "options": ["option text A", "option text B", "option text C", "option text D"],
  "correct_indices": [0],
  "explanation": "...",
  "difficulty": "easy|medium|hard"
}}

Rules:
- Options must not include A./B./C./D. prefix — plain text only
- Distractors must be plausible alternatives based on Claude/Anthropic concepts
- Explanation must reference the Anthropic official documentation or Claude best practices
- Scenario-based questions preferred (e.g. "A developer is building an agent with Claude...")
- Do NOT mention AWS services unless directly relevant to the concept"""

_MR_TEMPLATE_AIP = """\
Concept: {concept_name}
Description: {description}
Related AWS services: {services}
Difficulty: {difficulty}
Domain: {domain}
Number of correct answers: {num_correct}
{doc_section}

Write one MULTIPLE RESPONSE question (5 options A–E, exactly {num_correct} correct answers).

Return JSON:
{{
  "question_text": "A company needs to... (include 'Choose {num_correct} answers.' at the end)",
  "options": ["option A", "option B", "option C", "option D", "option E"],
  "correct_indices": [0, 1],
  "explanation": "...",
  "difficulty": "easy|medium|hard"
}}"""

_MR_TEMPLATE_CCA = """\
Concept: {concept_name}
Description: {description}
Difficulty: {difficulty}
Domain: {domain}
Number of correct answers: {num_correct}
{doc_section}

Write one MULTIPLE RESPONSE question (5 options A–E, exactly {num_correct} correct answers).

Return JSON:
{{
  "question_text": "A developer is building... (include 'Choose {num_correct} answers.' at the end)",
  "options": ["option A", "option B", "option C", "option D", "option E"],
  "correct_indices": [0, 1],
  "explanation": "...",
  "difficulty": "easy|medium|hard"
}}

Rules:
- Do NOT mention AWS services unless directly relevant to the concept
- Distractors must be plausible Claude/Anthropic concepts"""


def generate_question(
    concept: Concept,
    question_type: QuestionType = QuestionType.MULTIPLE_CHOICE,
    difficulty: Difficulty = Difficulty.MEDIUM,
    num_correct: int = 2,
    doc_content: str = "",
    chunk_heading: str = "",
    chunk_id: str = "",
    exam_id: str = "CCA",
) -> Question:
    is_cca = exam_id == "CCA"
    system = _QUESTION_SYSTEM_CCA if is_cca else _QUESTION_SYSTEM_AIP
    mc_template = _MC_TEMPLATE_CCA if is_cca else _MC_TEMPLATE_AIP
    mr_template = _MR_TEMPLATE_CCA if is_cca else _MR_TEMPLATE_AIP
    doc_label = "Reference Material" if is_cca else "AWS Documentation Reference"

    services_str = ", ".join(concept.aws_services) if concept.aws_services else ""
    if doc_content and chunk_heading:
        doc_section = (
            f"{doc_label} (Section: {chunk_heading}):\n"
            f"{doc_content[:2000]}\n"
            f"Focus this question specifically on the '{chunk_heading}' topic.\n"
        )
    elif doc_content:
        doc_section = f"{doc_label}:\n{doc_content[:2000]}\n"
    else:
        doc_section = ""

    if question_type == QuestionType.MULTIPLE_CHOICE:
        fmt = dict(
            concept_name=concept.name,
            description=concept.description,
            difficulty=difficulty.value,
            domain=concept.domain,
            doc_section=doc_section,
        )
        if not is_cca:
            fmt["services"] = services_str or "various AWS services"
        prompt = mc_template.format(**fmt)
    else:
        fmt = dict(
            concept_name=concept.name,
            description=concept.description,
            difficulty=difficulty.value,
            domain=concept.domain,
            num_correct=num_correct,
            doc_section=doc_section,
        )
        if not is_cca:
            fmt["services"] = services_str or "various AWS services"
        prompt = mr_template.format(**fmt)

    raw = _converse(settings.bedrock_smart_model_id, system, prompt)
    logger.debug(f"Bedrock raw response: {raw[:200]}")

    data = orjson.loads(_strip_code_fence(raw))
    return Question(
        concept_id=concept.concept_id,
        domain=concept.domain,
        difficulty=Difficulty(data.get("difficulty", difficulty.value)),
        question_type=question_type,
        question_text=data["question_text"],
        options=data["options"],
        correct_indices=data["correct_indices"],
        num_correct=num_correct if question_type == QuestionType.MULTIPLE_RESPONSE else 1,
        explanation=data["explanation"],
        source="generated",
        chunk_id=chunk_id,
        exam_id=exam_id,
    )


# ──────────────────────────────────────────────
# CCA 시나리오 문제 생성
# ──────────────────────────────────────────────

_SCENARIO_SYSTEM = """\
You are an expert exam question writer specializing in the Claude Certified Architect – Foundations (CCA-F) exam.
Write scenario-based Multiple Choice questions that test architectural decision-making with Claude APIs.
Always respond with valid JSON only, no markdown fences."""

_SCENARIO_TEMPLATE = """\
Scenario: {scenario_title}
Description: {scenario_description}
Key skills tested: {key_skills}
Difficulty: {difficulty}

Write one MULTIPLE CHOICE question (4 options A–D, exactly 1 correct answer) that:
- Is grounded in the scenario context above
- Tests one of the key skills listed
- Presents a realistic architectural decision or implementation choice

Return JSON:
{{
  "question_text": "...(reference the scenario context)...",
  "options": ["option A", "option B", "option C", "option D"],
  "correct_indices": [0],
  "explanation": "...",
  "difficulty": "easy|medium|hard"
}}

Rules:
- Options must not include A./B./C./D. prefix — plain text only
- Distractors must represent common architectural mistakes or anti-patterns
- Do NOT mention AWS services unless directly relevant"""


def generate_scenario_question(
    scenario: dict,
    difficulty: Difficulty = Difficulty.HARD,
    exam_id: str = "CCA",
) -> Question:
    """CCA 시나리오 기반 MC 문제 생성."""
    prompt = _SCENARIO_TEMPLATE.format(
        scenario_title=scenario["title"],
        scenario_description=scenario["description"],
        key_skills=", ".join(scenario.get("key_skills", [])),
        difficulty=difficulty.value,
    )
    raw = _converse(settings.bedrock_smart_model_id, _SCENARIO_SYSTEM, prompt)
    data = orjson.loads(_strip_code_fence(raw))
    concept_id = f"scenario-{scenario['id']}"
    domain = scenario.get("primary_domains", [0])[0]
    return Question(
        concept_id=concept_id,
        domain=domain,
        difficulty=Difficulty(data.get("difficulty", difficulty.value)),
        question_type=QuestionType.MULTIPLE_CHOICE,
        question_text=data["question_text"],
        options=data["options"],
        correct_indices=data["correct_indices"],
        num_correct=1,
        explanation=data["explanation"],
        source="generated",
        chunk_id="",
        exam_id=exam_id,
    )


# ──────────────────────────────────────────────
# AWS 문서 요약 (fetch_concept_docs.py용, 1회성)
# ──────────────────────────────────────────────

_SUMMARIZE_SYSTEM = """\
You are an AWS certification expert. Summarize AWS documentation for exam preparation.
Be concise and focus on exam-relevant facts."""

_SUMMARIZE_TEMPLATE = """\
Concept: {concept_name}
Target exam: AWS Certified Generative AI Developer Professional (AIP-C01)

AWS Documentation:
{raw_content}

Summarize the above documentation in 200-300 words. Focus on:
- What this concept is and how it works
- Key configuration options or limits relevant to the exam
- Differences from similar AWS services
- Common use cases and when to choose this over alternatives

Write in plain English. No markdown headers."""


def summarize_doc_content(concept_name: str, raw_content: str) -> str:
    """수집된 AWS 문서를 시험 대비용 200-300단어 요약으로 압축."""
    prompt = _SUMMARIZE_TEMPLATE.format(
        concept_name=concept_name,
        raw_content=raw_content[:24000],  # 3페이지 합산 전체
    )
    return _converse(settings.bedrock_smart_model_id, _SUMMARIZE_SYSTEM, prompt, max_tokens=512)


# ──────────────────────────────────────────────
# AWS 문서 URL 제안 (fetch_concept_docs.py용)
# ──────────────────────────────────────────────

_DOC_URL_SYSTEM = """\
You are an AWS documentation expert. Return only valid JSON, no markdown fences."""

_DOC_URL_TEMPLATE = """\
For the AWS concept below, list 2-3 specific AWS documentation pages that contain \
the most authoritative and detailed content about this concept.

Concept: {concept_name}
Description: {description}
Related AWS services: {services}

Return JSON:
{{"urls": ["https://docs.aws.amazon.com/...", ...]}}

Rules:
- Use only docs.aws.amazon.com URLs
- Prefer user guides and "What is X" / "How X works" pages over API references
- Use only URLs you are highly confident exist. Known valid patterns:
  * https://docs.aws.amazon.com/bedrock/latest/userguide/PAGENAME.html
  * https://docs.aws.amazon.com/sagemaker/latest/dg/PAGENAME.html
  * https://docs.aws.amazon.com/kendra/latest/dg/PAGENAME.html
  * https://docs.aws.amazon.com/opensearch-service/latest/developerguide/PAGENAME.html
- Return 2-3 URLs maximum"""


def suggest_doc_urls(concept: Concept) -> list[str]:
    """concept에 대한 관련 AWS 문서 URL 2-3개를 제안."""
    services_str = ", ".join(concept.aws_services) if concept.aws_services else "various AWS services"
    prompt = _DOC_URL_TEMPLATE.format(
        concept_name=concept.name,
        description=concept.description,
        services=services_str,
    )
    raw = _converse(settings.bedrock_model_id, _DOC_URL_SYSTEM, prompt, max_tokens=512)
    data = orjson.loads(_strip_code_fence(raw))
    return data.get("urls", [])


# ──────────────────────────────────────────────
# 팔로업 질문 답변
# ──────────────────────────────────────────────

_FOLLOWUP_SYSTEM_CCA = """\
You are a Claude/Anthropic expert helping a developer prepare for the \
Claude Certified Architect Foundations (CCA) exam.
Answer concisely and practically. Focus on exam-relevant knowledge about Claude, \
Claude Code, MCP, prompt engineering, and the Anthropic ecosystem.
Respond in Korean if the question is in Korean, otherwise English."""

_FOLLOWUP_SYSTEM_AIP = """\
You are an AWS expert helping a developer prepare for the AWS Certified \
Generative AI Developer Professional exam.
Answer concisely and practically. Focus on exam-relevant knowledge.
Respond in Korean if the question is in Korean, otherwise English."""


def answer_followup(
    concept_name: str,
    question_text: str,
    correct_answer_text: str,
    user_question: str,
    exam_id: str | None = None,
) -> str:
    prompt = f"""\
Exam concept: {concept_name}
Question that was asked: {question_text}
Correct answer explanation: {correct_answer_text}
User's follow-up question: {user_question}

Answer the follow-up question clearly."""
    eid = exam_id or settings.active_exam
    system = _FOLLOWUP_SYSTEM_CCA if eid == "CCA" else _FOLLOWUP_SYSTEM_AIP
    return _converse(settings.bedrock_model_id, system, prompt, max_tokens=512)


# ──────────────────────────────────────────────
# 사용자 팔로업 질문 → 문제 생성
# ──────────────────────────────────────────────

_USER_QUESTION_SYSTEM = """\
You are an expert AI certification exam question writer.
A student asked a follow-up question while studying. Use their question as inspiration \
to create one realistic exam question that tests the same knowledge area.
Always respond with valid JSON only, no markdown fences."""

_USER_QUESTION_TEMPLATE = """\
Concept: {concept_name}
Original exam question: {parent_question_text}
Student's follow-up question: {user_question}
Expert answer given to the student: {llm_answer}

Based on the student's question, write one MULTIPLE CHOICE exam question (4 options A–D, \
exactly 1 correct answer) that tests the knowledge the student was curious about.

Return JSON:
{{
  "question_text": "...",
  "options": ["option A", "option B", "option C", "option D"],
  "correct_indices": [0],
  "explanation": "...",
  "difficulty": "easy|medium|hard"
}}

Rules:
- Options must not include A./B./C./D. prefix
- Distractors must be plausible (real concepts or tools in this domain)
- Explanation must be accurate and reference established best practices"""


def generate_question_from_user_question(
    concept: Concept,
    parent_question_text: str,
    user_question: str,
    llm_answer: str,
) -> Question:
    """사용자 팔로업 질문을 기반으로 새 MC 문제 생성."""
    prompt = _USER_QUESTION_TEMPLATE.format(
        concept_name=concept.name,
        parent_question_text=parent_question_text,
        user_question=user_question,
        llm_answer=llm_answer,
    )
    raw = _converse(settings.bedrock_smart_model_id, _USER_QUESTION_SYSTEM, prompt, max_tokens=1024)
    data = orjson.loads(_strip_code_fence(raw))
    return Question(
        concept_id=concept.concept_id,
        domain=concept.domain,
        difficulty=Difficulty(data.get("difficulty", "medium")),
        question_type=QuestionType.MULTIPLE_CHOICE,
        question_text=data["question_text"],
        options=data["options"],
        correct_indices=data["correct_indices"],
        num_correct=1,
        explanation=data["explanation"],
        source="user_question",
        chunk_id="",
    )


# ──────────────────────────────────────────────
# 문제 한글 번역 (1회성 배치, Sonnet 사용)
# ──────────────────────────────────────────────

_TRANSLATE_SYSTEM = """\
You are a technical translator specializing in IT certification exam questions.
Translate the given exam question from English to Korean.

Rules:
- Keep ALL technical terms, product names, and proper nouns in English (e.g. prompt caching, RAG, fine-tuning, Claude, Amazon Bedrock, MCP, API, SDK, JSON, HTTPS, IAM, S3, EC2, etc.)
- Translate only the natural-language parts (verbs, conjunctions, explanations)
- Preserve the original tone and exam style (formal, precise)
- Always respond with valid JSON only, no markdown fences"""

_TRANSLATE_TEMPLATE = """\
Translate the following exam question to Korean. Keep technical terms in English.

question_text: {question_text}
options: {options}
explanation: {explanation}

Return JSON:
{{
  "question_text_ko": "...",
  "options_ko": ["...", "...", "...", "..."],
  "explanation_ko": "..."
}}"""


def translate_question(question_text: str, options: list[str], explanation: str) -> dict:
    """문제·선택지·해설을 한국어로 번역. 기술 용어는 영어 유지."""
    import json
    prompt = _TRANSLATE_TEMPLATE.format(
        question_text=question_text,
        options=json.dumps(options, ensure_ascii=False),
        explanation=explanation,
    )
    raw = _converse(settings.bedrock_smart_model_id, _TRANSLATE_SYSTEM, prompt, max_tokens=2048)
    return orjson.loads(_strip_code_fence(raw))


# ──────────────────────────────────────────────
# 개념 그래프 초기 시드 생성 (1회성, Sonnet 사용)
# ──────────────────────────────────────────────

_GRAPH_SYSTEM = """\
You are an AI certification expert. Extract concepts and their relationships \
from exam guide content.
Respond with valid JSON only, no markdown fences."""

_GRAPH_PROMPT = """\
Below is Domain {domain_num} content from the {exam_name} exam guide.

{content}

Extract ALL distinct concepts from this domain. Return JSON:
{{
  "nodes": [
    {{
      "concept_id": "short-kebab-case-id",
      "name": "Human readable name",
      "domain": {domain_num},
      "description": "One sentence description",
      "tags": ["tag1", "tag2", "..."]
    }}
  ],
  "edges": [
    {{
      "source_id": "concept-id-a",
      "target_id": "concept-id-b",
      "relation": "requires|uses|part_of|similar_to",
      "weight": 1.0
    }}
  ]
}}

Rules:
- concept_id must be unique kebab-case (prefix with d{domain_num}- to avoid collisions)
- source_id and target_id must reference concept_ids in nodes above
- Extract 8-15 concepts for this domain"""

_EXAM_DISPLAY_NAMES = {
    "CCA": "Claude Certified Architect Foundations (CCA)",
    "aip-c01": "AWS Certified Generative AI Developer Professional (AIP-C01)",
}


def extract_concept_graph_for_domain(domain_num: int, content: str, exam_id: str = "CCA") -> dict:
    """단일 도메인 콘텐츠에서 개념 추출 (timeout 300s)"""
    raw = _converse(
        settings.bedrock_smart_model_id,
        _GRAPH_SYSTEM,
        _GRAPH_PROMPT.format(
            domain_num=domain_num,
            content=content[:15000],
            exam_name=_EXAM_DISPLAY_NAMES.get(exam_id, exam_id),
        ),
        max_tokens=4096,
        read_timeout=300,
    )
    return orjson.loads(_strip_code_fence(raw))
