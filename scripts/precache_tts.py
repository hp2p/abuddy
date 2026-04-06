#!/usr/bin/env python
"""
edge-tts S3 캐시 사전 생성 스크립트.
모든 문제의 TTS를 미리 생성해 S3에 캐시합니다.
이미 캐시된 항목은 건너뜁니다.

사용법:
  uv run scripts/precache_tts.py                   # 전체 (모든 시험)
  uv run scripts/precache_tts.py --exam CCA        # 특정 시험만
  uv run scripts/precache_tts.py --delay 1.0       # API 호출 간격 (초, 기본 0.5)
  uv run scripts/precache_tts.py --dry-run         # 캐시 미스 목록만 출력 (생성 안 함)
"""
import asyncio
import sys

import typer
from loguru import logger

sys.path.insert(0, "src")
import boto3
from boto3.dynamodb.conditions import Attr

from abuddy.config import settings
from abuddy.models.question import Question
from abuddy.services.tts import _cache_key, _s3_exists, get_tts_url

app = typer.Typer()

OPT_LABELS = ["A", "B", "C", "D", "E", "F"]

# 터치 모드 안내 고정 문구 (text, voice)
FIXED_PHRASES: list[tuple[str, str]] = [
    ("스킵", "ko-female"),
    ("다시 읽기", "ko-female"),
    ("다음 선택", "ko-female"),
    ("모르겠어요", "ko-female"),
    ("다시 읽습니다", "ko-female"),
    ("정답입니다.", "ko-male"),
    ("오답입니다.", "ko-male"),
]
# 선택지별 문구
for _lbl in OPT_LABELS[:5]:
    FIXED_PHRASES.append((f"{_lbl} 선택", "ko-female"))
    FIXED_PHRASES.append((f"{_lbl} 취소", "ko-female"))
    FIXED_PHRASES.append((f"정답은 {_lbl}입니다.", "ko-male"))
# MR 제출 조합 (2개)
for _i in range(5):
    for _j in range(_i + 1, 5):
        _combo = f"{OPT_LABELS[_i]}, {OPT_LABELS[_j]}"
        FIXED_PHRASES.append((f"{_combo} 제출합니다", "ko-female"))
# MR 제출 조합 (3개)
for _i in range(5):
    for _j in range(_i + 1, 5):
        for _k in range(_j + 1, 5):
            _combo = f"{OPT_LABELS[_i]}, {OPT_LABELS[_j]}, {OPT_LABELS[_k]}"
            FIXED_PHRASES.append((f"{_combo} 제출합니다", "ko-female"))


def _opt_voice(index: int, lang: str = "ko") -> str:
    return f"{lang}-male" if index % 2 == 0 else f"{lang}-female"


def _question_segments(q: Question) -> list[tuple[str, str]]:
    """문제 하나의 모든 TTS 세그먼트 (text, voice) 반환."""
    segs: list[tuple[str, str]] = []

    # 문제 텍스트
    if q.question_text:
        segs.append((q.question_text, "en-female"))
    if q.question_text_ko:
        segs.append((q.question_text_ko, "ko-female"))

    # 선택지 (EN) — 프론트엔드와 동일하게 "A. option" 형태로
    for i, opt in enumerate(q.options):
        label = OPT_LABELS[i] if i < len(OPT_LABELS) else str(i + 1)
        segs.append((f"{label}. {opt}", _opt_voice(i, "en")))

    # 선택지 (KO)
    for i, opt in enumerate(q.options_ko):
        label = OPT_LABELS[i] if i < len(OPT_LABELS) else str(i + 1)
        segs.append((f"{label}. {opt}", _opt_voice(i, "ko")))

    # 해설
    if q.explanation:
        segs.append((q.explanation, "en-male"))
    if q.explanation_ko:
        segs.append((q.explanation_ko, "ko-male"))

    # 피드백: "정답은 {label}입니다." 에 쓰이는 정답 레이블 문구 (ko-female)
    if q.correct_indices:
        correct_en = ", ".join(
            f"{OPT_LABELS[i]}. {q.options[i]}"
            for i in q.correct_indices
            if i < len(q.options)
        )
        correct_ko = ", ".join(
            f"{OPT_LABELS[i]}. {q.options_ko[i]}"
            for i in q.correct_indices
            if i < len(q.options_ko)
        )
        if correct_en:
            segs.append((correct_en, "ko-female"))
        if correct_ko:
            segs.append((correct_ko, "ko-female"))

    return segs


async def _ensure_cached(text: str, voice: str, dry_run: bool) -> bool:
    """캐시 미스이면 생성. True=신규 생성(또는 dry-run miss), False=이미 있음."""
    text = text.strip()
    if not text:
        return False
    s3_key = _cache_key(text, voice)
    if _s3_exists(s3_key):
        return False
    if dry_run:
        logger.info(f"[MISS] voice={voice:12s} text={text[:70]!r}")
        return True
    await get_tts_url(text, voice)
    return True


def _scan_questions(exam_id: str | None) -> list[Question]:
    table = boto3.resource("dynamodb", region_name=settings.aws_region).Table(
        settings.dynamodb_questions_table
    )
    kwargs: dict = {}
    if exam_id:
        kwargs["FilterExpression"] = Attr("exam_id").eq(exam_id)
    items: list[dict] = []
    while True:
        resp = table.scan(**kwargs)
        items.extend(resp.get("Items", []))
        if "LastEvaluatedKey" not in resp:
            break
        kwargs["ExclusiveStartKey"] = resp["LastEvaluatedKey"]
    return [Question(**item) for item in items]


async def _run(exam_id: str | None, delay: float, dry_run: bool) -> None:
    logger.info(
        f"TTS 사전 캐시 생성 시작 "
        f"(exam={exam_id or '전체'}, delay={delay}s, dry_run={dry_run})"
    )

    # 1. 고정 안내 문구
    logger.info(f"고정 문구 {len(FIXED_PHRASES)}개 처리 중...")
    fixed_new = 0
    for text, voice in FIXED_PHRASES:
        if await _ensure_cached(text, voice, dry_run):
            fixed_new += 1
            if not dry_run:
                await asyncio.sleep(delay)
    logger.info(f"고정 문구: 신규 {fixed_new}개 / 전체 {len(FIXED_PHRASES)}개")

    # 2. 문제 TTS
    logger.info("문제 목록 로드 중...")
    questions = _scan_questions(exam_id)
    logger.info(f"문제 {len(questions)}개 로드 완료")

    total_segs = 0
    new_segs = 0
    for i, q in enumerate(questions):
        segs = _question_segments(q)
        for text, voice in segs:
            total_segs += 1
            if await _ensure_cached(text, voice, dry_run):
                new_segs += 1
                if not dry_run:
                    await asyncio.sleep(delay)
        if (i + 1) % 20 == 0 or (i + 1) == len(questions):
            logger.info(
                f"  [{i+1}/{len(questions)}] 진행 중 "
                f"(세그먼트 {total_segs}개 중 신규 {new_segs}개)"
            )

    logger.info(
        f"완료: 문제 {len(questions)}개, "
        f"세그먼트 {total_segs}개, 신규 생성 {new_segs}개"
    )


@app.command()
def main(
    exam: str | None = typer.Option(None, help="시험 ID (예: CCA, aip-c01). 없으면 전체"),
    delay: float = typer.Option(0.5, help="TTS 생성 후 대기 시간 (초). edge-tts 부하 방지용"),
    dry_run: bool = typer.Option(False, "--dry-run", help="실제 생성 없이 캐시 미스 목록만 출력"),
) -> None:
    asyncio.run(_run(exam, delay, dry_run))


if __name__ == "__main__":
    app()
