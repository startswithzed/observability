# --- Stage 1: Builder ---
FROM python:3.13-slim AS builder
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

RUN apt-get update && apt-get install -y \
  gcc \
  libpq-dev \
  && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY pyproject.toml uv.lock ./
ENV UV_PROJECT_ENVIRONMENT="/opt/venv"
RUN uv sync --frozen --no-dev --no-install-project

# --- Stage 2: Runtime ---
FROM python:3.13-slim
WORKDIR /app

# Install runtime library for Postgres
RUN apt-get update && apt-get install -y \
  libpq5 \
  curl \
  && rm -rf /var/lib/apt/lists/*

COPY --from=builder /opt/venv /opt/venv
COPY . .

ENV PATH="/opt/venv/bin:$PATH"
ENV PYTHONPATH="/app"
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

CMD ["gunicorn", "src.core.wsgi:application", "--bind", "0.0.0.0:8000", "-w", "4", "--log-level", "info"]