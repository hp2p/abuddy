"""사용자가 퀴즈 풀이 중 남긴 팔로업 질문을 저장/조회."""
from datetime import datetime, timezone
from uuid import uuid4

import boto3
from loguru import logger

from abuddy.config import settings


def _table():
    return boto3.resource("dynamodb", region_name=settings.aws_region).Table(
        settings.dynamodb_user_questions_table
    )


def save_user_question(
    user_id: str,
    parent_question_id: str,
    concept_id: str,
    domain: int,
    parent_question_text: str,
    user_question: str,
    llm_answer: str,
) -> str:
    """팔로업 질문 + LLM 답변을 저장. 생성된 uq_id 반환."""
    uq_id = str(uuid4())
    _table().put_item(
        Item={
            "uq_id": uq_id,
            "user_id": user_id,
            "parent_question_id": parent_question_id,
            "concept_id": concept_id,
            "domain": domain,
            "parent_question_text": parent_question_text,
            "user_question": user_question,
            "llm_answer": llm_answer,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "processed": False,
        }
    )
    logger.debug(f"Saved user question {uq_id[:8]} from user {user_id[:8]}")
    return uq_id


def list_unprocessed(limit: int = 100) -> list[dict]:
    """아직 문제 은행으로 변환되지 않은 항목 조회."""
    resp = _table().scan(
        FilterExpression="processed = :f",
        ExpressionAttributeValues={":f": False},
        Limit=limit,
    )
    return resp.get("Items", [])


def mark_processed(uq_id: str) -> None:
    """문제 생성 완료 표시."""
    _table().update_item(
        Key={"uq_id": uq_id},
        UpdateExpression="SET processed = :t",
        ExpressionAttributeValues={":t": True},
    )
