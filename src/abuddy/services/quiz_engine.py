"""퀴즈 엔진: 다음 문제 결정 + 정답 처리 (멀티유저)"""
import random
from datetime import datetime, timedelta

from loguru import logger

from abuddy.config import settings
from abuddy.db import questions as qdb
from abuddy.db import schedule as sdb
from abuddy.db import user_profile as updb
from abuddy.models.question import Question
from abuddy.models.schedule import IntervalStep, ReviewSchedule
from abuddy.services import concept_graph as cg

_DUE_WEIGHT = 0.6  # 복습 문제 선택 확률


def get_next_question(user_id: str, exam_id: str | None = None) -> Question | None:
    """
    복습 문제(due)와 새 문제를 랜덤하게 혼합해서 반환.
    due 문제가 있으면 60% 확률로, 새 문제가 있으면 40% 확률로 선택.
    한쪽만 있으면 그쪽에서 선택.
    """
    eid = exam_id or settings.active_exam
    due_ids = sdb.get_due_question_ids(user_id, limit=20)

    all_ids = qdb.list_all_question_ids(eid)
    scheduled = sdb.get_scheduled_question_ids(user_id)
    new_ids = [qid for qid in all_ids if qid not in scheduled]

    if due_ids and new_ids:
        pool = due_ids if random.random() < _DUE_WEIGHT else new_ids
    elif due_ids:
        pool = due_ids
    elif new_ids:
        pool = new_ids
    else:
        return None

    qid = random.choice(pool)
    q = qdb.get_question(qid)
    if q:
        kind = "due" if qid in due_ids else "new"
        logger.debug(f"[{user_id[:8]}] {kind}: {qid[:8]}")
    return q


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
        schedule = ReviewSchedule(question_id=question.question_id, domain=question.domain)

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
    updb.update_activity(user_id)
    return is_correct, schedule


def _queue_related_questions(user_id: str, question: Question) -> None:
    """오답 시 연관 concept 문제를 10분 후 스케줄에 추가"""
    related_concept_ids = cg.get_related_concept_ids(question.concept_id, hops=1, exam_id=question.exam_id)
    if not related_concept_ids:
        return

    for cid in related_concept_ids[:2]:
        related_qs = qdb.list_questions_by_concept(cid, exam_id=question.exam_id)
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
                domain=q.domain,
            )
            sdb.put_schedule(user_id, new_sched)
            logger.debug(f"[{user_id[:8]}] Queued related: {q.question_id[:8]} (concept: {cid})")
