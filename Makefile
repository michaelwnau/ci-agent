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
	uv venv .venv --python $(PY)
	UV_PROJECT_ENVIRONMENT=.venv uv sync --all-extras --dev

.PHONY: lint
lint:
	UV_PROJECT_ENVIRONMENT=.venv uv run ruff check .
	UV_PROJECT_ENVIRONMENT=.venv uv run ruff format --check .

.PHONY: test
test:
	UV_PROJECT_ENVIRONMENT=.venv uv run pytest -q

.PHONY: run
run:
	UV_PROJECT_ENVIRONMENT=.venv uv run streamlit run src/ci_agent/streamlit_app.py

.PHONY: docker-build
docker-build:
	docker build -t ci-agent:latest .

.PHONY: docker-run
docker-run:
	docker run --rm -p 8501:8501 -e OPENAI_API_KEY ci-agent:latest
