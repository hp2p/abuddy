#!/usr/bin/env python
"""
DynamoDB abuddy-questions 테이블의 기존 문제에 exam_id 필드를 추가하는 1회성 마이그레이션.

exam_id 필드가 없는 문제 → exam_id = "aip-c01" 설정.

사용법:
  uv run scripts/migrate_questions_exam_id.py            # 드라이런
  uv run scripts/migrate_questions_exam_id.py --execute  # 실제 업데이트
"""
import sys

import boto3
import typer
from loguru import logger

sys.path.insert(0, "src")
from abuddy.config import settings

app = typer.Typer()


@app.command()
def main(
    exam: str = typer.Option("aip-c01", "--exam", help="추가할 exam_id 값"),
    execute: bool = typer.Option(False, "--execute", help="실제 업데이트 실행 (기본: 드라이런)"),
):
    dynamodb = boto3.resource("dynamodb", region_name=settings.aws_region)
    table = dynamodb.Table(settings.dynamodb_questions_table)

    # exam_id 없는 항목 스캔
    paginator = dynamodb.meta.client.get_paginator("scan")
    items_to_update = []
    for page in paginator.paginate(
        TableName=settings.dynamodb_questions_table,
        FilterExpression="attribute_not_exists(exam_id)",
        ProjectionExpression="question_id",
    ):
        items_to_update.extend(page.get("Items", []))

    logger.info(f"exam_id 없는 문제: {len(items_to_update)}개 (→ exam_id='{exam}' 설정 예정)")

    if not items_to_update:
        logger.info("마이그레이션할 항목이 없습니다.")
        raise typer.Exit(0)

    if not execute:
        logger.info("드라이런 완료. 실제 실행하려면 --execute 플래그를 추가하세요.")
        raise typer.Exit(0)

    updated = errors = 0
    for item in items_to_update:
        qid = item["question_id"]
        try:
            table.update_item(
                Key={"question_id": qid},
                UpdateExpression="SET exam_id = :eid",
                ExpressionAttributeValues={":eid": exam},
                ConditionExpression="attribute_not_exists(exam_id)",
            )
            updated += 1
            if updated % 50 == 0:
                logger.info(f"  업데이트 중... {updated}/{len(items_to_update)}")
        except Exception as e:
            logger.error(f"  {qid[:8]} 업데이트 실패: {e}")
            errors += 1

    logger.info(f"\n완료: 업데이트 {updated}개, 실패 {errors}개")


if __name__ == "__main__":
    app()
