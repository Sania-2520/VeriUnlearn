#!/bin/sh
set -e

export PYTHONNOUSERSITE=1

python -m venv --system-site-packages /tmp/veriunlearn-test-venv
. /tmp/veriunlearn-test-venv/bin/activate

pip install --no-cache-dir -r requirements-dev.txt
python -m alembic upgrade head
exec python -m pytest tests/ -v --tb=short -o asyncio_mode=auto --cov=app --cov-report=term --cov-report=xml
