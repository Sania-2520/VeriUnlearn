#!/bin/sh
set -e
export PATH=/app/.local/bin:$PATH
pip install --no-cache-dir -r requirements-dev.txt
alembic upgrade head
exec python -m pytest tests/ -v --tb=short --cov=app --cov-report=term --cov-report=xml
