# Troubleshooting Guide — VeriUnlearn

## Common Installation Issues

### Backend won't start

```bash
# Check PostgreSQL is running
docker compose ps postgres
docker compose logs postgres

# Check database migration
cd packages/backend && alembic upgrade head

# Check port availability
netstat -ano | findstr :8000

# Check Python version (requires 3.13+)
python --version

# Check environment variables
# Ensure .env exists and has required values
ls .env
grep -E "^(JWT_SECRET_KEY|APP_SECRET_KEY|DATABASE_URL)" .env
```

### Python dependency conflicts

```bash
# Recreate virtual environment
rm -rf .venv
python -m venv .venv
.\\.venv\\Scripts\\activate   # Windows
source .venv/bin/activate      # Linux/macOS
pip install -r packages/backend/requirements.txt

# Check for conflicting versions
pip check

# Use exact versions from requirements.txt
pip install --no-deps -r packages/backend/requirements.txt
```

### Makefile commands fail on Windows

```powershell
# Use PowerShell equivalents:
# Instead of `make install`:
pip install -r packages/backend/requirements.txt
cd packages/frontend && npm install

# Instead of `make dev-backend`:
uvicorn app.main:app --reload --port 8000

# Instead of `make dev-frontend`:
npm run dev
```

---

## Docker / Container Issues

### Docker build fails

```bash
# Clear Docker cache
docker compose build --no-cache

# Check Docker disk space
docker system df

# Prune unused resources
docker system prune -f

# Check Docker version (requires 24+)
docker --version
docker compose version

# Build specific service for debugging
docker compose build --no-cache backend
```

### Container health checks failing

```bash
# Check all container statuses
docker compose ps

# View logs for specific service
docker compose logs backend
docker compose logs ml-engine
docker compose logs postgres

# Check health endpoint
curl http://localhost:8000/health
curl http://localhost:8001/health

# Inspect container resource usage
docker stats
```

### Container exits immediately

```bash
# Check container logs
docker compose logs <service>

# Common causes:
# - Missing .env file (check `docker compose config`)
# - Port conflicts (change port mapping)
# - Database not ready (add depends_on with healthcheck)
# - Insufficient memory (check with `docker stats`)

# Verify environment is loaded
docker compose run --rm backend env | grep APP_ENV
```

### Volume permission issues

```bash
# On Linux, ensure user IDs match
# Check current user ID
id -u

# If needed, set user ID in docker-compose.override.yml
# user: "${UID:-1000}:${GID:-1000}"

# On Windows, ensure shared drives are enabled in Docker Desktop
```

---

## Database Connection Issues

### PostgreSQL connection refused

```bash
# Check if PostgreSQL is running
docker compose ps postgres
docker compose logs postgres

# Test connection
docker compose exec postgres pg_isready -U veriunlearn

# Check DATABASE_URL in .env
# Should be: postgresql+asyncpg://veriunlearn:veriunlearn_secret@localhost:5432/veriunlearn

# For Docker-to-Docker, use service name:
# postgresql+asyncpg://veriunlearn:veriunlearn_secret@postgres:5432/veriunlearn
```

### Migration failures

```bash
# Check current migration state
cd packages/backend
alembic current

# View migration history
alembic history

# Apply pending migrations
alembic upgrade head

# Roll back last migration
alembic downgrade -1

# Reset database (development only)
alembic downgrade base
alembic upgrade head
```

### Redis connection issues

```bash
# Check if Redis is running
docker compose ps redis
docker compose logs redis

# Test connectivity
docker compose exec redis redis-cli -a veriunlearn_secret ping

# Check REDIS_URL in .env
# Should be: redis://:veriunlearn_secret@localhost:6379/0

# Clear Redis cache (development)
docker compose exec redis redis-cli -a veriunlearn_secret FLUSHALL
```

---

## ML Engine Issues

### ML Engine not responding

```bash
# Check GPU availability
nvidia-smi

# Check ML Engine logs
docker compose logs ml-engine

# Test direct health
curl http://localhost:8001/health

# Check model download status
# First run may take several minutes to download Qwen2.5 model
docker compose logs ml-engine | grep "model"

# Verify ML Engine port
curl http://localhost:8001/controller/health
```

### CUDA / GPU issues

```bash
# Verify CUDA is available
python -c "import torch; print(torch.cuda.is_available())"
python -c "import torch; print(torch.version.cuda)"

# Check PyTorch CUDA version matches system CUDA
python -c "import torch; print(torch.cuda.get_device_name(0))"

# Fall back to CPU by setting DEVICE=cpu in .env
# DEVICE=cpu
```

### Out of memory (GPU)

```bash
# Reduce quantization bits (default: 4)
# QUANTIZATION_BITS=4  →  QUANTIZATION_BITS=8

# Reduce batch size
# Update in training configuration

# Use smaller base model
# BASE_MODEL_NAME=Qwen/Qwen2.5-0.5B-Instruct

# Limit concurrent inference requests
# Update Celery concurrency: CELERY_WORKER_CONCURRENCY=1
```

### LoRA training fails

```bash
# Check disk space for checkpoints
df -h

# Check PEFT availability
python -c "from peft import LoraConfig; print('OK')"

# Verify base model is downloaded
docker compose exec ml-engine python -c "from transformers import AutoModel; AutoModel.from_pretrained('Qwen/Qwen2.5-1.5B-Instruct')"

# Increase timeout for large models
# LoRA training on 7B+ models may require 30+ minutes
```

---

## Performance Problems

### Slow API responses

```bash
# Check database query performance
# Enable SQL query logging
APP_DEBUG=true

# Check connection pool exhaustion
# Increase pool size in DATABASE_URL
# postgresql+asyncpg://user:pass@host:5432/db?pool_size=20&max_overflow=10

# Check Redis cache hit rate
docker compose exec redis redis-cli -a veriunlearn_secret INFO stats | grep hit_rate

# Profile specific endpoints
# Use curl with timing
curl -w "\nTime: %{time_total}s\n" http://localhost:8000/health
```

### High memory usage

```bash
# Check per-service memory
docker stats

# Reduce Celery worker concurrency
# CELERY_WORKER_CONCURRENCY=2

# Limit Qdrant memory
# QDRANT_MEMORY_LIMIT=2GB

# Reduce ML Engine batch sizes
# Add to .env: ML_ENGINE_MAX_BATCH_SIZE=8
```

### Slow unlearning operations

```bash
# Choose faster algorithm for large deletions
# Certified Removal (~180ms) > Influence (~350ms) > Hybrid (~420ms) > SISA (~1250ms)

# Reduce dataset size for influence computation
# Increase shard count for SISA to improve parallelization

# Check Celery worker load
celery -A app.workers.celery_app inspect active
celery -A app.workers.celery_app inspect reserved

# Monitor task queue depth
docker compose exec redis redis-cli -a veriunlearn_secret LLEN celery
```

---

## Certificate Generation Issues

### Certificate signing fails

```bash
# Check APP_SECRET_KEY is set
grep APP_SECRET_KEY .env

# Verify Ed25519 key is valid (64-char hex for key pair)
python -c "
from nacl.signing import SigningKey
import os
key = os.environ.get('APP_SECRET_KEY', '').encode()
print('Valid' if len(key) >= 32 else 'Invalid key length')
"

# Check MinIO connectivity for certificate storage
curl http://localhost:9000/minio/health/live
```

### Proof verification fails

```bash
# Verify Merkle root hash matches stored value
# Re-verify via API
curl -X POST http://localhost:8000/api/v1/verify/proofs/verify \
  -H "Content-Type: application/json" \
  -d '{"proof_id": "<proof_id>"}'

# Check audit chain integrity
curl http://localhost:8000/api/v1/audit/chain/verify

# Ensure verification keys match (regenerate if rotated)
```

---

## Debug Mode Instructions

### Enable Debug Mode

```bash
# Set in .env
APP_DEBUG=true

# This enables:
# - Detailed error messages in API responses
# - SQL query logging (SQLAlchemy echo)
# - Request/response logging middleware
# - CORS (all origins allowed)
# - Additional metrics and tracing
```

### Log Levels

```bash
# Set log level in .env
LOG_LEVEL=DEBUG        # Most verbose (default: INFO)
# Options: DEBUG, INFO, WARNING, ERROR, CRITICAL

# For specific modules:
LOG_LEVEL_APP=DEBUG
LOG_LEVEL_CELERY=INFO
LOG_LEVEL_SQLALCHEMY=WARNING
```

### Debugging Celery Tasks

```bash
# Enable Celery task tracing
CELERY_TASK_ALWAYS_EAGER=true   # Run tasks synchronously
CELERY_TASK_EAGER_PROPAGATES=true  # Propagate exceptions

# Monitor Celery flower (web UI)
celery -A app.workers.celery_app flower --port=5555
# Access at: http://localhost:5555
```

---

## Log Locations and Analysis

### Log Locations

| Environment | Backend | ML Engine | Celery | Nginx |
|-------------|---------|-----------|--------|-------|
| Development | `logs/backend.log` | `logs/ml-engine.log` | `logs/celery.log` | `logs/nginx/` |
| Docker | `docker compose logs backend` | `docker compose logs ml-engine` | `docker compose logs celery` | `docker compose logs nginx` |
| Kubernetes | `kubectl logs deploy/backend` | `kubectl logs deploy/ml-engine` | `kubectl logs deploy/celery` | `kubectl logs deploy/nginx` |
| Production | Loki (aggregated) | Loki (aggregated) | Loki (aggregated) | Loki (aggregated) |

### Analyzing Logs

```bash
# Follow logs in real-time
docker compose logs -f backend

# Search for errors
docker compose logs backend | grep -i "error\|exception\|traceback"

# Filter by date range
docker compose logs --since "2026-07-27T10:00:00" --until "2026-07-27T12:00:00" backend

# Extract structured JSON fields
docker compose logs backend | python -c "import sys,json; [print(json.loads(l).get('event'), json.loads(l).get('duration_ms')) for l in sys.stdin if l.strip().startswith('{')]"
```

### Common Log Patterns

| Log Pattern | Meaning | Action |
|-------------|---------|--------|
| `connection refused` | Service not running | Start the service or check networking |
| `relation "..." does not exist` | Migration not applied | Run `alembic upgrade head` |
| `JWT expired` | Token expired | Re-authenticate or refresh token |
| `rate limit exceeded` | Too many requests | Wait or increase limit |
| `CUDA out of memory` | GPU memory full | Reduce batch size or quantization |
| `task ... retry #N` | Celery task retrying | Check worker logs for root cause |
| `hash mismatch` | Data integrity issue | Re-run verification or restore from backup |

---

## Getting Help

- **GitHub Issues**: Open a bug report at https://github.com/Sania-2520/VeriUnlearn/issues
- **Feature Requests**: Use the feature request template
- **Security**: Report privately to security@veriunlearn.com
- **Provide**: Logs, steps to reproduce, environment details (OS, Python version, Docker version)

When reporting an issue, include:
```
- VeriUnlearn version: v1.0.0
- Deployment method: Docker / Local / K8s
- OS: Windows 11 / Ubuntu 24.04 / macOS 15
- Python version: 3.13.x
- Docker version: 27.x
- Steps to reproduce:
- Expected behavior:
- Actual behavior:
- Relevant logs:
```

---

## Related Documents

- [FAQ](FAQ.md) — Frequently asked questions
- [Deployment Guide](deployment.md) — Environment configuration
- [Developer Guide](developer-guide.md) — Local setup and debugging
- [Benchmark Guide](BENCHMARK_GUIDE.md) — Evaluation framework issues
