#!/usr/bin/env python
"""
개념 그래프의 각 concept에 대해 문제를 생성해 DynamoDB에 저장.
기본: 각 concept당 MC 2개 + MR 1개 = concept당 3문제.

사용법:
  uv run scripts/generate_questions.py              # 전체 생성
  uv run scripts/generate_questions.py --domain 1   # 도메인 1만
  uv run scripts/generate_questions.py --limit 10   # 최대 10개 concept
"""
import sys
import random

import typer
from loguru import logger

sys.path.insert(0, "src")
from abuddy.db import questions as qdb
from abuddy.models.question import Difficulty, QuestionType
from abuddy.services import bedrock
from abuddy.services.concept_graph import get_all_concepts

app = typer.Typer()

DIFFICULTIES = [Difficulty.EASY, Difficulty.MEDIUM, Difficulty.HARD]
QUESTION_PLANS = [
    (QuestionType.MULTIPLE_CHOICE, Difficulty.MEDIUM, 1),
    (QuestionType.MULTIPLE_CHOICE, Difficulty.HARD, 1),
    (QuestionType.MULTIPLE_RESPONSE, Difficulty.MEDIUM, 2),
]


@app.command()
def main(
    domain: int = typer.Option(0, help="특정 도메인만 (0=전체)"),
    limit: int = typer.Option(0, help="최대 concept 수 (0=전체)"),
):
    concepts = get_all_concepts()
    if domain:
        concepts = [c for c in concepts if c.domain == domain]
    if limit:
        concepts = concepts[:limit]

    logger.info(f"Generating questions for {len(concepts)} concepts...")
    total = 0
    errors = 0

    for concept in concepts:
        for q_type, difficulty, num_correct in QUESTION_PLANS:
            try:
                q = bedrock.generate_question(
                    concept=concept,
                    question_type=q_type,
                    difficulty=difficulty,
                    num_correct=num_correct,
                )
                qdb.put_question(q)
                total += 1
                logger.info(f"  [{concept.name}] {q_type.value} {difficulty.value} → {q.question_id[:8]}")
            except Exception as e:
                errors += 1
                logger.error(f"  [{concept.name}] {q_type.value} FAILED: {e}")

    logger.info(f"Done. Generated {total} questions, {errors} errors.")


if __name__ == "__main__":
    app()
