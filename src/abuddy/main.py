import os
import sys
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from loguru import logger

from abuddy.routers.auth import router as auth_router
from abuddy.routers.quiz import router as quiz_router
from abuddy.services.auth import NotAuthenticated

# loguru 설정
_log_dir = Path("/tmp/logs") if os.environ.get("AWS_LAMBDA_FUNCTION_NAME") else Path("logs")
_log_dir.mkdir(parents=True, exist_ok=True)

logger.remove()
logger.add(sys.stderr, level="DEBUG", format="{time:HH:mm:ss} | {level:<8} | {message}")
logger.add(str(_log_dir / "abuddy.log"), rotation="10 MB", retention="7 days", level="INFO")

app = FastAPI(title="ABuddy — AI Cert Study", version="0.1.0")
app.mount("/static", StaticFiles(directory=str(Path(__file__).parent / "static")), name="static")
app.include_router(auth_router)
app.include_router(quiz_router)


@app.exception_handler(NotAuthenticated)
async def auth_redirect(_: Request, __: NotAuthenticated):
    return RedirectResponse("/auth/login")


_ERROR_HTML = """<!DOCTYPE html>
<html lang="ko">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>오류 — ABuddy</title>
  <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-gray-50 min-h-screen flex items-center justify-center font-sans">
  <div class="text-center">
    <div class="text-6xl mb-4">⚠️</div>
    <h1 class="text-xl font-bold text-gray-800 mb-2">서버 오류가 발생했습니다</h1>
    <p class="text-gray-500 mb-6">잠시 후 다시 시도해 주세요.</p>
    <a href="/" class="inline-block bg-orange-500 text-white px-6 py-2 rounded-xl hover:bg-orange-600 transition-colors">
      홈으로 돌아가기
    </a>
  </div>
</body>
</html>"""


@app.exception_handler(Exception)
async def generic_error(request: Request, exc: Exception):
    # HTTPException이나 RequestValidationError는 FastAPI 기본 처리에 맡김
    from fastapi.exceptions import HTTPException
    if isinstance(exc, (HTTPException, RequestValidationError)):
        raise exc
    logger.exception(f"Unhandled error on {request.url}: {exc}")
    return HTMLResponse(content=_ERROR_HTML, status_code=500)


@app.on_event("startup")
async def startup():
    logger.info("ABuddy starting up")
    from abuddy.services.concept_graph import load_graph
    try:
        g = load_graph()
        logger.info(f"Concept graph ready: {g.number_of_nodes()} concepts")
    except Exception as e:
        logger.warning(f"Could not load concept graph: {e}")


# Lambda handler (로컬 실행 시에는 무시됨)
from mangum import Mangum  # noqa: E402
handler = Mangum(app, lifespan="off")
