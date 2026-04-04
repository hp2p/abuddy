#!/usr/bin/env python
"""
잘못 생성된 CCA 문제를 삭제.

"잘못 생성"의 기준: Multiple Response(MR) 타입 문제.
CCA 시험은 Multiple Choice only이므로 MR 문제는 모두 잘못 생성된 것입니다.

(AWS/Amazon 언급은 삭제 기준이 아닙니다.
 Claude를 AWS Bedrock에 연결하는 내용 등은 CCA 범위에 포함됩니다.)

사용법:
  uv run scripts/delete_bad_cca_questions.py            # 드라이런 (삭제 안 함)
  uv run scripts/delete_bad_cca_questions.py --execute  # 실제 삭제
"""
import sys

import boto3
import typer
from boto3.dynamodb.conditions import Attr
from loguru import logger

sys.path.insert(0, "src")
from abuddy.config import settings

app = typer.Typer()


@app.command()
def main(
    execute: bool = typer.Option(False, "--execute", help="실제 삭제 (기본: 드라이런)"),
    exam: str = typer.Option("CCA", "--exam", help="대상 자격증 ID"),
):
    table = boto3.resource("dynamodb", region_name=settings.aws_region).Table(
        settings.dynamodb_questions_table
    )

    logger.info(f"[{exam}] DynamoDB 스캔 중 (MR 문제 탐색)...")
    bad: list[str] = []
    last_key = None
    scanned = 0
    while True:
        kwargs: dict = {
            "FilterExpression": (
                Attr("exam_id").eq(exam) & Attr("question_type").eq("multiple_response")
            ),
            "ProjectionExpression": "question_id, question_text",
        }
        if last_key:
            kwargs["ExclusiveStartKey"] = last_key
        resp = table.scan(**kwargs)
        items = resp.get("Items", [])
        scanned += len(items)
        for item in items:
            bad.append(item["question_id"])
        last_key = resp.get("LastEvaluatedKey")
        if not last_key:
            break

    logger.info(f"스캔 완료: Multiple Response 문제 {len(bad)}개 발견")

    if not bad:
        logger.info("삭제할 문제 없음.")
        return

    for qid in bad[:10]:
        logger.info(f"  {qid}")
    if len(bad) > 10:
        logger.info(f"  ... 외 {len(bad) - 10}개")

    if not execute:
        logger.info("드라이런 완료. --execute 옵션을 추가하면 실제 삭제합니다.")
        return

    deleted = 0
    with table.batch_writer() as batch:
        for qid in bad:
            batch.delete_item(Key={"question_id": qid})
            deleted += 1

    logger.info(f"삭제 완료: {deleted}개")


if __name__ == "__main__":
    app()
