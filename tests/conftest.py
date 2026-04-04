"""공통 fixtures"""
import sys
from datetime import datetime, timedelta

import pytest

sys.path.insert(0, "src")

from abuddy.models.question import Difficulty, Question, QuestionType
from abuddy.models.schedule import IntervalStep, ReviewSchedule


def make_question(**kwargs) -> Question:
    defaults = dict(
        concept_id="d1-test-concept",
        domain=1,
        difficulty=Difficulty.MEDIUM,
        question_type=QuestionType.MULTIPLE_CHOICE,
        question_text="Which of the following best describes the agentic loop in Claude?",
        options=["Option A", "Option B", "Option C", "Option D"],
        correct_indices=[0],
        num_correct=1,
        explanation="The agentic loop allows Claude to iteratively use tools.",
        exam_id="CCA",
    )
    defaults.update(kwargs)
    return Question(**defaults)


def make_schedule(
    question_id: str = "q-test",
    interval_step: IntervalStep = IntervalStep.IN_SESSION,
    consecutive_correct: int = 0,
    is_mastered: bool = False,
    next_review_at: datetime | None = None,
) -> ReviewSchedule:
    return ReviewSchedule(
        question_id=question_id,
        interval_step=interval_step,
        consecutive_correct=consecutive_correct,
        is_mastered=is_mastered,
        next_review_at=next_review_at or datetime.now(),
        domain=1,
    )
