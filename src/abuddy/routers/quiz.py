import json
import random
from datetime import date
from pathlib import Path

import boto3
from fastapi import APIRouter, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from loguru import logger

from abuddy.config import settings
from abuddy.db import questions as qdb
from abuddy.db import schedule as sdb
from abuddy.db import user_profile as updb
from abuddy.db import user_questions as uqdb
from abuddy.services import bedrock
from abuddy.services import quiz_engine as engine
from abuddy.services.auth import NotAuthenticated, get_current_user, get_display_name
from abuddy.services.concept_graph import get_concept, load_graph


def _shuffle_options(question):
    """선택지 순서를 랜덤하게 섞고 correct_indices를 재매핑한 복사본 반환"""
    indices = list(range(len(question.options)))
    random.shuffle(indices)
    shuffled_options = [question.options[i] for i in indices]
    reverse_map = {old: new for new, old in enumerate(indices)}
    new_correct = sorted(reverse_map[i] for i in question.correct_indices)
    return question.model_copy(update={"options": shuffled_options, "correct_indices": new_correct})


_CARDS_PATH = Path(__file__).parent.parent / "data" / "motivation_cards.json"
MOTIVATION_CARDS: list[dict] = json.loads(_CARDS_PATH.read_text(encoding="utf-8"))


def _pick_motivation(user_id: str) -> dict:
    """날짜 + user_id 기반으로 매일 다른 카드 반환 (같은 날·같은 유저는 동일 카드)"""
    idx = (date.today().toordinal() + hash(user_id)) % len(MOTIVATION_CARDS)
    return MOTIVATION_CARDS[idx]


DOMAIN_TITLES: dict[str, dict[int, str]] = {
    "CCA": {
        1: "Agentic Architecture & Orchestration",
        2: "Tool Design & MCP Integration",
        3: "Claude Code Configuration & Workflows",
        4: "Prompt Engineering & Structured Output",
        5: "Context Management & Reliability",
    },
    "aip-c01": {
        1: "Foundation Model 통합·데이터 관리",
        2: "구현 및 통합",
        3: "AI 안전·보안·거버넌스",
        4: "운영 효율화 및 최적화",
        5: "테스트·검증·트러블슈팅",
    },
}

EXAM_DISPLAY_NAMES = {
    "CCA": "Claude Certified Architect – Foundations",
    "aip-c01": "AWS Certified AI Practitioner (AIP-C01)",
}
DAILY_GOAL = 5

router = APIRouter()
templates = Jinja2Templates(directory="src/abuddy/templates")


@router.get("/health")
async def health():
    """현재 배포 상태 확인용 (인증 불필요)"""
    exam = settings.active_exam
    s3_key = f"{exam}/graph/concept_graph.json"
    old_s3_key = "graph/concept_graph.json"

    # S3 경로 존재 여부
    s3 = boto3.client("s3", region_name=settings.aws_region)
    def _s3_exists(key: str) -> bool:
        try:
            s3.head_object(Bucket=settings.s3_bucket, Key=key)
            return True
        except Exception:
            return False

    # 개념 그래프 (캐시에서)
    g = load_graph(exam)

    return JSONResponse({
        "active_exam": exam,
        "s3": {
            "new_path": s3_key,
            "new_path_exists": _s3_exists(s3_key),
            "old_path_exists": _s3_exists(old_s3_key),
        },
        "concept_graph": {
            "nodes": g.number_of_nodes(),
            "edges": g.number_of_edges(),
        },
        "questions": {
            "count": qdb.question_count(exam),
        },
    })
templates.env.globals["enumerate"] = enumerate

OPTION_LABELS = ["A", "B", "C", "D", "E", "F"]


def _user(request: Request) -> str:
    """인증 실패 시 /auth/login 으로 리다이렉트"""
    try:
        return get_current_user(request)
    except NotAuthenticated:
        raise HTTPException(status_code=302, headers={"Location": "/auth/login"})


# ─────────────────────────────────────────────
# 메인 페이지
# ─────────────────────────────────────────────

def _build_domain_stats(user_id: str) -> list[dict]:
    raw = sdb.get_domain_stats(user_id)
    exam = settings.active_exam
    titles = DOMAIN_TITLES.get(exam, DOMAIN_TITLES["aip-c01"])
    return [
        {
            "id": d,
            "title": titles[d],
            "mastered": raw.get(d, {}).get("mastered", 0),
            "total": raw.get(d, {}).get("total", 0),
        }
        for d in range(1, 6)
    ]


def _days_remaining(exam_date: str | None) -> int | None:
    if not exam_date:
        return None
    try:
        return (date.fromisoformat(exam_date) - date.today()).days
    except ValueError:
        return None


@router.get("/", response_class=HTMLResponse)
async def index(request: Request):
    try:
        user_id = get_current_user(request)
    except NotAuthenticated:
        return RedirectResponse("/auth/login")

    profile = updb.get_profile(user_id)
    exam = settings.active_exam
    return templates.TemplateResponse(request, "index.html", {
        "stats": sdb.get_stats(user_id),
        "question_count": qdb.question_count(),
        "profile": profile,
        "days_remaining": _days_remaining(profile.exam_date),
        "daily_goal": DAILY_GOAL,
        "domain_stats": _build_domain_stats(user_id),
        "motivation": _pick_motivation(user_id),
        "username": get_display_name(request),
        "exam_display_name": EXAM_DISPLAY_NAMES.get(exam, exam),
    })


@router.post("/set-exam-date", response_class=HTMLResponse)
async def set_exam_date(request: Request, exam_date: str = Form(...)):
    try:
        user_id = get_current_user(request)
    except NotAuthenticated:
        return RedirectResponse("/auth/login")
    updb.set_exam_date(user_id, exam_date)
    return RedirectResponse("/", status_code=303)


# ─────────────────────────────────────────────
# 다음 문제
# ─────────────────────────────────────────────

@router.get("/quiz", response_class=HTMLResponse)
async def quiz_page(request: Request):
    user_id = _user(request)
    question = engine.get_next_question(user_id)
    if not question:
        return templates.TemplateResponse(request, "no_questions.html")

    concept = get_concept(question.concept_id)
    return templates.TemplateResponse(request, "quiz.html", {
        "question": _shuffle_options(question),
        "concept": concept,
        "labels": OPTION_LABELS,
        "stats": sdb.get_stats(user_id),
        "username": get_display_name(request),
    })


# ─────────────────────────────────────────────
# 답변 제출 (HTMX)
# ─────────────────────────────────────────────

@router.post("/quiz/{question_id}/answer", response_class=HTMLResponse)
async def submit_answer(request: Request, question_id: str):
    user_id = _user(request)
    form = await request.form()

    selected = []
    for key, val in form.multi_items():
        if key == "selected":
            try:
                selected.append(int(val))
            except ValueError:
                pass
    self_confirmed = form.get("self_confirmed") == "true"

    question = qdb.get_question(question_id)
    if not question:
        raise HTTPException(status_code=404, detail="Question not found")

    is_correct, schedule = engine.process_answer(user_id, question, selected, self_confirmed)
    concept = get_concept(question.concept_id)

    return templates.TemplateResponse(request, "partials/feedback.html", {
        "question": question,
        "concept": concept,
        "labels": OPTION_LABELS,
        "selected_indices": selected,
        "is_correct": is_correct,
        "schedule": schedule,
    })


# ─────────────────────────────────────────────
# 팔로업 질문 (HTMX)
# ─────────────────────────────────────────────

@router.post("/quiz/{question_id}/ask", response_class=HTMLResponse)
async def ask_followup(request: Request, question_id: str, user_question: str = Form(...)):
    user_id = _user(request)  # 인증 확인

    question = qdb.get_question(question_id)
    if not question:
        raise HTTPException(status_code=404, detail="Question not found")

    concept = get_concept(question.concept_id)
    concept_name = concept.name if concept else question.concept_id
    correct_text = " / ".join(question.options[i] for i in question.correct_indices)

    answer = bedrock.answer_followup(
        concept_name=concept_name,
        question_text=question.question_text,
        correct_answer_text=correct_text + "\n" + question.explanation,
        user_question=user_question,
    )

    uqdb.save_user_question(
        user_id=user_id,
        parent_question_id=question_id,
        concept_id=question.concept_id,
        domain=question.domain,
        parent_question_text=question.question_text,
        user_question=user_question,
        llm_answer=answer,
    )
    logger.info(f"[{user_id[:8]}] Followup answered + saved for {question_id[:8]}")

    return templates.TemplateResponse(request, "partials/followup_answer.html", {
        "user_question": user_question,
        "answer": answer,
        "question_id": question_id,
    })


# ─────────────────────────────────────────────
# 진도 통계
# ─────────────────────────────────────────────

@router.get("/stats", response_class=HTMLResponse)
async def stats_page(request: Request):
    user_id = _user(request)
    return templates.TemplateResponse(request, "stats.html", {
        "stats": sdb.get_stats(user_id),
        "question_count": qdb.question_count(),
        "domain_stats": _build_domain_stats(user_id),
        "username": get_display_name(request),
    })
