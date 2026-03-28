from fastapi import APIRouter, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from loguru import logger

from abuddy.db import questions as qdb
from abuddy.db import schedule as sdb
from abuddy.services import bedrock
from abuddy.services import quiz_engine as engine
from abuddy.services.auth import NotAuthenticated, get_current_user
from abuddy.services.concept_graph import get_concept

router = APIRouter()
templates = Jinja2Templates(directory="src/abuddy/templates")
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

@router.get("/", response_class=HTMLResponse)
async def index(request: Request):
    try:
        user_id = get_current_user(request)
    except NotAuthenticated:
        return RedirectResponse("/auth/login")
    return templates.TemplateResponse(request, "index.html", {
        "stats": sdb.get_stats(user_id),
        "question_count": qdb.question_count(),
    })


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
        "question": question,
        "concept": concept,
        "labels": OPTION_LABELS,
        "stats": sdb.get_stats(user_id),
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
    logger.info(f"[{user_id[:8]}] Followup answered for {question_id[:8]}")

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
    })
