"""
CCA 문제 콘텐츠 품질 테스트

- 기능 테스트: CCA 문제가 올바른 구조를 가지는지
- 통합 테스트: 실제 DynamoDB의 CCA 문제 구조 검증

DynamoDB 접근이 필요한 테스트는 pytest.mark.integration으로 표시.
오프라인 환경: uv run pytest -m "not integration"
"""
import sys

import pytest

sys.path.insert(0, "src")

from abuddy.models.question import Difficulty, Question, QuestionType

from conftest import make_question


# ─── 오프라인 단위 테스트 ────────────────────────────────

class TestCCAQuestionStructure:
    def test_mc_has_4_options(self):
        q = make_question(question_type=QuestionType.MULTIPLE_CHOICE)
        assert len(q.options) == 4

    def test_mc_has_exactly_1_correct(self):
        q = make_question(correct_indices=[0], num_correct=1)
        assert q.num_correct == 1
        assert len(q.correct_indices) == 1

    def test_mr_has_5_options_and_multiple_correct(self):
        q = make_question(
            question_type=QuestionType.MULTIPLE_RESPONSE,
            options=["A", "B", "C", "D", "E"],
            correct_indices=[0, 2],
            num_correct=2,
        )
        assert len(q.options) == 5
        assert q.num_correct >= 2

    def test_exam_id_is_CCA(self):
        q = make_question(exam_id="CCA")
        assert q.exam_id == "CCA"

    def test_domain_in_range(self):
        for domain in range(1, 6):
            q = make_question(domain=domain)
            assert 1 <= q.domain <= 5

    def test_correct_indices_in_options_range(self):
        q = make_question(options=["A", "B", "C", "D"], correct_indices=[2])
        for idx in q.correct_indices:
            assert 0 <= idx < len(q.options)


# ─── 통합 테스트 (DynamoDB 필요) ─────────────────────────

@pytest.mark.integration
class TestCCAContentInDynamoDB:
    """실제 DynamoDB의 CCA 문제 구조 검증"""

    def test_cca_questions_exist(self):
        from abuddy.db import questions as qdb
        qids = qdb.list_all_question_ids(exam_id="CCA")
        assert qids, "CCA 문제가 없습니다. 먼저 generate_questions.py를 실행하세요."

    def test_cca_questions_are_mc_only(self):
        """CCA 시험은 Multiple Response 없음"""
        from abuddy.db import questions as qdb
        qids = qdb.list_all_question_ids(exam_id="CCA")
        mr_questions = []
        for qid in qids:
            q = qdb.get_question(qid)
            if q and q.question_type == QuestionType.MULTIPLE_RESPONSE:
                mr_questions.append(qid)

        assert not mr_questions, (
            f"CCA 문제 중 Multiple Response {len(mr_questions)}개 발견 (CCA는 MC only): "
            + ", ".join(mr_questions[:5])
        )

    def test_all_cca_questions_have_4_options(self):
        from abuddy.db import questions as qdb
        qids = qdb.list_all_question_ids(exam_id="CCA")
        violations = [
            qid for qid in qids
            if (q := qdb.get_question(qid)) and len(q.options) != 4
        ]
        assert not violations, (
            f"{len(violations)}개 문제의 선택지가 4개가 아님: {violations[:5]}"
        )

    def test_all_cca_questions_have_correct_exam_id(self):
        from abuddy.db import questions as qdb
        qids = qdb.list_all_question_ids(exam_id="CCA")
        wrong = [
            qid for qid in qids
            if (q := qdb.get_question(qid)) and q.exam_id != "CCA"
        ]
        assert not wrong, f"exam_id가 CCA가 아닌 문제 {len(wrong)}개"
