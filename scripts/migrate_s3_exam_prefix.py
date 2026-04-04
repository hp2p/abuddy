#!/usr/bin/env python
"""
기존 S3 데이터에 exam_id 프리픽스를 추가하는 1회성 마이그레이션 스크립트.

변경 전: s3://abuddy-data/graph/concept_graph.json
변경 후: s3://abuddy-data/aip-c01/graph/concept_graph.json

변경 전: s3://abuddy-data/docs/{concept_id}.json
변경 후: s3://abuddy-data/aip-c01/docs/{concept_id}.json

사용법:
  uv run scripts/migrate_s3_exam_prefix.py               # 드라이런 (실제 이동 안 함)
  uv run scripts/migrate_s3_exam_prefix.py --execute     # 실제 복사 실행
  uv run scripts/migrate_s3_exam_prefix.py --execute --delete-old  # 복사 후 구버전 삭제
"""
import sys

import boto3
import typer
from loguru import logger

sys.path.insert(0, "src")
from abuddy.config import settings

app = typer.Typer()


def _s3():
    return boto3.client("s3", region_name=settings.aws_region)


def list_objects(prefix: str) -> list[str]:
    s3 = _s3()
    paginator = s3.get_paginator("list_objects_v2")
    keys = []
    for page in paginator.paginate(Bucket=settings.s3_bucket, Prefix=prefix):
        for obj in page.get("Contents", []):
            keys.append(obj["Key"])
    return keys


@app.command()
def main(
    exam: str = typer.Option("aip-c01", "--exam", help="마이그레이션 대상 자격증 ID"),
    execute: bool = typer.Option(False, "--execute", help="실제 복사 실행 (기본: 드라이런)"),
    delete_old: bool = typer.Option(False, "--delete-old", help="복사 후 구버전 키 삭제"),
):
    if delete_old and not execute:
        logger.error("--delete-old는 --execute와 함께 사용해야 합니다.")
        raise typer.Exit(1)

    s3 = _s3()
    bucket = settings.s3_bucket

    # 마이그레이션 대상 수집
    migrations: list[tuple[str, str]] = []

    # graph/concept_graph.json → {exam}/graph/concept_graph.json
    old_graph_key = "graph/concept_graph.json"
    new_graph_key = f"{exam}/graph/concept_graph.json"
    try:
        s3.head_object(Bucket=bucket, Key=old_graph_key)
        migrations.append((old_graph_key, new_graph_key))
    except Exception:
        logger.info(f"구버전 그래프 없음: {old_graph_key}")

    # docs/*.json → {exam}/docs/*.json
    old_doc_keys = list_objects("docs/")
    for old_key in old_doc_keys:
        new_key = f"{exam}/{old_key}"
        migrations.append((old_key, new_key))

    logger.info(f"마이그레이션 대상: {len(migrations)}개 객체 (exam={exam})")

    if not migrations:
        logger.info("마이그레이션할 객체가 없습니다.")
        raise typer.Exit(0)

    for old_key, new_key in migrations:
        # 새 경로에 이미 존재하는지 확인
        try:
            s3.head_object(Bucket=bucket, Key=new_key)
            logger.info(f"  이미 존재, 스킵: {new_key}")
            continue
        except Exception:
            pass

        logger.info(f"  {'복사' if execute else '[드라이런] 복사 예정'}: {old_key} → {new_key}")
        if execute:
            s3.copy_object(
                Bucket=bucket,
                CopySource={"Bucket": bucket, "Key": old_key},
                Key=new_key,
            )

    if execute and delete_old:
        logger.info("구버전 객체 삭제 중...")
        for old_key, _ in migrations:
            logger.info(f"  삭제: {old_key}")
            s3.delete_object(Bucket=bucket, Key=old_key)

    if not execute:
        logger.info("\n드라이런 완료. 실제 실행하려면 --execute 플래그를 추가하세요.")
    else:
        logger.info(f"\n마이그레이션 완료. {len(migrations)}개 객체 복사됨.")
        if delete_old:
            logger.info("구버전 객체 삭제 완료.")


if __name__ == "__main__":
    app()
