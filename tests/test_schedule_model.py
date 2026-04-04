"""ReviewSchedule 모델 단위 테스트 (DB 불필요)"""
from datetime import datetime, timedelta

import pytest

from abuddy.models.question import Difficulty
from abuddy.models.schedule import IntervalStep, ReviewSchedule

from conftest import make_schedule


class TestAdvance:
    def test_in_session_advances_to_day1(self):
        s = make_schedule(interval_step=IntervalStep.IN_SESSION, consecutive_correct=1)
        result = s.advance(Difficulty.MEDIUM)
        assert result.interval_step == IntervalStep.DAY_1
        assert result.consecutive_correct == 2

    def test_day1_advances_to_week1(self):
        s = make_schedule(interval_step=IntervalStep.DAY_1, consecutive_correct=2)
        result = s.advance(Difficulty.MEDIUM)
        assert result.interval_step == IntervalStep.WEEK_1

    def test_week1_advances_to_month1(self):
        s = make_schedule(interval_step=IntervalStep.WEEK_1, consecutive_correct=3)
        result = s.advance(Difficulty.MEDIUM)
        assert result.interval_step == IntervalStep.MONTH_1

    def test_mastery_easy_threshold_2(self):
        # EASY: 연속 2회 정답 + MONTH_1 → MASTERED
        s = make_schedule(interval_step=IntervalStep.MONTH_1, consecutive_correct=1)
        result = s.advance(Difficulty.EASY)
        assert result.is_mastered
        assert result.interval_step == IntervalStep.MASTERED

    def test_mastery_medium_threshold_3(self):
        s = make_schedule(interval_step=IntervalStep.MONTH_1, consecutive_correct=2)
        result = s.advance(Difficulty.MEDIUM)
        assert result.is_mastered

    def test_mastery_hard_threshold_4(self):
        s = make_schedule(interval_step=IntervalStep.MONTH_1, consecutive_correct=3)
        result = s.advance(Difficulty.HARD)
        assert result.is_mastered

    def test_no_mastery_before_month1(self):
        # 연속 정답 충분해도 MONTH_1 전엔 마스터 안 됨
        s = make_schedule(interval_step=IntervalStep.WEEK_1, consecutive_correct=10)
        result = s.advance(Difficulty.EASY)
        assert not result.is_mastered
        assert result.interval_step == IntervalStep.MONTH_1

    def test_no_mastery_insufficient_streak(self):
        # MONTH_1이지만 연속 정답이 threshold 미만
        s = make_schedule(interval_step=IntervalStep.MONTH_1, consecutive_correct=0)
        result = s.advance(Difficulty.EASY)
        # EASY threshold=2, new_consecutive=1 < 2 → 마스터 안 됨
        assert not result.is_mastered

    def test_next_review_future_after_advance(self):
        s = make_schedule(interval_step=IntervalStep.IN_SESSION, consecutive_correct=1)
        before = datetime.now()
        result = s.advance(Difficulty.MEDIUM)
        assert result.next_review_at > before + timedelta(hours=20)  # ~1일


class TestReset:
    def test_reset_clears_streak(self):
        s = make_schedule(interval_step=IntervalStep.WEEK_1, consecutive_correct=5)
        result = s.reset()
        assert result.consecutive_correct == 0
        assert result.interval_step == IntervalStep.DAY_1
        assert not result.is_mastered

    def test_reset_schedules_one_day(self):
        s = make_schedule()
        before = datetime.now()
        result = s.reset()
        assert result.next_review_at > before + timedelta(hours=20)

    def test_reset_mastered_question(self):
        s = make_schedule(interval_step=IntervalStep.MASTERED, is_mastered=True, consecutive_correct=4)
        result = s.reset()
        assert not result.is_mastered
        assert result.interval_step == IntervalStep.DAY_1
        assert result.consecutive_correct == 0
