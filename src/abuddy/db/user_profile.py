from datetime import date, timedelta

import boto3

from abuddy.config import settings
from abuddy.models.user_profile import UserProfile


def _table():
    return boto3.resource("dynamodb", region_name=settings.aws_region).Table(
        settings.dynamodb_user_profile_table
    )


def get_profile(user_id: str) -> UserProfile:
    resp = _table().get_item(Key={"user_id": user_id})
    item = resp.get("Item")
    if not item:
        return UserProfile(user_id=user_id)
    return UserProfile(
        user_id=item["user_id"],
        exam_date=item.get("exam_date"),
        current_streak=int(item.get("current_streak", 0)),
        max_streak=int(item.get("max_streak", 0)),
        last_activity_date=item.get("last_activity_date"),
        today_answered=int(item.get("today_answered", 0)),
        today_date=item.get("today_date"),
    )


def put_profile(profile: UserProfile) -> None:
    item: dict = {
        "user_id": profile.user_id,
        "current_streak": profile.current_streak,
        "max_streak": profile.max_streak,
    }
    if profile.exam_date is not None:
        item["exam_date"] = profile.exam_date
    if profile.last_activity_date is not None:
        item["last_activity_date"] = profile.last_activity_date
    if profile.today_date is not None:
        item["today_date"] = profile.today_date
        item["today_answered"] = profile.today_answered
    _table().put_item(Item=item)


def update_activity(user_id: str) -> UserProfile:
    """문제를 풀 때마다 호출: 스트릭 계산 + 오늘 풀이 수 증가"""
    profile = get_profile(user_id)
    today = date.today().isoformat()
    yesterday = (date.today() - timedelta(days=1)).isoformat()

    # 오늘 풀이 수 업데이트
    if profile.today_date == today:
        new_today_answered = profile.today_answered + 1
    else:
        new_today_answered = 1

    # 스트릭 계산
    if profile.last_activity_date is None:
        new_streak = 1
    elif profile.last_activity_date == today:
        new_streak = profile.current_streak  # 오늘 이미 활동, 유지
    elif profile.last_activity_date == yesterday:
        new_streak = profile.current_streak + 1
    else:
        new_streak = 1  # 하루 이상 공백 → 리셋

    profile = profile.model_copy(update={
        "today_answered": new_today_answered,
        "today_date": today,
        "current_streak": new_streak,
        "max_streak": max(new_streak, profile.max_streak),
        "last_activity_date": today,
    })
    put_profile(profile)
    return profile


def set_exam_date(user_id: str, exam_date: str) -> UserProfile:
    profile = get_profile(user_id)
    profile = profile.model_copy(update={"exam_date": exam_date})
    put_profile(profile)
    return profile
