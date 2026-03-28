import sys

from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from loguru import logger

from abuddy.config import settings
from abuddy.routers.auth import router as auth_router
from abuddy.routers.quiz import router as quiz_router
from abuddy.services.auth import NotAuthenticated

# loguru 설정
logger.remove()
logger.add(sys.stderr, level="DEBUG", format="{time:HH:mm:ss} | {level:<8} | {message}")
logger.add("logs/abuddy.log", rotation="10 MB", retention="7 days", level="INFO")

app = FastAPI(title="ABuddy — AWS GenAI Cert Study", version="0.1.0")
app.include_router(auth_router)
app.include_router(quiz_router)


@app.exception_handler(NotAuthenticated)
async def auth_redirect(_: Request, __: NotAuthenticated):
    return RedirectResponse("/auth/login")


@app.on_event("startup")
async def startup():
    logger.info("ABuddy starting up")
    from abuddy.services.concept_graph import load_graph
    try:
        g = load_graph()
        logger.info(f"Concept graph ready: {g.number_of_nodes()} concepts")
    except Exception as e:
        logger.warning(f"Could not load concept graph: {e}")
