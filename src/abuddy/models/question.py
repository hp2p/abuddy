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


class AnswerSubmission(BaseModel):
    selected_indices: list[int]
    user_question: str = ""      # 팔로업 질문 (빈 문자열이면 없음)
    self_confirmed: bool = False  # "확실히 이해했어요" 체크박스
