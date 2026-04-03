"""Amazon Cognito JWT 검증 + 토큰 교환"""
import time
from functools import lru_cache

import httpx
import jwt
from fastapi import Request
from fastapi.responses import RedirectResponse
from loguru import logger

from abuddy.config import settings


class NotAuthenticated(Exception):
    pass


@lru_cache(maxsize=1)
def _get_jwks() -> dict:
    """Cognito 공개키 (JWKS) — 프로세스 생애 1회 캐시"""
    region = settings.aws_region
    pool_id = settings.cognito_user_pool_id
    url = f"https://cognito-idp.{region}.amazonaws.com/{pool_id}/.well-known/jwks.json"
    resp = httpx.get(url, timeout=10)
    resp.raise_for_status()
    logger.info("Fetched Cognito JWKS")
    return resp.json()


def verify_token(id_token: str) -> str:
    """
    Cognito ID 토큰 검증 후 user_id(sub) 반환.
    실패 시 NotAuthenticated 발생.
    """
    if not settings.cognito_user_pool_id:
        raise NotAuthenticated("Cognito not configured")

    jwks = _get_jwks()
    try:
        header = jwt.get_unverified_header(id_token)
        key = next(k for k in jwks["keys"] if k["kid"] == header["kid"])
        public_key = jwt.algorithms.RSAAlgorithm.from_jwk(key)

        issuer = (
            f"https://cognito-idp.{settings.aws_region}.amazonaws.com"
            f"/{settings.cognito_user_pool_id}"
        )
        payload = jwt.decode(
            id_token,
            public_key,
            algorithms=["RS256"],
            audience=settings.cognito_client_id,
            issuer=issuer,
        )
        return payload["sub"]  # user_id
    except StopIteration:
        raise NotAuthenticated("Unknown key ID")
    except jwt.ExpiredSignatureError:
        raise NotAuthenticated("Token expired")
    except Exception as e:
        raise NotAuthenticated(f"Token invalid: {e}")


def get_current_user(request: Request) -> str:
    """FastAPI dependency — 인증 안 됐으면 NotAuthenticated"""
    token = request.cookies.get("id_token")
    if not token:
        raise NotAuthenticated("No token cookie")
    return verify_token(token)


def get_display_name(request: Request) -> str:
    """JWT 클레임에서 표시용 이름 추출 (email 또는 username 앞부분)"""
    token = request.cookies.get("id_token")
    if not token:
        return ""
    try:
        payload = jwt.decode(token, options={"verify_signature": False})
        email = payload.get("email", "")
        if email:
            return email.split("@")[0]
        return payload.get("cognito:username") or payload.get("sub", "")[:8]
    except Exception:
        return ""


async def exchange_code(code: str) -> dict:
    """Cognito authorization code → tokens (ID/access/refresh)"""
    callback_url = f"{settings.app_base_url}/auth/callback"
    token_url = f"https://{settings.cognito_domain}/oauth2/token"
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            token_url,
            data={
                "grant_type": "authorization_code",
                "client_id": settings.cognito_client_id,
                "client_secret": settings.cognito_client_secret,
                "redirect_uri": callback_url,
                "code": code,
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            timeout=15,
        )
        resp.raise_for_status()
        return resp.json()


async def refresh_id_token(refresh_token: str) -> str:
    """refresh_token → 새 id_token. 실패 시 예외 발생."""
    token_url = f"https://{settings.cognito_domain}/oauth2/token"
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            token_url,
            data={
                "grant_type": "refresh_token",
                "client_id": settings.cognito_client_id,
                "client_secret": settings.cognito_client_secret,
                "refresh_token": refresh_token,
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            timeout=15,
        )
        resp.raise_for_status()
        return resp.json()["id_token"]
