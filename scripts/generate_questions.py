#!/usr/bin/env python
"""
개념 그래프의 각 concept에 대해 문제를 생성해 DynamoDB에 저장.

모드:
  summary  — concept 전체 요약 기반, concept당 3문제 (MC medium/hard + MR medium)
  chunk    — 개별 청크 기반, 청크당 1문제 (MC medium), 세부 주제 심화
  all      — summary + chunk 모두

사용법:
  uv run scripts/generate_questions.py                        # 전체 (summary 모드)
  uv run scripts/generate_questions.py --mode chunk           # chunk 모드
  uv run scripts/generate_questions.py --mode all             # 전체
  uv run scripts/generate_questions.py --domain 1 --limit 5  # 도메인 1, 최대 5개 concept
"""
import sys

import typer
from loguru import logger

sys.path.insert(0, "src")
from abuddy.db import questions as qdb
from abuddy.models.question import Difficulty, QuestionType
from abuddy.services import bedrock
from abuddy.services.concept_docs import load_doc_chunks, load_doc_content
from abuddy.services.concept_graph import get_all_concepts

app = typer.Typer()

# AIP-C01: summary 기반 (MC + MR)
SUMMARY_PLANS_AIP = [
    (QuestionType.MULTIPLE_CHOICE, Difficulty.MEDIUM, 1),
    (QuestionType.MULTIPLE_CHOICE, Difficulty.HARD, 1),
    (QuestionType.MULTIPLE_RESPONSE, Difficulty.MEDIUM, 2),
]

# CCA: summary 기반 (MC only — CCA exam has no Multiple Response)
SUMMARY_PLANS_CCA = [
    (QuestionType.MULTIPLE_CHOICE, Difficulty.EASY, 1),
    (QuestionType.MULTIPLE_CHOICE, Difficulty.MEDIUM, 1),
    (QuestionType.MULTIPLE_CHOICE, Difficulty.HARD, 1),
]

# 청크 기반: 특정 섹션의 세부 지식을 테스트 (청크당 1문제)
CHUNK_PLANS = [
    (QuestionType.MULTIPLE_CHOICE, Difficulty.MEDIUM, 1),
]

# CCA 시나리오 난이도 플랜 (시나리오당 N문제)
SCENARIO_DIFFICULTIES = [Difficulty.MEDIUM, Difficulty.HARD, Difficulty.HARD]


@app.command()
def main(
    domain: int = typer.Option(0, help="특정 도메인만 (0=전체)"),
    limit: int = typer.Option(0, help="최대 concept 수 (0=전체)"),
    mode: str = typer.Option("summary", help="summary | chunk | all | scenario"),
    exam: str = typer.Option("CCA", "--exam", help="자격증 ID (예: CCA, aip-c01)"),
):
    if mode not in ("summary", "chunk", "all", "scenario"):
        logger.error("--mode는 summary / chunk / all / scenario 중 하나여야 합니다.")
        raise typer.Exit(1)

    concepts = get_all_concepts(exam_id=exam)
    if domain:
        concepts = [c for c in concepts if c.domain == domain]
    if limit:
        concepts = concepts[:limit]

    summary_plans = SUMMARY_PLANS_CCA if exam == "CCA" else SUMMARY_PLANS_AIP
    logger.info(f"Generating questions for {len(concepts)} concepts (mode={mode}, exam={exam})...")
    total = errors = 0

    # ── scenario 모드 (CCA 전용) ────────────────────────────
    if mode == "scenario":
        if exam != "CCA":
            logger.error("--mode scenario는 CCA 전용입니다.")
            raise typer.Exit(1)
        import json, orjson
        from pathlib import Path
        guide = orjson.loads(Path("claude-cert-exam-guide.json").read_bytes())
        scenarios = guide.get("scenarios", [])
        logger.info(f"시나리오 {len(scenarios)}개 처리 중...")
        for scenario in scenarios:
            existing = qdb.list_questions_by_concept(f"scenario-{scenario['id']}", exam_id=exam)
            existing_diffs = {q.difficulty for q in existing}
            for difficulty in SCENARIO_DIFFICULTIES:
                if difficulty in existing_diffs:
                    logger.info(f"  [scenario-{scenario['id']}] {difficulty.value} 이미 존재, 스킵")
                    continue
                try:
                    q = bedrock.generate_scenario_question(scenario, difficulty=difficulty, exam_id=exam)
                    qdb.put_question(q)
                    total += 1
                    logger.info(f"  [scenario-{scenario['id']}] {scenario['title']} {difficulty.value} → {q.question_id[:8]}")
                except Exception as e:
                    errors += 1
                    logger.error(f"  [scenario-{scenario['id']}] FAILED: {e}")
        logger.info(f"Done. Generated {total} questions, {errors} errors.")
        return

    for concept in concepts:
        # ── summary 모드 ────────────────────────────────────
        if mode in ("summary", "all"):
            existing = qdb.list_questions_by_concept(concept.concept_id, exam_id=exam)
            # chunk 기반이 아닌 summary 문제만 필터
            existing_summary = {(q.question_type, q.difficulty) for q in existing if not q.chunk_id}
            remaining_plans = [
                (q_type, difficulty, num_correct)
                for q_type, difficulty, num_correct in summary_plans
                if (q_type, difficulty) not in existing_summary
            ]
            if not remaining_plans:
                logger.info(f"[{concept.name}] summary 문제 모두 존재, 스킵")
                continue
            if len(remaining_plans) < len(summary_plans):
                logger.info(f"[{concept.name}] summary {len(existing_summary)}/{len(summary_plans)}개 존재, 나머지 {len(remaining_plans)}개 생성")
            doc_content = load_doc_content(concept.concept_id, exam_id=exam)
            if doc_content:
                logger.info(f"[{concept.name}] summary {len(doc_content)}자 로드")
            for q_type, difficulty, num_correct in remaining_plans:
                try:
                    q = bedrock.generate_question(
                        concept=concept,
                        question_type=q_type,
                        difficulty=difficulty,
                        num_correct=num_correct,
                        doc_content=doc_content,
                        exam_id=exam,
                    )
                    qdb.put_question(q)
                    total += 1
                    logger.info(
                        f"  [summary] {q_type.value} {difficulty.value} → {q.question_id[:8]}"
                    )
                except Exception as e:
                    errors += 1
                    logger.error(f"  [summary] {q_type.value} FAILED: {e}")

        # ── chunk 모드 ──────────────────────────────────────
        if mode in ("chunk", "all"):
            existing_chunk_ids = {q.chunk_id for q in qdb.list_questions_by_concept(concept.concept_id, exam_id=exam) if q.chunk_id}
            chunks = load_doc_chunks(concept.concept_id, exam_id=exam)
            if not chunks:
                logger.warning(f"[{concept.name}] 청크 없음, chunk 모드 스킵")
                continue
            chunks_to_process = [c for c in chunks if c["chunk_id"] not in existing_chunk_ids]
            if not chunks_to_process:
                logger.info(f"[{concept.name}] 모든 청크 문제 존재, 스킵")
                continue
            if existing_chunk_ids:
                logger.info(f"[{concept.name}] {len(existing_chunk_ids)}/{len(chunks)}개 청크 존재, 나머지 {len(chunks_to_process)}개 처리 중...")
            else:
                logger.info(f"[{concept.name}] {len(chunks_to_process)}개 청크 처리 중...")
            for chunk in chunks_to_process:
                for q_type, difficulty, num_correct in CHUNK_PLANS:
                    try:
                        q = bedrock.generate_question(
                            concept=concept,
                            question_type=q_type,
                            difficulty=difficulty,
                            num_correct=num_correct,
                            doc_content=chunk["content"],
                            chunk_heading=chunk["heading"],
                            chunk_id=chunk["chunk_id"],
                            exam_id=exam,
                        )
                        qdb.put_question(q)
                        total += 1
                        logger.info(
                            f"  [chunk {chunk['chunk_id']}] {chunk['heading'][:40]}"
                            f" → {q.question_id[:8]}"
                        )
                    except Exception as e:
                        errors += 1
                        logger.error(
                            f"  [chunk {chunk['chunk_id']}] FAILED: {e}"
                        )

    logger.info(f"Done. Generated {total} questions, {errors} errors.")


if __name__ == "__main__":
    app()
