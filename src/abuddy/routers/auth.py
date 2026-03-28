from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from loguru import logger

from abuddy.config import settings
from abuddy.services import auth

router = APIRouter(prefix="/auth")
templates = Jinja2Templates(directory="src/abuddy/templates")
templates.env.globals["enumerate"] = enumerate

_COOKIE_MAX_AGE = 60 * 60 * 8  # 8시간


@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    """로그인 페이지 — Cognito Hosted UI로 리다이렉트 버튼 제공"""
    if not settings.cognito_domain:
        return templates.TemplateResponse("login_no_cognito.html", {"request": request})
    return templates.TemplateResponse("login.html", {
        "request": request,
        "cognito_url": _cognito_auth_url(),
    })


@router.get("/callback")
async def cognito_callback(request: Request, code: str = "", error: str = ""):
    """Cognito Hosted UI 콜백 — 코드를 토큰으로 교환하고 쿠키 설정"""
    if error:
        logger.warning(f"Cognito error: {error}")
        return RedirectResponse("/auth/login?error=cognito")

    tokens = await auth.exchange_code(code)
    id_token = tokens.get("id_token", "")
    logger.info("User logged in via Cognito")

    response = RedirectResponse("/", status_code=302)
    response.set_cookie(
        "id_token",
        id_token,
        max_age=_COOKIE_MAX_AGE,
        httponly=True,
        samesite="lax",
    )
    return response


@router.get("/logout")
async def logout():
    callback = f"{settings.app_base_url}/auth/login"
    cognito_logout = (
        f"https://{settings.cognito_domain}/logout"
        f"?client_id={settings.cognito_client_id}"
        f"&logout_uri={callback}"
    )
    response = RedirectResponse(cognito_logout, status_code=302)
    response.delete_cookie("id_token")
    return response


def _cognito_auth_url() -> str:
    callback = f"{settings.app_base_url}/auth/callback"
    return (
        f"https://{settings.cognito_domain}/oauth2/authorize"
        f"?response_type=code"
        f"&client_id={settings.cognito_client_id}"
        f"&redirect_uri={callback}"
        f"&scope=openid+email+profile"
    )
