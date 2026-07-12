# Deployment Guide

## Prerequisites

- Docker & Docker Compose v2
- NVIDIA GPU with CUDA 12+ (optional, for GPU inference)
- 16 GB+ RAM (32 GB recommended for ML workloads)

## Quick Start

```bash
# 1. Clone and set up secrets
cp .env.example .env
# Edit .env: replace JWT_SECRET_KEY and APP_SECRET_KEY

# 2. Start all services
docker compose up -d

# 3. Apply database migrations
docker compose exec backend alembic upgrade head

# 4. Verify health
curl http://localhost:8000/health
```

Services:
| Service  | Port | URL                     |
|----------|------|-------------------------|
| Frontend | 80   | http://localhost         |
| API      | 8000 | http://localhost:8000    |
| Docs     | 8000 | http://localhost:8000/api/docs |
| Metrics  | 8000 | http://localhost:8000/metrics  |

## Environment Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `JWT_SECRET_KEY` | — | 64-char random key for token signing |
| `APP_SECRET_KEY` | — | 32-char random key for app-level crypto |
| `JWT_ALGORITHM` | `HS256` | Signing algorithm |
| `JWT_ACCESS_TOKEN_EXPIRE_MINUTES` | `30` | Access token TTL |
| `JWT_REFRESH_TOKEN_EXPIRE_DAYS` | `7` | Refresh token TTL |

| Variable | Default | Description |
|----------|---------|-------------|
| `POSTGRES_*` | `veriunlearn` | Database credentials |
| `REDIS_HOST` | `redis` | Celery broker (port 6379) |
| `QDRANT_HOST` | `qdrant` | Vector store (port 6333) |
| `MINIO_*` | `veriunlearn` | Object storage (port 9000) |

| Variable | Default | Description |
|----------|---------|-------------|
| `BASE_MODEL_NAME` | `Qwen/Qwen2.5-1.5B-Instruct` | HuggingFace model ID |
| `DEVICE` | `cuda` | `cuda` or `cpu` |
| `QUANTIZATION_BITS` | `4` | Bits for 4-bit quantized loading |
| `LORA_R` | `16` | LoRA rank |
| `LORA_ALPHA` | `32` | LoRA alpha |
| `LORA_DROPOUT` | `0.1` | LoRA dropout rate |

## Local Development (no Docker)

```bash
# Infrastructure (PostgreSQL, Redis, Qdrant, MinIO)
docker compose up -d postgres redis qdrant minio

# Backend
make dev-backend  # uvicorn on :8000

# Frontend (separate terminal)
make dev-frontend # Next.js on :3000

# Celery worker (separate terminal)
make worker

# Run migrations
make db-migrate
```

All 9 unit tests pass in ~18s:
```bash
make test
```

## Production Considerations

1. **Secrets**: Generate with `openssl rand -hex 32` for each deployment.
2. **PostgreSQL**: Use managed RDS/Cloud SQL instead of container.
3. **Redis**: Use ElastiCache / Memorystore for production.
4. **Qdrant**: Use Qdrant Cloud or dedicated instance with persistent volume.
5. **MinIO**: Replace with S3-compatible storage (AWS S3, GCS).
6. **Nginx**: Configure TLS termination and rate limiting.
7. **Scaling**: Run multiple backend replicas behind nginx; Celery workers scale independently.
8. **GPU**: Set `DEVICE=cuda` and deploy on GPU instances for real inference.
9. **Monitoring**: Prometheus metrics at `/metrics`; Grafana dashboards recommended.
10. **Backup**: Schedule `pg_dump` for PostgreSQL; snapshot Qdrant volumes.
