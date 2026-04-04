from enum import Enum
from uuid import uuid4

from pydantic import BaseModel, Field


class QuestionType(str, Enum):
    MULTIPLE_CHOICE = "multiple_choice"    # 4지선다, 1개 정답
    MULTIPLE_RESPONSE = "multiple_response"  # 5지선다, 2-3개 정답


class Difficulty(str, Enum):
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"


class Question(BaseModel):
    question_id: str = Field(default_factory=lambda: str(uuid4()))
    concept_id: str
    domain: int  # 1-5
    difficulty: Difficulty = Difficulty.MEDIUM
    question_type: QuestionType = QuestionType.MULTIPLE_CHOICE
    question_text: str
    options: list[str]           # ["Amazon Bedrock", "SageMaker", ...]  (label 없이 텍스트만)
    correct_indices: list[int]   # 0-based, multiple_response면 여러 개
    num_correct: int = 1         # multiple_response 시 "다음 중 N개를 고르시오"
    explanation: str
    source: str = "generated"   # "official" | "generated"
    chunk_id: str = ""           # chunk 기반 문제일 때 설정 (concept_id_pX_cY)
    exam_id: str = "aip-c01"    # 자격증 종류 ("aip-c01" | "CCA")
    question_text_ko: str = ""   # 한글 번역 (없으면 빈 문자열)
    options_ko: list[str] = []   # 한글 선택지 (없으면 빈 리스트)
    explanation_ko: str = ""     # 한글 해설 (없으면 빈 문자열)


class AnswerSubmission(BaseModel):
    selected_indices: list[int]
    user_question: str = ""      # 팔로업 질문 (빈 문자열이면 없음)
    self_confirmed: bool = False  # "확실히 이해했어요" 체크박스
