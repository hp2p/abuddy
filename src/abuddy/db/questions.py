import boto3
from boto3.dynamodb.conditions import Attr
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


def list_questions_by_concept(concept_id: str, exam_id: str | None = None) -> list[Question]:
    eid = exam_id or settings.active_exam
    filt = Attr("concept_id").eq(concept_id) & Attr("exam_id").eq(eid)
    resp = _table().scan(FilterExpression=filt)
    return [Question(**i) for i in resp.get("Items", [])]


def list_all_question_ids(exam_id: str | None = None) -> list[str]:
    eid = exam_id or settings.active_exam
    resp = _table().scan(
        ProjectionExpression="question_id",
        FilterExpression=Attr("exam_id").eq(eid),
    )
    return [i["question_id"] for i in resp.get("Items", [])]


def question_count(exam_id: str | None = None) -> int:
    eid = exam_id or settings.active_exam
    resp = _table().scan(
        Select="COUNT",
        FilterExpression=Attr("exam_id").eq(eid),
    )
    return resp.get("Count", 0)
