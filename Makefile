.PHONY: help install dev lint test build run clean

help:
	@echo "VeriUnlearn Development Commands"
	@echo "================================"
	@echo "make install       - Install Python and Node.js dependencies"
	@echo "make dev           - Start development environment (Docker + backend + frontend)"
	@echo "make dev-backend   - Start FastAPI backend only"
	@echo "make dev-frontend  - Start Next.js frontend only"
	@echo "make worker        - Start Celery worker"
	@echo "make lint          - Run linting checks"
	@echo "make test          - Run all tests"
	@echo "make test-unit     - Run unit tests"
	@echo "make test-int      - Run integration tests"
	@echo "make db-migrate    - Run Alembic migrations"
	@echo "make db-revision   - Create new Alembic migration"
	@echo "make build         - Build Docker images"
	@echo "make deploy        - Full production deployment"
	@echo "make seed          - Seed demo data"
	@echo "make benchmark     - Run benchmark suite"
	@echo "make graphs        - Generate research graphs"
	@echo "make clean         - Clean temporary files"

install:
	pip install -r backend/requirements.txt
	cd frontend && npm install

dev:
	docker compose up -d postgres redis qdrant minio
	$(MAKE) db-migrate
	$(MAKE) dev-backend &

dev-backend:
	cd backend && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

dev-frontend:
	cd frontend && npm run dev

worker:
	cd backend && celery -A app.worker.celery_app worker --loglevel=info --concurrency=1

lint:
	cd backend && ruff check .
	cd backend && mypy app
	cd frontend && npm run lint

test:
	cd backend && KMP_DUPLICATE_LIB_OK=TRUE pytest -v --cov=app --cov-report=term-missing

test-unit:
	cd backend && KMP_DUPLICATE_LIB_OK=TRUE pytest -v -m unit

test-int:
	cd backend && KMP_DUPLICATE_LIB_OK=TRUE pytest -v -m integration

db-migrate:
	cd backend && alembic upgrade head

db-revision:
	cd backend && alembic revision --autogenerate -m "$(message)"

build:
	docker compose build

deploy:
	docker compose build
	docker compose up -d
	@echo "Deployment complete. Check: http://localhost:8000/health"

seed:
	python infra/scripts/seed_demo_data.py

benchmark:
	python infra/scripts/run_benchmarks.py

graphs:
	python infra/scripts/generate_graphs.py

clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	rm -rf .pytest_cache .coverage htmlcov coverage.xml
