PY=python3.11

.PHONY: help
help:
	@echo "make setup        - create venv and sync deps with uv"
	@echo "make lint         - run ruff"
	@echo "make test         - run pytest"
	@echo "make run          - run Streamlit UI locally"
	@echo "make docker-build - build container"
	@echo "make docker-run   - run container on :8501"

.PHONY: setup
setup:
	uv venv .venv --python $(PY) --clear
ifeq ($(OS),Windows_NT)
	powershell -ExecutionPolicy Bypass -Command "$$env:UV_PROJECT_ENVIRONMENT='.venv'; uv sync --all-extras --dev; uv pip install -e ."
else
	UV_PROJECT_ENVIRONMENT=.venv uv sync --all-extras --dev
	UV_PROJECT_ENVIRONMENT=.venv uv pip install -e .
endif

.PHONY: lint
lint:
ifeq ($(OS),Windows_NT)
	powershell -ExecutionPolicy Bypass -Command "$$env:UV_PROJECT_ENVIRONMENT='.venv'; uv run ruff check ."
	powershell -ExecutionPolicy Bypass -Command "$$env:UV_PROJECT_ENVIRONMENT='.venv'; uv run ruff format --check ."
else
	UV_PROJECT_ENVIRONMENT=.venv uv run ruff check .
	UV_PROJECT_ENVIRONMENT=.venv uv run ruff format --check .
endif

.PHONY: test
test:
ifeq ($(OS),Windows_NT)
	powershell -ExecutionPolicy Bypass -Command "$$env:UV_PROJECT_ENVIRONMENT='.venv'; uv run pytest -q"
else
	UV_PROJECT_ENVIRONMENT=.venv uv run pytest -q
endif

.PHONY: run
run:
ifeq ($(OS),Windows_NT)
	powershell -ExecutionPolicy Bypass -Command "$$env:UV_PROJECT_ENVIRONMENT='.venv'; uv run streamlit run src/ci_agent/streamlit_app.py"
else
	UV_PROJECT_ENVIRONMENT=.venv uv run streamlit run src/ci_agent/streamlit_app.py
endif

.PHONY: docker-build
docker-build:
	docker build -t ci-agent:latest .

.PHONY: docker-run
docker-run:
	docker run --rm -p 8501:8501 -e OPENAI_API_KEY ci-agent:latest

.PHONY: podman-build
podman-build:
	podman build -t ci-agent:latest .

.PHONY: podman-run
podman-run:
	podman run --rm -p 8501:8501 -e OPENAI_API_KEY ci-agent:latest

# Generic container build/run helpers. On Unix-like systems these will prefer
# podman when available, otherwise fall back to docker. On Windows make will
# continue to use the explicit `docker-*` targets unless you call the
# `podman-*` targets directly.
.PHONY: container-build
container-build:
	@echo "Detecting container runtime (prefer podman)..."; \
	if command -v podman >/dev/null 2>&1; then \
		echo "Using podman"; podman build -t ci-agent:latest .; \
	else \
		echo "podman not found, falling back to docker"; docker build -t ci-agent:latest .; \
	fi

.PHONY: container-run
container-run:
	@echo "Detecting container runtime (prefer podman)..."; \
	if command -v podman >/dev/null 2>&1; then \
		echo "Using podman"; podman run --rm -p 8501:8501 -e OPENAI_API_KEY ci-agent:latest; \
	else \
		echo "podman not found, falling back to docker"; docker run --rm -p 8501:8501 -e OPENAI_API_KEY ci-agent:latest; \
	fi
