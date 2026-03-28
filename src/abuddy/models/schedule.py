from datetime import datetime, timedelta
from enum import IntEnum

from pydantic import BaseModel

from abuddy.models.question import Difficulty


class IntervalStep(IntEnum):
    """에빙하우스 망각곡선 기반 반복 간격 단계"""
    IN_SESSION = 0   # 10분 후 (세션 내 메모리 큐)
    DAY_1 = 1        # 1일 후
    WEEK_1 = 2       # 7일 후
    MONTH_1 = 3      # 30일 후
    MASTERED = 4     # 완료 (6개월+ 기억)


INTERVAL_DELTAS: dict[IntervalStep, timedelta] = {
    IntervalStep.DAY_1: timedelta(days=1),
    IntervalStep.WEEK_1: timedelta(days=7),
    IntervalStep.MONTH_1: timedelta(days=30),
}

# 난이도별 마스터 판정 연속 정답 횟수
MASTERY_THRESHOLD: dict[Difficulty, int] = {
    Difficulty.EASY: 2,
    Difficulty.MEDIUM: 3,
    Difficulty.HARD: 4,
}


class ReviewSchedule(BaseModel):
    question_id: str
    interval_step: IntervalStep = IntervalStep.IN_SESSION
    next_review_at: datetime = datetime.now()
    consecutive_correct: int = 0
    is_mastered: bool = False

    def advance(self, difficulty: Difficulty) -> "ReviewSchedule":
        """정답 처리: 다음 단계로 이동"""
        new_consecutive = self.consecutive_correct + 1
        threshold = MASTERY_THRESHOLD[difficulty]

        if new_consecutive >= threshold and self.interval_step == IntervalStep.MONTH_1:
            return self.model_copy(update={
                "consecutive_correct": new_consecutive,
                "interval_step": IntervalStep.MASTERED,
                "is_mastered": True,
                "next_review_at": datetime.max,
            })

        next_step = IntervalStep(min(self.interval_step + 1, IntervalStep.MONTH_1))
        delta = INTERVAL_DELTAS.get(next_step, timedelta(days=30))
        return self.model_copy(update={
            "consecutive_correct": new_consecutive,
            "interval_step": next_step,
            "next_review_at": datetime.now() + delta,
        })

    def reset(self) -> "ReviewSchedule":
        """오답 처리: 1일 후로 리셋"""
        return self.model_copy(update={
            "consecutive_correct": 0,
            "interval_step": IntervalStep.DAY_1,
            "next_review_at": datetime.now() + timedelta(days=1),
            "is_mastered": False,
        })
