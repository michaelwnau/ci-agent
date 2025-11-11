# syntax=docker/dockerfile:1.6

FROM python:3.11-slim AS uv-base

ARG UV_INSTALL_URL="https://astral.sh/uv/install.sh"
ENV UV_INSTALL_URL=${UV_INSTALL_URL}
# Install system deps and uv tool in a robust way. Fail fast on missing URL.
RUN set -eux; \
	export DEBIAN_FRONTEND=noninteractive; \
	apt-get update; \
	apt-get install -y --no-install-recommends \
		curl \
		ca-certificates \
		build-essential; \
	rm -rf /var/lib/apt/lists/*; \
	if [ -z "${UV_INSTALL_URL}" ]; then echo "UV_INSTALL_URL is not set" >&2; exit 1; fi; \
	curl -fsSL "${UV_INSTALL_URL}" | sh; \
	/root/.local/bin/uv --version

ENV PATH="/root/.local/bin:${PATH}"
ENV UV_LINK_MODE=copy
ENV UV_PROJECT_ENVIRONMENT=/app/.venv

WORKDIR /app

FROM uv-base AS builder

COPY pyproject.toml ./
# uv.lock is present in the repository; copy it directly. (Previous form with shell redirection is invalid Dockerfile syntax.)
COPY uv.lock ./

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
