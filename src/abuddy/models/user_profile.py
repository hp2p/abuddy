from pydantic import BaseModel


class UserProfile(BaseModel):
    user_id: str
    exam_date: str | None = None           # "YYYY-MM-DD"
    current_streak: int = 0
    max_streak: int = 0
    last_activity_date: str | None = None  # "YYYY-MM-DD"
    today_answered: int = 0
    today_date: str | None = None          # "YYYY-MM-DD"
    lang: str = "en"                       # "en" | "ko"
