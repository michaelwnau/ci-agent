# syntax=docker/dockerfile:1.6

FROM python:3.11-slim AS uv-base

ARG UV_INSTALL_URL="https://astral.sh/uv/install.sh"
RUN apt-get update && apt-get install -y --no-install-recommends \      curl ca-certificates build-essential \    && rm -rf /var/lib/apt/lists/* \    && curl -LsSf ${UV_INSTALL_URL} | sh \    && /root/.local/bin/uv --version

ENV PATH="/root/.local/bin:${PATH}"
ENV UV_LINK_MODE=copy
ENV UV_PROJECT_ENVIRONMENT=/app/.venv

WORKDIR /app

FROM uv-base AS builder

COPY pyproject.toml ./
COPY uv.lock ./ 2>/dev/null || true

RUN uv sync --all-extras --dev || true

COPY src ./src
COPY tests ./tests
COPY .ruff.toml ./.ruff.toml

FROM builder AS qa
RUN uv run ruff check . && uv run ruff format --check .
# RUN uv run pytest -q

FROM python:3.11-slim AS runtime

RUN useradd -m -u 10001 appuser

ENV UV_PROJECT_ENVIRONMENT=/app/.venv
ENV PATH="/app/.venv/bin:${PATH}"

WORKDIR /app
COPY --from=builder /app/.venv /app/.venv
COPY --from=builder /app/src /app/src
COPY pyproject.toml /app/pyproject.toml

EXPOSE 8501

USER appuser

CMD ["streamlit", "run", "src/ci_agent/streamlit_app.py", "--server.port=8501", "--server.address=0.0.0.0"]
