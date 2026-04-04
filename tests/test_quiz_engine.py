"""quiz_engine.process_answer 단위 테스트 (DB mock)"""
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest

from abuddy.models.question import Difficulty
from abuddy.models.schedule import IntervalStep, ReviewSchedule
from abuddy.services import quiz_engine as engine

from conftest import make_question, make_schedule


def _patch_db(existing_schedule: ReviewSchedule | None = None):
    """sdb, qdb, updb, cg를 모두 mock으로 대체하는 context manager 집합"""
    saved = {}

    def fake_put(user_id, s):
        saved["schedule"] = s

    def fake_get(user_id, question_id):
        return existing_schedule

    def fake_activity(user_id):
        pass

    patches = [
        patch("abuddy.services.quiz_engine.sdb.get_schedule", side_effect=fake_get),
        patch("abuddy.services.quiz_engine.sdb.put_schedule", side_effect=fake_put),
        patch("abuddy.services.quiz_engine.updb.update_activity", side_effect=fake_activity),
        patch("abuddy.services.quiz_engine.cg.get_related_concept_ids", return_value=[]),
    ]
    return patches, saved


class TestProcessAnswerWrong:
    def test_wrong_resets_to_day1(self):
        q = make_question(correct_indices=[0])
        patches, saved = _patch_db()
        with patches[0], patches[1], patches[2], patches[3]:
            is_correct, sched = engine.process_answer("user1", q, selected_indices=[1])
        assert not is_correct
        assert saved["schedule"].interval_step == IntervalStep.DAY_1
        assert saved["schedule"].consecutive_correct == 0

    def test_wrong_schedules_one_day(self):
        q = make_question(correct_indices=[0])
        patches, saved = _patch_db()
        before = datetime.now()
        with patches[0], patches[1], patches[2], patches[3]:
            engine.process_answer("user1", q, selected_indices=[2])
        assert saved["schedule"].next_review_at > before + timedelta(hours=20)


class TestProcessAnswerCorrectUnconfirmed:
    def test_schedules_10min_review(self):
        q = make_question(correct_indices=[0])
        patches, saved = _patch_db()
        before = datetime.now()
        with patches[0], patches[1], patches[2], patches[3]:
            is_correct, sched = engine.process_answer("user1", q, selected_indices=[0], self_confirmed=False)
        assert is_correct
        assert saved["schedule"].interval_step == IntervalStep.IN_SESSION
        delta = saved["schedule"].next_review_at - before
        assert timedelta(minutes=9) < delta < timedelta(minutes=11)

    def test_does_not_advance_step(self):
        existing = make_schedule(interval_step=IntervalStep.DAY_1, consecutive_correct=1)
        q = make_question(correct_indices=[0])
        patches, saved = _patch_db(existing)
        with patches[0], patches[1], patches[2], patches[3]:
            engine.process_answer("user1", q, selected_indices=[0], self_confirmed=False)
        assert saved["schedule"].interval_step == IntervalStep.IN_SESSION


class TestProcessAnswerCorrectConfirmed:
    def test_bug2_first_ever_correct_confirmed_stays_in_session(self):
        """Bug 2: 첫 정답+확인이어도 IN_SESSION 10분 재확인 건너뛰지 않음"""
        q = make_question(correct_indices=[0])
        # 처음 보는 문제 (스케줄 없음)
        patches, saved = _patch_db(existing_schedule=None)
        before = datetime.now()
        with patches[0], patches[1], patches[2], patches[3]:
            is_correct, sched = engine.process_answer("user1", q, selected_indices=[0], self_confirmed=True)
        assert is_correct
        # DAY_1으로 바로 가면 안 됨
        assert saved["schedule"].interval_step == IntervalStep.IN_SESSION
        delta = saved["schedule"].next_review_at - before
        assert timedelta(minutes=9) < delta < timedelta(minutes=11)
        # consecutive_correct가 1로 설정됨 (다음 번엔 advance 허용)
        assert saved["schedule"].consecutive_correct == 1

    def test_second_correct_confirmed_advances(self):
        """두 번째 정답+확인 (consecutive_correct=1)은 DAY_1으로 advance"""
        existing = make_schedule(
            interval_step=IntervalStep.IN_SESSION,
            consecutive_correct=1,
        )
        q = make_question(correct_indices=[0])
        patches, saved = _patch_db(existing)
        with patches[0], patches[1], patches[2], patches[3]:
            engine.process_answer("user1", q, selected_indices=[0], self_confirmed=True)
        assert saved["schedule"].interval_step == IntervalStep.DAY_1

    def test_confirmed_on_day1_advances_to_week1(self):
        existing = make_schedule(interval_step=IntervalStep.DAY_1, consecutive_correct=2)
        q = make_question(correct_indices=[0])
        patches, saved = _patch_db(existing)
        with patches[0], patches[1], patches[2], patches[3]:
            engine.process_answer("user1", q, selected_indices=[0], self_confirmed=True)
        assert saved["schedule"].interval_step == IntervalStep.WEEK_1


class TestGetNextQuestion:
    def _make_question_db(self, qids):
        questions = {qid: make_question(exam_id="CCA") for qid in qids}
        for qid, q in questions.items():
            object.__setattr__(q, "question_id", qid)
        return questions

    def test_bug1_in_session_due_deprioritized_when_new_exists(self):
        """Bug 1: regular due + new 있으면 IN_SESSION 문제는 선택 안 됨"""
        from abuddy.models.schedule import IntervalStep

        in_session_id = "q-in-session"
        new_id = "q-new"
        all_ids = [in_session_id, new_id]

        with (
            patch("abuddy.services.quiz_engine.sdb.get_due_items") as mock_due,
            patch("abuddy.services.quiz_engine.qdb.list_all_question_ids") as mock_all,
            patch("abuddy.services.quiz_engine.sdb.get_scheduled_question_ids") as mock_sched,
            patch("abuddy.services.quiz_engine.qdb.get_question") as mock_get,
        ):
            mock_due.return_value = [(in_session_id, IntervalStep.IN_SESSION)]
            mock_all.return_value = all_ids
            mock_sched.return_value = {in_session_id}  # in_session은 scheduled, new는 not
            mock_get.side_effect = lambda qid: make_question(exam_id="CCA")

            for _ in range(20):
                q = engine.get_next_question("user1", exam_id="CCA")
                # in_session_id가 절대로 선택되면 안 됨 (new_id만 있음)
                assert mock_get.call_args[0][0] == new_id

    def test_bug1_in_session_served_when_nothing_else(self):
        """Bug 1: regular due, new 모두 없으면 IN_SESSION 문제 출제"""
        in_session_id = "q-in-session"
        with (
            patch("abuddy.services.quiz_engine.sdb.get_due_items") as mock_due,
            patch("abuddy.services.quiz_engine.qdb.list_all_question_ids") as mock_all,
            patch("abuddy.services.quiz_engine.sdb.get_scheduled_question_ids") as mock_sched,
            patch("abuddy.services.quiz_engine.qdb.get_question") as mock_get,
        ):
            mock_due.return_value = [(in_session_id, IntervalStep.IN_SESSION)]
            mock_all.return_value = [in_session_id]
            mock_sched.return_value = {in_session_id}
            mock_get.return_value = make_question(exam_id="CCA")

            q = engine.get_next_question("user1", exam_id="CCA")
            assert q is not None

    def test_returns_none_when_no_questions(self):
        with (
            patch("abuddy.services.quiz_engine.sdb.get_due_items", return_value=[]),
            patch("abuddy.services.quiz_engine.qdb.list_all_question_ids", return_value=[]),
            patch("abuddy.services.quiz_engine.sdb.get_scheduled_question_ids", return_value=set()),
        ):
            q = engine.get_next_question("user1", exam_id="CCA")
            assert q is None
