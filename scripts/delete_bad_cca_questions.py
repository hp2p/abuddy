#!/usr/bin/env python
"""
CCA 문제 중 AWS/Amazon 관련 내용이 포함된 잘못 생성된 문제를 삭제.

CCA는 Anthropic/Claude 전용 시험이므로 question_text나 explanation에
"Amazon", "AWS", "Amazon Bedrock" 등이 포함된 문제는 잘못 생성된 것입니다.

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

AWS_KEYWORDS = ["amazon", "aws ", "amazon bedrock", "amazon s3", "amazon sagemaker"]

app = typer.Typer()


def _is_bad(item: dict) -> bool:
    text = (item.get("question_text", "") + " " + item.get("explanation", "")).lower()
    return any(kw in text for kw in AWS_KEYWORDS)


@app.command()
def main(
    execute: bool = typer.Option(False, "--execute", help="실제 삭제 (기본: 드라이런)"),
    exam: str = typer.Option("CCA", "--exam", help="대상 자격증 ID"),
):
    table = boto3.resource("dynamodb", region_name=settings.aws_region).Table(
        settings.dynamodb_questions_table
    )

    logger.info(f"[{exam}] DynamoDB 스캔 중...")
    bad: list[str] = []
    last_key = None
    scanned = 0
    while True:
        kwargs: dict = {
            "FilterExpression": Attr("exam_id").eq(exam),
            "ProjectionExpression": "question_id, question_text, explanation",
        }
        if last_key:
            kwargs["ExclusiveStartKey"] = last_key
        resp = table.scan(**kwargs)
        items = resp.get("Items", [])
        scanned += len(items)
        for item in items:
            if _is_bad(item):
                bad.append(item["question_id"])
        last_key = resp.get("LastEvaluatedKey")
        if not last_key:
            break

    logger.info(f"스캔 완료: 전체 {scanned}개 중 AWS 언급 {len(bad)}개 발견")

    if not bad:
        logger.info("삭제할 문제 없음.")
        return

    for qid in bad[:10]:
        logger.info(f"  예시: {qid}")
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
