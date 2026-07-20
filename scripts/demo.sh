#!/usr/bin/env bash
# =============================================================================
# VeriUnlearn — demo script
# Brings the stack up, seeds demo data, and prints a guided tour.
# Intended for judges / quick evaluation. Should complete in < 10 minutes.
# Usage: ./scripts/demo.sh
# =============================================================================
set -euo pipefail

cd "$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo "=============================================================="
echo "  VeriUnlearn — Automated Demo"
echo "=============================================================="
echo "This will: (1) start the stack, (2) seed demo data, (3) guide you."
echo ""

# 1. Bring up the stack + seed
./scripts/setup.sh --seed

# 2. Health check
./scripts/healthcheck.sh

# 3. Guided tour
FRONTEND="http://localhost:${FRONTEND_PORT:-3000}"
BACKEND="http://localhost:${BACKEND_PORT:-8000}"
echo ""
echo "=============================================================="
echo "  Guided Tour (≈ 8 minutes)"
echo "=============================================================="
echo "1. Open the dashboard:        $FRONTEND"
echo "   Log in with: demo@veriunlearn.ai / DemoPassword123!"
echo ""
echo "2. Submit a deletion request: $FRONTEND/dashboard/unlearning"
echo "   (or inspect offline: demo/deletion-requests/sample-requests.json)"
echo ""
echo "3. View the verification cert: $FRONTEND/dashboard/audit"
echo "   (offline: demo/verification-certificates/sample-certificates.json)"
echo ""
echo "4. Compare algorithms:        $FRONTEND/dashboard/benchmarks"
echo "   (offline: demo/benchmark-reports/sample-report.json)"
echo ""
echo "5. Explainability:            $FRONTEND/dashboard/explainability"
echo "6. Audit / compliance log:    $FRONTEND/dashboard/audit"
echo "7. API docs:                  $BACKEND/docs"
echo ""
echo "Full walkthrough: docs/DEMO_WALKTHROUGH.md"
echo "Demo video outline: docs/DEMO_VIDEO_OUTLINE.md"
echo ""
echo "Tear down when done: ./scripts/teardown.sh"
