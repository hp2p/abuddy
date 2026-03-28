FROM python:3.12-slim

# uv 설치
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

# 의존성 먼저 복사 (캐시 활용)
COPY pyproject.toml .
RUN uv sync --no-dev --no-install-project

# 소스 복사
COPY src/ src/
COPY scripts/ scripts/

# 로그 디렉토리
RUN mkdir -p logs

ENV PYTHONPATH=/app/src
ENV UV_SYSTEM_PYTHON=1

EXPOSE 8002

CMD ["uv", "run", "uvicorn", "abuddy.main:app", "--host", "0.0.0.0", "--port", "8002"]
