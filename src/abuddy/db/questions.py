from datetime import datetime

import boto3
from loguru import logger

from abuddy.config import settings
from abuddy.models.question import Question


def _table():
    return boto3.resource("dynamodb", region_name=settings.aws_region).Table(
        settings.dynamodb_questions_table
    )


def put_question(q: Question) -> None:
    _table().put_item(Item=q.model_dump())
    logger.debug(f"Saved question {q.question_id}")


def get_question(question_id: str) -> Question | None:
    resp = _table().get_item(Key={"question_id": question_id})
    item = resp.get("Item")
    return Question(**item) if item else None


def list_questions_by_concept(concept_id: str) -> list[Question]:
    resp = _table().scan(
        FilterExpression="concept_id = :cid",
        ExpressionAttributeValues={":cid": concept_id},
    )
    return [Question(**i) for i in resp.get("Items", [])]


def list_all_question_ids() -> list[str]:
    resp = _table().scan(ProjectionExpression="question_id")
    return [i["question_id"] for i in resp.get("Items", [])]


def question_count() -> int:
    return _table().scan(Select="COUNT").get("Count", 0)
