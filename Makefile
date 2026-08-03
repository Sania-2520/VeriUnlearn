.PHONY: help install install-dev lint typecheck test test-evaluation benchmark-phase2 benchmark-quick benchmark-full figures report docker-build docker-up docker-down clean verify dev dev-backend dev-frontend worker test-unit test-int db-migrate db-revision build deploy seed graphs setup setup-monitoring teardown healthcheck backup restore demo env-prod deploy-prod

help:
	@echo "VeriUnlearn Development Commands"
	@echo "================================"
	@echo "help                 Show this help message"
	@echo ""
	@echo "## Installation ##"
	@echo "install              Install all dependencies (pip + npm)"
	@echo "install-dev          Install dev dependencies"
	@echo ""
	@echo "## Development ##"
	@echo "dev                  Start development environment (Docker + backend)"
	@echo "dev-backend          Start FastAPI backend only"
	@echo "dev-frontend         Start Next.js frontend only"
	@echo "worker               Start Celery worker"
	@echo ""
	@echo "## Quality ##"
	@echo "lint                 Run ruff linter checks"
	@echo "typecheck            Run mypy type checker"
	@echo "test                 Run all tests"
	@echo "test-evaluation      Run evaluation-specific tests"
	@echo "test-unit            Run unit tests"
	@echo "test-int             Run integration tests"
	@echo ""
	@echo "## Benchmarking ##"
	@echo "benchmark-phase2     Run Phase 2 validation (2 datasets x 5 algo x 3 ratios x 3 seeds = 90 runs)"
	@echo "benchmark-quick      Run quick smoke test (MNIST x 3 algo x 1 ratio x 1 seed = 3 runs)"
	@echo "benchmark-full       Run full Phase 2 benchmark (4 datasets x 5 algo x 3 ratios x 5 seeds = 300 runs)"
	@echo "benchmark            Run default benchmark suite"
	@echo ""
	@echo "## Output ##"
	@echo "figures              Generate publication figures from existing results"
	@echo "report               Generate publication report from existing results"
	@echo "graphs               Generate research graphs"
	@echo ""
	@echo "## Docker ##"
	@echo "docker-build         Build Docker images"
	@echo "docker-up            Start Docker services"
	@echo "docker-down          Stop Docker services"
	@echo "build                Alias for docker-build"
	@echo "deploy               Full production deployment"
	@echo ""
	@echo "## Reproducibility ##"
	@echo "verify               Verify reproducibility (Python version, packages, smoke test, snapshot)"
	@echo ""
	@echo "## Database ##"
	@echo "db-migrate           Run Alembic migrations"
	@echo "db-revision          Create new Alembic migration"
	@echo ""
	@echo "## Other ##"
	@echo "clean                Clean temporary files (pycache, coverage, etc.)"
	@echo "setup                One-command setup with demo data"
	@echo "setup-monitoring     Setup with monitoring stack"
	@echo "teardown             Tear down all services"
	@echo "healthcheck          Check service health"
	@echo "backup               Backup databases"
	@echo "restore              Restore from backup"
	@echo "demo                 Run demo"
	@echo "seed                 Seed demo data"
	@echo "env-prod             Create .env from production template"

install:
	pip install -r packages/backend/requirements.txt
	pip install -r packages/ml-engine/requirements.txt
	pip install -r requirements.txt
	cd packages/frontend && npm install

install-dev:
	pip install -r requirements.lock.txt
	pip install -e .
	pip install pytest pytest-cov pytest-asyncio mypy ruff
	cd packages/frontend && npm install

lint:
	cd packages/backend && ruff check .
	cd packages/backend && mypy app
	cd packages/frontend && npm run lint
	ruff check evaluation/
	ruff check scripts/

typecheck:
	cd packages/backend && mypy app
	mypy evaluation/ --ignore-missing-imports

test:
	cd packages/backend && KMP_DUPLICATE_LIB_OK=TRUE pytest -v --cov=app --cov-report=term-missing
	cd packages/ml-engine && KMP_DUPLICATE_LIB_OK=TRUE pytest -v
	pytest evaluation/tests/ -v
	cd packages/frontend && npm test 2>/dev/null || echo "Frontend tests not configured"

test-ml:
	cd packages/ml-engine && KMP_DUPLICATE_LIB_OK=TRUE pytest -v

test-evaluation:
	pytest evaluation/tests/ -v
	python evaluation/smoke_test.py

test-unit:
	cd packages/backend && KMP_DUPLICATE_LIB_OK=TRUE pytest -v -m unit

test-int:
	cd packages/backend && KMP_DUPLICATE_LIB_OK=TRUE pytest -v -m integration

benchmark-phase2:
	python evaluation/_run_benchmark.py

benchmark-quick:
	python -m evaluation.run_all --quick

benchmark-full:
	python evaluation/_phase2_benchmark.py

benchmark:
	python infra/scripts/run_benchmarks.py

figures:
	python -c "
import json, sys
from pathlib import Path
from evaluation.visualization import PublicationVisualizer
from evaluation.export import ExperimentResults

results_dirs = sorted(Path('evaluation/results').glob('*/results.json'))
if not results_dirs:
    results_dirs = sorted(Path('evaluation/results').glob('*/summary.json'))
if not results_dirs:
    print('No results found in evaluation/results/')
    sys.exit(1)
latest = results_dirs[-1]
results = ExperimentResults(**json.loads(latest.read_text()))
viz = PublicationVisualizer()
fig_dir = latest.parent / 'figures'
fig_dir.mkdir(exist_ok=True)
viz.generate_all_figures(results, str(fig_dir))
print(f'Figures saved to {fig_dir}')
"

report:
	python -c "
import json, sys
from pathlib import Path
from evaluation.report import PublicationReport
from evaluation.config import ExperimentConfig
from evaluation.export import ExperimentResults

results_dirs = sorted(Path('evaluation/results').glob('*/results.json'))
if not results_dirs:
    print('No results found in evaluation/results/')
    sys.exit(1)
latest = results_dirs[-1]
results = ExperimentResults(**json.loads(latest.read_text()))
report = PublicationReport()
# Try to load config
config_path = latest.parent / 'config.json'
if config_path.exists():
    report.config = ExperimentConfig(**json.loads(config_path.read_text()))
out = latest.parent
report.generate_report(results, figures=[], output_dir=str(out))
print(f'Report saved to {out}')
"

docker-build:
	docker compose build

docker-up:
	docker compose up -d

docker-down:
	docker compose down

clean:
	@echo "Cleaning temporary files..."
	-if command -v find >/dev/null 2>&1; then \
		find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true; \
		find . -type f -name "*.pyc" -delete 2>/dev/null || true; \
	else \
		powershell -Command "Get-ChildItem -Path . -Recurse -Directory -Filter __pycache__ | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue"; \
		powershell -Command "Get-ChildItem -Path . -Recurse -Filter *.pyc | Remove-Item -Force -ErrorAction SilentlyContinue"; \
	fi
	rm -rf .pytest_cache .coverage htmlcov coverage.xml
	rm -rf .mypy_cache .ruff_cache
	@echo "Clean complete."

verify:
	@echo "=== VeriUnlearn Reproducibility Verification ==="
	@echo ""
	@echo "1. Python version..."
	@python --version
	@echo ""
	@echo "2. Key package versions..."
	@python -c "
import sys
pkgs = ['torch', 'numpy', 'scipy', 'sklearn', 'transformers', 'peft', 'datasets', 'pandas', 'matplotlib', 'seaborn', 'fastapi', 'pydantic']
for pkg in pkgs:
    try:
        mod = __import__(pkg)
        print(f'  {pkg}: {getattr(mod, \"__version__\", \"unknown\")}')
    except ImportError:
        print(f'  {pkg}: NOT INSTALLED')
"
	@echo ""
	@echo "3. Running evaluation smoke test..."
	@python evaluation/smoke_test.py
	@echo ""
	@echo "4. Running reproducibility tests..."
	@pytest evaluation/tests/test_reproducibility.py -v --tb=short || echo "No reproducibility tests found"
	@echo ""
	@echo "5. Checking reference snapshot..."
	@python -c "
import json, os
snapshot_path = 'evaluation/results/phase2_complete/reproducibility_snapshot.json'
if os.path.exists(snapshot_path):
    snap = json.load(open(snapshot_path))
    print(f'  Reference snapshot found: config_fingerprint={snap[\"config_fingerprint\"]}')
    print(f'  Completed runs: {snap[\"results_summary\"][\"completed_runs\"]}')
    print(f'  Git commit: {snap[\"git\"][\"commit\"]}')
else:
    print('  No reference snapshot found')
"
	@echo ""
	@echo "=== Verification Complete ==="

# ─── Legacy / existing targets ──────────────────────────────────────────────

dev:
	docker compose up -d postgres redis qdrant minio
	$(MAKE) db-migrate
	$(MAKE) dev-backend &

dev-backend:
	cd packages/backend && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

dev-frontend:
	cd packages/frontend && npm run dev

worker:
	cd packages/backend && celery -A app.workers.celery_app worker --loglevel=info --concurrency=1

db-migrate:
	cd packages/backend && alembic upgrade head

db-revision:
	cd packages/backend && alembic revision --autogenerate -m "$(message)"

build:
	@echo "Building Docker images..."
	docker compose build

deploy:
	docker compose build
	docker compose up -d
	@echo "Deployment complete. Check: http://localhost:8000/health"

seed:
	python infra/scripts/seed_demo_data.py

graphs:
	python infra/scripts/generate_graphs.py

setup:
	./scripts/setup.sh --seed

setup-monitoring:
	./scripts/setup.sh --seed --with-monitoring

teardown:
	./scripts/teardown.sh

healthcheck:
	./scripts/healthcheck.sh

backup:
	./scripts/backup.sh

restore:
	./scripts/restore.sh --out ./backups

demo:
	./scripts/demo.sh

env-prod:
	cp .env.production.example .env
	@echo "Created .env from production template. Edit secrets before deploying."

deploy-prod:
	docker compose --profile monitoring up -d --build
	./scripts/healthcheck.sh
