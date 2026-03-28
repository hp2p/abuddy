"""퀴즈 엔진: 다음 문제 결정 + 정답 처리 (멀티유저)"""
import random
from datetime import datetime, timedelta

from loguru import logger

from abuddy.db import questions as qdb
from abuddy.db import schedule as sdb
from abuddy.models.question import Question
from abuddy.models.schedule import IntervalStep, ReviewSchedule
from abuddy.services import concept_graph as cg


def get_next_question(user_id: str) -> Question | None:
    """
    우선순위:
    1. DynamoDB에서 next_review_at <= now 인 문제 (10분 큐 포함)
    2. 처음 보는 문제 (해당 유저의 schedule에 없는 문제)
    """
    # 1. due된 문제 (10분 리뷰 + 장기 복습 통합)
    due_ids = sdb.get_due_question_ids(user_id, limit=10)
    if due_ids:
        qid = due_ids[0]  # 가장 오래된 것 먼저
        q = qdb.get_question(qid)
        if q:
            logger.debug(f"[{user_id[:8]}] Due review: {qid[:8]}")
            return q

    # 2. 새 문제
    all_ids = qdb.list_all_question_ids()
    scheduled = sdb.get_scheduled_question_ids(user_id)
    unscheduled = [qid for qid in all_ids if qid not in scheduled]
    if unscheduled:
        qid = random.choice(unscheduled)
        q = qdb.get_question(qid)
        if q:
            logger.debug(f"[{user_id[:8]}] New question: {qid[:8]}")
            return q

    return None


def process_answer(
    user_id: str,
    question: Question,
    selected_indices: list[int],
    self_confirmed: bool = False,
) -> tuple[bool, ReviewSchedule]:
    """
    정답 여부 판정 + 스케줄 업데이트.
    Returns: (is_correct, updated_schedule)
    """
    is_correct = set(question.correct_indices) == set(selected_indices)

    schedule = sdb.get_schedule(user_id, question.question_id)
    if schedule is None:
        schedule = ReviewSchedule(question_id=question.question_id)

    if is_correct and not self_confirmed:
        # 정답이지만 불확실 → 10분 후 재확인 (advance는 하지 않음)
        schedule = schedule.model_copy(update={
            "next_review_at": datetime.now() + timedelta(minutes=10),
            "interval_step": IntervalStep.IN_SESSION,
        })
    elif is_correct and self_confirmed:
        schedule = schedule.advance(question.difficulty)
    else:
        # 오답 → 1일 후 리셋 + 연관 문제 10분 큐 등록
        schedule = schedule.reset()
        _queue_related_questions(user_id, question)

    sdb.put_schedule(user_id, schedule)
    return is_correct, schedule


def _queue_related_questions(user_id: str, question: Question) -> None:
    """오답 시 연관 concept 문제를 10분 후 스케줄에 추가"""
    related_concept_ids = cg.get_related_concept_ids(question.concept_id, hops=1)
    if not related_concept_ids:
        return

    for cid in related_concept_ids[:2]:
        related_qs = qdb.list_questions_by_concept(cid)
        candidates = [q for q in related_qs if q.question_id != question.question_id]
        if not candidates:
            continue

        q = random.choice(candidates)
        existing = sdb.get_schedule(user_id, q.question_id)
        # 아직 스케줄이 없거나 마스터된 문제는 10분 후 큐에 추가
        if existing is None or existing.is_mastered:
            new_sched = ReviewSchedule(
                question_id=q.question_id,
                interval_step=IntervalStep.IN_SESSION,
                next_review_at=datetime.now() + timedelta(minutes=10),
            )
            sdb.put_schedule(user_id, new_sched)
            logger.debug(f"[{user_id[:8]}] Queued related: {q.question_id[:8]} (concept: {cid})")
