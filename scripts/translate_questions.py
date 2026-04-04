#!/usr/bin/env python
"""
DynamoDB에 저장된 문제를 한국어로 번역해서 업데이트 (1회성 배치).

사용법:
  uv run scripts/translate_questions.py                    # 전체 (미번역 문제만)
  uv run scripts/translate_questions.py --exam aip-c01    # 특정 시험만
  uv run scripts/translate_questions.py --limit 10        # 최대 10개 (테스트용)
  uv run scripts/translate_questions.py --dry-run         # 실제 저장 안 함
  uv run scripts/translate_questions.py --force           # 이미 번역된 것도 재번역
"""
import sys
import time

import typer
from loguru import logger

sys.path.insert(0, "src")
import boto3
from boto3.dynamodb.conditions import Attr

from abuddy.config import settings
from abuddy.models.question import Question
from abuddy.services import bedrock

app = typer.Typer()


def _table():
    return boto3.resource("dynamodb", region_name=settings.aws_region).Table(
        settings.dynamodb_questions_table
    )


def _scan_untranslated(exam_id: str, force: bool) -> list[Question]:
    """번역이 필요한 문제 목록 반환."""
    table = _table()
    filt = Attr("exam_id").eq(exam_id)
    if not force:
        # question_text_ko 필드가 없거나 빈 문자열인 것만
        filt = filt & (
            Attr("question_text_ko").not_exists() | Attr("question_text_ko").eq("")
        )

    items = []
    kwargs: dict = {"FilterExpression": filt}
    while True:
        resp = table.scan(**kwargs)
        items.extend(resp.get("Items", []))
        if "LastEvaluatedKey" not in resp:
            break
        kwargs["ExclusiveStartKey"] = resp["LastEvaluatedKey"]

    return [Question(**i) for i in items]


def _update_translation(question_id: str, translation: dict) -> None:
    _table().update_item(
        Key={"question_id": question_id},
        UpdateExpression="SET question_text_ko = :qt, options_ko = :op, explanation_ko = :ex",
        ExpressionAttributeValues={
            ":qt": translation["question_text_ko"],
            ":op": translation["options_ko"],
            ":ex": translation["explanation_ko"],
        },
    )


@app.command()
def main(
    exam: str = typer.Option(None, help="시험 ID (없으면 active_exam 사용)"),
    limit: int = typer.Option(0, help="최대 번역 수 (0=전체)"),
    dry_run: bool = typer.Option(False, help="번역 결과만 출력, 저장 안 함"),
    force: bool = typer.Option(False, help="이미 번역된 문제도 재번역"),
    delay: float = typer.Option(0.5, help="요청 간 대기 시간(초), 스로틀링 방지"),
):
    exam_id = exam or settings.active_exam
    logger.info(f"대상 시험: {exam_id}  force={force}  dry_run={dry_run}")

    questions = _scan_untranslated(exam_id, force)
    logger.info(f"번역 대상: {len(questions)}개")

    if limit > 0:
        questions = questions[:limit]
        logger.info(f"--limit {limit} 적용 → {len(questions)}개만 처리")

    success = 0
    failed = 0
    for i, q in enumerate(questions, 1):
        logger.info(f"[{i}/{len(questions)}] {q.question_id[:8]}… 번역 중")
        try:
            translation = bedrock.translate_question(
                question_text=q.question_text,
                options=q.options,
                explanation=q.explanation,
            )

            # 선택지 수 검증
            if len(translation.get("options_ko", [])) != len(q.options):
                logger.warning(f"  선택지 수 불일치 ({len(q.options)} → {len(translation.get('options_ko', []))}), 건너뜀")
                failed += 1
                continue

            if dry_run:
                logger.info(f"  [dry-run] question_text_ko: {translation['question_text_ko'][:80]}…")
            else:
                _update_translation(q.question_id, translation)
                logger.info(f"  저장 완료")

            success += 1
            if delay > 0 and i < len(questions):
                time.sleep(delay)

        except Exception as e:
            logger.error(f"  실패: {e}")
            failed += 1

    logger.info(f"완료 — 성공: {success}, 실패: {failed}")


if __name__ == "__main__":
    app()
