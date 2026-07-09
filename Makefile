.PHONY: setup dev dev-backend dev-frontend dev-ml-engine test lint build clean

# ─── Setup ──────────────────────────────────────────────────────

setup: setup-backend setup-frontend setup-ml-engine

setup-backend:
	cd packages/backend && python -m venv .venv && \
		.venv\Scripts\pip install -r requirements.txt -r requirements-dev.txt

setup-frontend:
	cd packages/frontend && npm install

setup-ml-engine:
	cd packages/ml-engine && python -m venv .venv && \
		.venv\Scripts\pip install -r requirements.txt -r requirements-dev.txt

# ─── Development ────────────────────────────────────────────────

dev:
	docker compose -f infra/docker/docker-compose.yml up --build

dev-backend:
	cd packages/backend && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

dev-frontend:
	cd packages/frontend && npm run dev

dev-ml-engine:
	cd packages/ml-engine && uvicorn api:app --reload --host 0.0.0.0 --port 8001

# ─── Testing ───────────────────────────────────────────────────

test: test-backend test-frontend test-ml-engine

test-backend:
	cd packages/backend && pytest --cov --cov-report=term-missing --cov-report=html -v

test-frontend:
	cd packages/frontend && npm test

test-ml-engine:
	cd packages/ml-engine && pytest --cov --cov-report=term-missing --cov-report=html -v

test-integration:
	cd packages/backend && pytest tests/integration -v

test-performance:
	k6 run tests/performance/load-test.js

# ─── Linting ────────────────────────────────────────────────────

lint: lint-backend lint-frontend lint-ml-engine

lint-backend:
	cd packages/backend && ruff check . && mypy .

lint-frontend:
	cd packages/frontend && npm run lint

lint-ml-engine:
	cd packages/ml-engine && ruff check . && mypy .

typecheck-backend:
	cd packages/backend && mypy .

typecheck-frontend:
	cd packages/frontend && npm run typecheck

typecheck-ml-engine:
	cd packages/ml-engine && mypy .

# ─── Building ──────────────────────────────────────────────────

build: build-backend build-frontend build-ml-engine

build-backend:
	docker build -t ghcr.io/veriunlearn/backend:latest -f packages/backend/Dockerfile packages/backend

build-frontend:
	docker build -t ghcr.io/veriunlearn/frontend:latest -f packages/frontend/Dockerfile packages/frontend

build-ml-engine:
	docker build -t ghcr.io/veriunlearn/ml-engine:latest -f packages/ml-engine/Dockerfile packages/ml-engine

# ─── Database ──────────────────────────────────────────────────

migrate:
	cd packages/backend && alembic upgrade head

migrate-downgrade:
	cd packages/backend && alembic downgrade -1

migrate-create:
	cd packages/backend && alembic revision --autogenerate -m "$(name)"

# ─── Cleanup ──────────────────────────────────────────────────

clean:
	rm -rf packages/backend/.venv
	rm -rf packages/frontend/node_modules
	rm -rf packages/ml-engine/.venv
	rm -rf .pytest_cache
	rm -rf htmlcov
	rm -rf .coverage
	rm -rf dist
	rm -rf build
	rm -rf *.egg-info
	docker compose -f infra/docker/docker-compose.yml down -v
	docker system prune -f
