#!/usr/bin/env python
"""
S3의 claude-cert/ 프리픽스를 CCA/ 로 복사하는 1회성 마이그레이션.

변경 전: s3://abuddy-data/claude-cert/graph/concept_graph.json
         s3://abuddy-data/claude-cert/docs/{concept_id}.json
변경 후: s3://abuddy-data/CCA/graph/concept_graph.json
         s3://abuddy-data/CCA/docs/{concept_id}.json

사용법:
  uv run scripts/migrate_exam_id_claude_cert_to_CCA.py            # 드라이런
  uv run scripts/migrate_exam_id_claude_cert_to_CCA.py --execute  # 실제 복사
  uv run scripts/migrate_exam_id_claude_cert_to_CCA.py --execute --delete-old  # 복사 후 구버전 삭제
"""
import sys

import boto3
import typer
from loguru import logger

sys.path.insert(0, "src")
from abuddy.config import settings

SRC_PREFIX = "claude-cert/"
DST_PREFIX = "CCA/"

app = typer.Typer()


def _s3():
    return boto3.client("s3", region_name=settings.aws_region)


def list_objects(prefix: str) -> list[str]:
    paginator = _s3().get_paginator("list_objects_v2")
    keys = []
    for page in paginator.paginate(Bucket=settings.s3_bucket, Prefix=prefix):
        for obj in page.get("Contents", []):
            keys.append(obj["Key"])
    return keys


@app.command()
def main(
    execute: bool = typer.Option(False, "--execute", help="실제 복사 실행 (없으면 드라이런)"),
    delete_old: bool = typer.Option(False, "--delete-old", help="복사 완료 후 claude-cert/ 삭제"),
) -> None:
    s3 = _s3()
    bucket = settings.s3_bucket

    keys = list_objects(SRC_PREFIX)
    if not keys:
        logger.warning(f"s3://{bucket}/{SRC_PREFIX} 에 객체가 없습니다.")
        raise typer.Exit(1)

    logger.info(f"{'[드라이런] ' if not execute else ''}총 {len(keys)}개 객체 복사: {SRC_PREFIX} → {DST_PREFIX}")

    copied = 0
    for src_key in keys:
        dst_key = DST_PREFIX + src_key[len(SRC_PREFIX):]
        logger.info(f"  {src_key} → {dst_key}")
        if execute:
            s3.copy_object(
                Bucket=bucket,
                CopySource={"Bucket": bucket, "Key": src_key},
                Key=dst_key,
            )
            copied += 1

    if execute:
        logger.info(f"복사 완료: {copied}개")

    if execute and delete_old:
        logger.info(f"구버전 삭제 중: {SRC_PREFIX}")
        for src_key in keys:
            s3.delete_object(Bucket=bucket, Key=src_key)
            logger.info(f"  삭제: {src_key}")
        logger.info("삭제 완료")
    elif not execute:
        logger.info("드라이런 완료. --execute 플래그를 추가하면 실제 복사됩니다.")


if __name__ == "__main__":
    app()
