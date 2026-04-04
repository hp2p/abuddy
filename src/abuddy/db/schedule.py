from datetime import datetime, timedelta
from decimal import Decimal

import boto3
from loguru import logger

from abuddy.config import settings
from abuddy.models.schedule import IntervalStep, ReviewSchedule

# DynamoDB 스키마: PK=user_id (S), SK=question_id (S)
# 멀티유저: 사용자별 독립 스케줄


def _table():
    return boto3.resource("dynamodb", region_name=settings.aws_region).Table(
        settings.dynamodb_schedule_table
    )


def _to_item(user_id: str, s: ReviewSchedule) -> dict:
    return {
        "user_id": user_id,
        "question_id": s.question_id,
        "interval_step": int(s.interval_step),
        "next_review_at": Decimal(str(s.next_review_at.timestamp())),
        "consecutive_correct": s.consecutive_correct,
        "is_mastered": s.is_mastered,
        "domain": s.domain,
    }


def _from_item(item: dict) -> ReviewSchedule:
    return ReviewSchedule(
        question_id=item["question_id"],
        interval_step=IntervalStep(int(item["interval_step"])),
        next_review_at=datetime.fromtimestamp(float(item["next_review_at"])),
        consecutive_correct=int(item["consecutive_correct"]),
        is_mastered=bool(item["is_mastered"]),
        domain=int(item.get("domain", 0)),
    )


def put_schedule(user_id: str, s: ReviewSchedule) -> None:
    _table().put_item(Item=_to_item(user_id, s))


def get_schedule(user_id: str, question_id: str) -> ReviewSchedule | None:
    resp = _table().get_item(Key={"user_id": user_id, "question_id": question_id})
    item = resp.get("Item")
    return _from_item(item) if item else None


def get_due_question_ids(user_id: str, limit: int = 20, exam_id: str | None = None) -> list[str]:
    """next_review_at <= now 이고 미마스터인 문제 (10분 큐 포함). exam_id로 시험 격리."""
    from abuddy.db import questions as qdb
    now_ts = Decimal(str(datetime.now().timestamp()))
    resp = _table().query(
        KeyConditionExpression="user_id = :uid",
        FilterExpression="next_review_at <= :now AND is_mastered = :false",
        ExpressionAttributeValues={
            ":uid": user_id,
            ":now": now_ts,
            ":false": False,
        },
    )
    items = sorted(resp.get("Items", []), key=lambda x: x["next_review_at"])
    ids = [i["question_id"] for i in items]
    if exam_id:
        allowed = set(qdb.list_all_question_ids(exam_id))
        ids = [qid for qid in ids if qid in allowed]
    return ids[:limit]


def get_scheduled_question_ids(user_id: str, exam_id: str | None = None) -> set[str]:
    """해당 유저가 스케줄에 등록한 모든 question_id. exam_id로 시험 격리."""
    from abuddy.db import questions as qdb
    resp = _table().query(
        KeyConditionExpression="user_id = :uid",
        ProjectionExpression="question_id",
        ExpressionAttributeValues={":uid": user_id},
    )
    ids = {i["question_id"] for i in resp.get("Items", [])}
    if exam_id:
        allowed = set(qdb.list_all_question_ids(exam_id))
        ids = ids & allowed
    return ids


def get_stats(user_id: str) -> dict:
    resp = _table().query(
        KeyConditionExpression="user_id = :uid",
        ExpressionAttributeValues={":uid": user_id},
    )
    items = resp.get("Items", [])
    now_ts = datetime.now().timestamp()
    total = len(items)
    mastered = sum(1 for i in items if i.get("is_mastered"))
    due = sum(
        1 for i in items
        if not i.get("is_mastered") and float(i["next_review_at"]) <= now_ts
    )
    return {"total_scheduled": total, "mastered": mastered, "due_now": due}


def get_domain_stats(user_id: str) -> dict[int, dict]:
    """도메인별 mastered/total 집계"""
    resp = _table().query(
        KeyConditionExpression="user_id = :uid",
        ExpressionAttributeValues={":uid": user_id},
    )
    stats: dict[int, dict] = {}
    for item in resp.get("Items", []):
        domain = int(item.get("domain", 0))
        if domain == 0:
            continue
        if domain not in stats:
            stats[domain] = {"mastered": 0, "total": 0}
        stats[domain]["total"] += 1
        if item.get("is_mastered"):
            stats[domain]["mastered"] += 1
    return stats
