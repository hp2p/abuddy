#!/usr/bin/env python
"""
사용자가 퀴즈 풀이 중 남긴 팔로업 질문을 기반으로 새 문제를 생성해 문제 은행에 추가.

사용법:
  uv run scripts/generate_from_user_questions.py
  uv run scripts/generate_from_user_questions.py --limit 20
  uv run scripts/generate_from_user_questions.py --dry-run
"""
import sys

import typer
from loguru import logger

sys.path.insert(0, "src")
from abuddy.db import questions as qdb
from abuddy.db import user_questions as uqdb
from abuddy.services import bedrock
from abuddy.services.concept_graph import get_concept

app = typer.Typer()


@app.command()
def main(
    limit: int = typer.Option(50, help="처리할 최대 항목 수"),
    dry_run: bool = typer.Option(False, "--dry-run", help="문제를 저장하지 않고 출력만"),
):
    items = uqdb.list_unprocessed(limit=limit)
    if not items:
        logger.info("처리할 사용자 질문이 없습니다.")
        return

    logger.info(f"{len(items)}개 사용자 질문 처리 시작...")
    total = errors = 0

    for item in items:
        uq_id = item["uq_id"]
        concept = get_concept(item["concept_id"])
        if not concept:
            logger.warning(f"[{uq_id[:8]}] concept '{item['concept_id']}' 없음, 스킵")
            continue

        try:
            q = bedrock.generate_question_from_user_question(
                concept=concept,
                parent_question_text=item["parent_question_text"],
                user_question=item["user_question"],
                llm_answer=item["llm_answer"],
            )

            if dry_run:
                logger.info(f"[DRY-RUN] {concept.name}: {q.question_text[:80]}...")
            else:
                qdb.put_question(q)
                uqdb.mark_processed(uq_id)
                logger.info(
                    f"[{uq_id[:8]}] → 문제 {q.question_id[:8]} 저장 ({concept.name})"
                )

            total += 1

        except Exception as e:
            errors += 1
            logger.error(f"[{uq_id[:8]}] 문제 생성 실패: {e}")

    logger.info(f"완료. 생성 {total}개, 실패 {errors}개.")


if __name__ == "__main__":
    app()
