"""Amazon Bedrock Converse API 래퍼"""
import json

import boto3
import orjson
from loguru import logger

from abuddy.config import settings
from abuddy.models.concept import Concept
from abuddy.models.question import Difficulty, Question, QuestionType


def _client():
    return boto3.client("bedrock-runtime", region_name=settings.aws_region)


def _converse(model_id: str, system: str, user: str, max_tokens: int = 2048) -> str:
    resp = _client().converse(
        modelId=model_id,
        system=[{"text": system}],
        messages=[{"role": "user", "content": [{"text": user}]}],
        inferenceConfig={"maxTokens": max_tokens, "temperature": 0.3},
    )
    return resp["output"]["message"]["content"][0]["text"]


# ──────────────────────────────────────────────
# 문제 생성
# ──────────────────────────────────────────────

_QUESTION_SYSTEM = """\
You are an expert AWS exam question writer specializing in the AWS Certified \
Generative AI Developer Professional (AIP-C01) exam.
Write questions that match the exact style, difficulty, and format of actual AWS certification exams.
Always respond with valid JSON only, no markdown fences."""

_MC_TEMPLATE = """\
Concept: {concept_name}
Description: {description}
Related AWS services: {services}
Difficulty: {difficulty}
Domain: {domain}

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

_MR_TEMPLATE = """\
Concept: {concept_name}
Description: {description}
Related AWS services: {services}
Difficulty: {difficulty}
Domain: {domain}
Number of correct answers: {num_correct}

Write one MULTIPLE RESPONSE question (5 options A–E, exactly {num_correct} correct answers).

Return JSON:
{{
  "question_text": "A company needs to... (include 'Choose {num_correct} answers.' at the end)",
  "options": ["option A", "option B", "option C", "option D", "option E"],
  "correct_indices": [0, 1],
  "explanation": "...",
  "difficulty": "easy|medium|hard"
}}"""


def generate_question(
    concept: Concept,
    question_type: QuestionType = QuestionType.MULTIPLE_CHOICE,
    difficulty: Difficulty = Difficulty.MEDIUM,
    num_correct: int = 2,
) -> Question:
    services_str = ", ".join(concept.aws_services) if concept.aws_services else "various AWS services"

    if question_type == QuestionType.MULTIPLE_CHOICE:
        prompt = _MC_TEMPLATE.format(
            concept_name=concept.name,
            description=concept.description,
            services=services_str,
            difficulty=difficulty.value,
            domain=concept.domain,
        )
    else:
        prompt = _MR_TEMPLATE.format(
            concept_name=concept.name,
            description=concept.description,
            services=services_str,
            difficulty=difficulty.value,
            domain=concept.domain,
            num_correct=num_correct,
        )

    raw = _converse(settings.bedrock_model_id, _QUESTION_SYSTEM, prompt)
    logger.debug(f"Bedrock raw response: {raw[:200]}")

    data = orjson.loads(raw)
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
    )


# ──────────────────────────────────────────────
# 팔로업 질문 답변
# ──────────────────────────────────────────────

_FOLLOWUP_SYSTEM = """\
You are an AWS expert helping a developer prepare for the AWS Certified \
Generative AI Developer Professional exam.
Answer concisely and practically. Focus on exam-relevant knowledge.
Respond in Korean if the question is in Korean, otherwise English."""


def answer_followup(
    concept_name: str,
    question_text: str,
    correct_answer_text: str,
    user_question: str,
) -> str:
    prompt = f"""\
Exam concept: {concept_name}
Question that was asked: {question_text}
Correct answer explanation: {correct_answer_text}
User's follow-up question: {user_question}

Answer the follow-up question clearly."""
    return _converse(settings.bedrock_model_id, _FOLLOWUP_SYSTEM, prompt, max_tokens=512)


# ──────────────────────────────────────────────
# 개념 그래프 초기 시드 생성 (1회성, Sonnet 사용)
# ──────────────────────────────────────────────

_GRAPH_SYSTEM = """\
You are an AWS certification expert. Extract concepts and their relationships \
from AWS exam guide content.
Respond with valid JSON only."""

_GRAPH_PROMPT = """\
Below is content from the AWS Certified Generative AI Developer Professional exam guide.

{content}

Extract a concept graph. Return JSON:
{{
  "nodes": [
    {{
      "concept_id": "short-kebab-case-id",
      "name": "Human readable name",
      "domain": 1,
      "description": "One sentence description",
      "aws_services": ["Amazon Bedrock", "..."],
      "tags": ["rag", "retrieval", "..."]
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

Guidelines:
- Extract 30-60 distinct concepts
- source_id and target_id must reference concept_ids in nodes
- Focus on concepts that appear in exam questions"""


def extract_concept_graph(exam_guide_content: str) -> dict:
    raw = _converse(
        settings.bedrock_smart_model_id,
        _GRAPH_SYSTEM,
        _GRAPH_PROMPT.format(content=exam_guide_content[:50000]),
        max_tokens=8192,
    )
    return orjson.loads(raw)
