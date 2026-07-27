# syntax=docker/dockerfile:1

# ---- Builder: create virtualenv with dependencies ----
FROM python:3.14-slim AS builder

# Copy uv binary from the official image (avoids installing it via curl each build)
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

# gcc/libc-dev only needed in case a dependency lacks a prebuilt wheel (kept out of runtime)
RUN sed -i 's/deb.debian.org/mirrors.aliyun.com/g' /etc/apt/sources.list.d/debian.sources \
    && apt-get update && apt-get install -y --no-install-recommends gcc libc-dev \
    && rm -rf /var/lib/apt/lists/*

# Aliyun PyPI mirror for faster downloads in China
ENV UV_INDEX_URL=https://mirrors.aliyun.com/pypi/simple/

# Install dependencies only (cached unless pyproject/lock change)
COPY pyproject.toml uv.lock README.md ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --no-install-project

# ---- Runtime: slim image, no build tools ----
FROM python:3.14-slim

WORKDIR /app

COPY --from=builder /app/.venv /app/.venv
COPY app ./app
COPY migrations ./migrations
COPY alembic.ini ./
COPY migrate.sh ./
RUN chmod +x migrate.sh && mkdir -p /app/data

ENV PATH="/app/.venv/bin:$PATH"

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
