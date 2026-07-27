# VeriUnlearn — Deployment Guide

## 1. Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                         Internet                             │
└──────────────────┬──────────────────────────────────────────┘
                   │ :80 / :443
┌──────────────────▼──────────────────────────────────────────┐
│                          nginx                              │
│               Reverse Proxy / TLS Termination                │
│              /api/ → backend :8000                           │
│              /ml/  → ml-engine :8001                         │
│                /   → frontend :3000                          │
└──────┬─────────────────────┬───────────────────┬────────────┘
       │                     │                   │
┌──────▼──────┐    ┌────────▼───────┐   ┌───────▼─────────┐
│   Frontend  │    │    Backend     │   │   ML Engine     │
│  Next.js    │    │  FastAPI       │   │  PyTorch/HF     │
│  :3000      │    │  :8000         │   │  :8001          │
└─────────────┘    └───┬────────┬───┘   └───┬─────────────┘
                       │        │            │
        ┌──────────────┼────────┼────────────┼──────────────┐
        │              │        │            │              │
┌───────▼────┐  ┌─────▼────┐ ┌─▼──────┐ ┌───▼────────┐ ┌──▼────────┐
│ PostgreSQL │  │  Redis   │ │ Qdrant │ │   MinIO    │ │  RabbitMQ │
│  :5432     │  │  :6379   │ │ :6333  │ │   :9000    │ │  :5672    │
│  Metadata  │  │  Broker  │ │Vector  │ │  Object    │ │  Optional │
│            │  │  Cache   │ │Store   │ │  Storage   │ │  Queue    │
└────────────┘  └──────────┘ └────────┘ └────────────┘ └───────────┘
```

### Monitoring Stack (opt-in profile)

```
┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────────┐
│Prometheus│◄───│  Loki    │◄───│ Grafana  │◄───│ Alertmanager │
│ :9090    │    │  :3100   │    │  :3001   │    │  :9093       │
└──────────┘    └──────────┘    └──────────┘    └──────────────┘
     │                              ▲
     └──────────────────────────────┘
```

### Service Dependencies

| Service | Depends On | Health Check | Start Period |
|---------|-----------|-------------|--------------|
| postgres | — | `pg_isready` | 10s |
| redis | — | `redis-cli ping` | 5s |
| qdrant | — | `curl /healthz` | 10s |
| minio | — | `curl /minio/health/live` | 10s |
| backend | postgres, redis, qdrant, minio | `curl /health` | 30s |
| worker | postgres, redis, backend | `celery inspect ping` | 30s |
| ml-engine | qdrant, minio | `curl /health` | 60s |
| frontend | backend | `wget localhost:3000` | 40s |
| nginx | backend, frontend | `curl localhost:80` | 10s |

---

## 2. Prerequisites

### Minimum Requirements

| Resource | Development | Production |
|----------|-------------|------------|
| CPU | 4 cores | 8+ cores |
| RAM | 16 GB | 32 GB+ |
| Disk | 50 GB SSD | 200 GB+ SSD (gp3) |
| Docker | 24+ | 24+ |
| Docker Compose | v2.20+ | v2.20+ |
| GPU | — | NVIDIA + CUDA 12.4+ (optional) |
| OS | Linux/macOS/Windows | Linux (Ubuntu 22.04+, RHEL 9+) |

### Software

- **Docker Engine** ≥ 24.0
- **Docker Compose** ≥ v2.20 (or plugin)
- **Git** ≥ 2.30
- **Make** (optional, for convenience targets)
- **Python** 3.11+ (for local development without Docker)
- **Node.js** 20+ (for local frontend development)
- **NVIDIA Container Toolkit** (for GPU acceleration)
- **Helm** 3.14+ (for Kubernetes deployment)
- **kubectl** 1.29+ (for Kubernetes deployment)
- **Terraform** 1.5+ (for infrastructure provisioning)

### Network Ports

| Port | Service | Required |
|------|---------|----------|
| 80 | HTTP (nginx) | Yes |
| 443 | HTTPS (nginx) | Yes |
| 5432 | PostgreSQL | Internal |
| 6379 | Redis | Internal |
| 6333 | Qdrant | Internal |
| 9000 | MinIO API | Internal |
| 9001 | MinIO Console | Internal |
| 8000 | Backend API | Yes |
| 8001 | ML Engine | Yes |
| 3000 | Frontend | Yes |
| 9090 | Prometheus | Optional |
| 3001 | Grafana | Optional |
| 3100 | Loki | Optional |
| 9093 | Alertmanager | Optional |

---

## 3. Docker Compose Deployment

### Quick Start

```bash
# 1. Clone the repository
git clone https://github.com/veriunlearn/veriunlearn.git
cd veriunlearn

# 2. Create environment file
cp .env.example .env
# ⚠️ IMPORTANT: Edit .env — generate secure secrets (see Section 7)

# 3. Start all services
docker compose up -d

# 4. Run database migrations
docker compose exec backend alembic upgrade head

# 5. Verify health
docker compose ps
curl http://localhost:8000/health
```

### With Monitoring Stack

```bash
docker compose --profile monitoring up -d
```

This starts Prometheus (`:9090`), Grafana (`:3001`), Loki (`:3100`), and Alertmanager (`:9093`).

### First-Time Seed

```bash
# Seed demo data (datasets, models, sample requests)
docker compose exec backend python scripts/seed_demo_data.py

# Or use the setup script
./scripts/setup.sh --seed
```

### Common Operations

```bash
# View logs
docker compose logs -f backend
docker compose logs -f ml-engine
docker compose logs -f worker

# Scale workers
docker compose up -d --scale worker=4

# Restart a service
docker compose restart ml-engine

# Rebuild and restart
docker compose build backend
docker compose up -d --force-recreate backend

# Stop with monitoring
docker compose --profile monitoring down

# Full cleanup (destroys volumes)
docker compose down -v
```

---

## 4. Production Deployment (Helm / Kubernetes)

### Prerequisites

- Kubernetes 1.29+ cluster (EKS, AKS, GKE, or self-managed)
- Helm 3.14+
- NVIDIA GPU Operator (for GPU nodes)
- cert-manager (for TLS certificates)
- Ingress Controller (nginx-ingress or AWS ALB)

### Helm Chart Structure

```
infra/kubernetes/helm/veriunlearn/
├── Chart.yaml
├── values/
│   ├── development.yaml
│   ├── staging.yaml
│   └── production.yaml
├── templates/
│   ├── _helpers.tpl
│   ├── backend.yaml
│   ├── frontend.yaml
│   ├── ml-engine.yaml
│   ├── worker.yaml
│   ├── postgres.yaml
│   ├── redis.yaml
│   ├── qdrant.yaml
│   ├── minio.yaml
│   ├── ingress.yaml
│   ├── configmap.yaml
│   ├── secrets.yaml
│   ├── serviceaccount.yaml
│   ├── hpa.yaml
│   ├── pdb.yaml
│   ├── network-policy.yaml
│   └── monitoring/
│       ├── prometheus.yaml
│       ├── grafana.yaml
│       └── loki.yaml
```

### Installation

```bash
# Add Helm repository
helm repo add veriunlearn https://helm.veriunlearn.ai

# Install with production values
helm upgrade --install veriunlearn veriunlearn/veriunlearn \
  --namespace veriunlearn --create-namespace \
  --values values/production.yaml \
  --set image.tag=<RELEASE_TAG> \
  --set secrets.jwtSecret=$(openssl rand -hex 32) \
  --set secrets.appSecretKey=$(openssl rand -hex 32) \
  --set secrets.mlEngineApiKey=$(openssl rand -hex 32) \
  --set secrets.redisPassword=$(openssl rand -hex 32) \
  --set secrets.postgresPassword=$(openssl rand -hex 32)

# Verify deployment
kubectl -n veriunlearn get pods
kubectl -n veriunlearn rollout status deployment/veriunlearn-backend
```

### Horizontal Pod Autoscaling

```yaml
backend:
  autoscaling:
    enabled: true
    minReplicas: 2
    maxReplicas: 10
    targetCPUUtilizationPercentage: 70
    targetMemoryUtilizationPercentage: 80

worker:
  autoscaling:
    enabled: true
    minReplicas: 2
    maxReplicas: 20
    targetCPUUtilizationPercentage: 75

ml-engine:
  autoscaling:
    enabled: true
    minReplicas: 1
    maxReplicas: 5
    targetGPUUtilizationPercentage: 80
```

### Pod Disruption Budgets

```yaml
backend:
  pdb:
    minAvailable: 1

worker:
  pdb:
    minAvailable: 1

ml-engine:
  pdb:
    minAvailable: 0  # stateless, can restart
```

---

## 5. Terraform Provisioning

### AWS EKS Module

VeriUnlearn includes a Terraform module for provisioning a production-grade EKS cluster.

### Production Environment

```hcl
# infra/terraform/environments/production/main.tf
module "eks" {
  source = "../../modules/eks"

  project_name = "veriunlearn"
  environment  = "production"

  cluster_version                = "1.29"
  vpc_cidr                       = "10.0.0.0/16"
  cluster_endpoint_public_access = false  # private access only

  standard_instance_types = ["m6i.xlarge", "m6i.2xlarge"]
  standard_min_size = 2
  standard_max_size = 10
  standard_desired_size = 3

  gpu_instance_types = ["p3.2xlarge", "p3.8xlarge"]
  gpu_min_size = 1
  gpu_max_size = 5
  gpu_desired_size = 2
}
```

### Provisioning Steps

```bash
cd infra/terraform/environments/production

# Initialize backend (S3 + DynamoDB)
terraform init

# Preview changes
terraform plan

# Apply
terraform apply -auto-approve

# Configure kubectl
aws eks update-kubeconfig --name veriunlearn-production --region us-east-1
```

### Terraform State

State is stored in S3 with DynamoDB locking:

```hcl
backend "s3" {
  bucket         = "veriunlearn-terraform-state"
  key            = "production/eks/terraform.tfstate"
  region         = "us-east-1"
  dynamodb_table = "veriunlearn-terraform-locks"
  encrypt        = true
}
```

---

## 6. Configuration Reference

### Docker Compose Configuration

#### x-backend-env (anchor)

Shared environment variables injected into `backend` and `worker` services:

| Variable | Source | Purpose |
|----------|--------|---------|
| `APP_ENV` | `.env` / `production` | Environment name |
| `DATABASE_URL` | Computed | AsyncPG connection string |
| `REDIS_URL` | Computed | Redis connection (db 0) |
| `CELERY_BROKER_URL` | Computed | Redis as broker (db 1) |
| `CELERY_RESULT_BACKEND` | Computed | Redis as result backend (db 2) |
| `ML_ENGINE_URL` | Computed | ML Engine internal endpoint |
| `QDRANT_URL` | Computed | Qdrant internal endpoint |
| `MINIO_ENDPOINT` | Computed | MinIO internal endpoint |
| `MINIO_ROOT_USER` | `.env` | MinIO access key |
| `MINIO_ROOT_PASSWORD` | `.env` | MinIO secret key |
| `JWT_SECRET_KEY` | `.env` | Token signing key |
| `APP_SECRET_KEY` | `.env` | Application encryption key |
| `CORS_ORIGINS` | `.env` | Allowed CORS origins |
| `OTEL_EXPORTER_OTLP_ENDPOINT` | `.env` | OpenTelemetry collector |
| `PROMETHEUS_ENABLED` | `.env` | Enable metrics endpoint |
| `LOG_FORMAT` | `.env` | Log output format |

### Helm Values Reference

```yaml
# Key configuration parameters
image:
  registry: ghcr.io/veriunlearn
  tag: latest
  pullPolicy: Always

backend:
  replicas: 2
  resources:
    limits:
      cpu: "2.0"
      memory: 2Gi
  autoscaling:
    enabled: true
    minReplicas: 2
    maxReplicas: 10

worker:
  replicas: 2
  concurrency: 4
  resources:
    limits:
      cpu: "2.0"
      memory: 2Gi
  autoscaling:
    enabled: true

ml-engine:
  replicas: 1
  device: cuda
  quantizationBits: 4
  resources:
    limits:
      cpu: "4.0"
      memory: 16Gi
      nvidia.com/gpu: 1

postgresql:
  enabled: true  # set false for external managed DB
  persistence:
    size: 100Gi
    storageClass: gp3

redis:
  enabled: true  # set false for external managed Redis
  persistence:
    size: 10Gi

qdrant:
  persistence:
    size: 50Gi

minio:
  persistence:
    size: 100Gi
  buckets:
    - models
    - checkpoints
    - certificates

ingress:
  enabled: true
  host: api.veriunlearn.com
  tls: true
  annotations:
    cert-manager.io/cluster-issuer: letsencrypt-prod
```

---

## 7. Environment Variables (All 91)

### Database (7)

| Variable | Default | Description |
|----------|---------|-------------|
| `POSTGRES_USER` | `veriunlearn` | Database user |
| `POSTGRES_PASSWORD` | `veriunlearn_secret` | Database password |
| `POSTGRES_DB` | `veriunlearn` | Database name |
| `POSTGRES_HOST` | `localhost` | Database host |
| `POSTGRES_PORT` | `5432` | Database port |
| `DATABASE_URL` | *(computed)* | Full asyncpg connection string |

### Redis (5)

| Variable | Default | Description |
|----------|---------|-------------|
| `REDIS_HOST` | `localhost` | Redis host |
| `REDIS_PORT` | `6379` | Redis port |
| `REDIS_PASSWORD` | `veriunlearn_secret` | Redis password |
| `REDIS_URL` | *(computed)* | Redis connection string |

### Qdrant (3)

| Variable | Default | Description |
|----------|---------|-------------|
| `QDRANT_HOST` | `localhost` | Qdrant host |
| `QDRANT_PORT` | `6333` | Qdrant port |
| `QDRANT_URL` | *(computed)* | Qdrant HTTP URL |

### MinIO (6)

| Variable | Default | Description |
|----------|---------|-------------|
| `MINIO_ROOT_USER` | `veriunlearn` | Access key |
| `MINIO_ROOT_PASSWORD` | `veriunlearn_secret` | Secret key |
| `MINIO_HOST` | `localhost` | Host |
| `MINIO_PORT` | `9000` | API port |
| `MINIO_BUCKET` | `models` | Default bucket |
| `MINIO_ENDPOINT` | *(computed)* | Endpoint for client |

### JWT (6)

| Variable | Default | Description |
|----------|---------|-------------|
| `JWT_SECRET_KEY` | `dev-jwt-secret-key-at-least-32-chars-long!!` | Signing key (min 256-bit) |
| `JWT_ALGORITHM` | `HS256` | Signing algorithm |
| `JWT_ACCESS_TOKEN_EXPIRE_MINUTES` | `30` | Access token TTL |
| `JWT_REFRESH_TOKEN_EXPIRE_DAYS` | `7` | Refresh token TTL |
| `JWT_ISSUER` | `veriunlearn` | Token issuer |
| `JWT_AUDIENCE` | `veriunlearn-api` | Token audience |

### ML Engine (8)

| Variable | Default | Description |
|----------|---------|-------------|
| `ML_ENGINE_URL` | `http://localhost:8001` | ML Engine endpoint |
| `ML_ENGINE_API_KEY` | *(empty)* | API key for ML Engine |
| `BASE_MODEL_NAME` | `Qwen/Qwen2.5-1.5B-Instruct` | HuggingFace model |
| `ML_DEVICE` | `cpu` | Device for ML Engine |
| `DEVICE` | `cpu` | Device for inference |
| `QUANTIZATION_BITS` | `4` | Quantization bits |
| `LORA_R` | `16` | LoRA rank |
| `LORA_ALPHA` | `32` | LoRA alpha |
| `LORA_DROPOUT` | `0.1` | LoRA dropout rate |

### Celery (3)

| Variable | Default | Description |
|----------|---------|-------------|
| `CELERY_BROKER_URL` | *(computed)* | Redis broker URL |
| `CELERY_RESULT_BACKEND` | *(computed)* | Redis result backend |
| `CELERY_WORKER_CONCURRENCY` | `4` | Worker concurrency |

### OpenTelemetry (2)

| Variable | Default | Description |
|----------|---------|-------------|
| `OTEL_SERVICE_NAME` | `veriunlearn` | Service name |
| `OTEL_EXPORTER_OTLP_ENDPOINT` | `http://localhost:4317` | OTLP endpoint |

### App (5)

| Variable | Default | Description |
|----------|---------|-------------|
| `APP_ENV` | `development` | Application environment |
| `APP_DEBUG` | `true` | Debug mode |
| `APP_SECRET_KEY` | `dev-app-secret-key-at-least-32-chars-long!!!` | App encryption key |
| `DOMAIN` | `localhost:3000` | Allowed domain |
| `ALLOWED_HOSTS` | *(empty)* | Extra allowed hosts |

### Services (8)

| Variable | Default | Description |
|----------|---------|-------------|
| `BACKEND_PORT` | `8000` | Backend host port |
| `ML_ENGINE_PORT` | `8001` | ML Engine host port |
| `FRONTEND_PORT` | `3000` | Frontend host port |
| `HTTP_PORT` | `80` | HTTP port |
| `HTTPS_PORT` | `443` | HTTPS port |
| `PROMETHEUS_PORT` | `9090` | Prometheus host port |
| `ALERTMANAGER_PORT` | `9093` | Alertmanager host port |
| `GRAFANA_PORT` | `3001` | Grafana host port |
| `LOKI_PORT` | `3100` | Loki host port |

### Frontend (1)

| Variable | Default | Description |
|----------|---------|-------------|
| `NEXT_PUBLIC_API_URL` | `http://localhost:8000/api/v1` | Public API URL |

### OAuth / SSO (4)

| Variable | Default | Description |
|----------|---------|-------------|
| `GOOGLE_CLIENT_ID` | *(empty)* | Google OAuth client ID |
| `GOOGLE_CLIENT_SECRET` | *(empty)* | Google OAuth client secret |
| `GITHUB_CLIENT_ID` | *(empty)* | GitHub OAuth client ID |
| `GITHUB_CLIENT_SECRET` | *(empty)* | GitHub OAuth client secret |

### AI Providers (3)

| Variable | Default | Description |
|----------|---------|-------------|
| `OPENAI_API_KEY` | *(empty)* | OpenAI API key |
| `ANTHROPIC_API_KEY` | *(empty)* | Anthropic API key |
| `HUGGINGFACE_API_TOKEN` | *(empty)* | HuggingFace API token |

### Security / Compliance (3)

| Variable | Default | Description |
|----------|---------|-------------|
| `COMPLIANCE_GDPR_CONTACT` | *(empty)* | GDPR contact email |
| `COMPLIANCE_AI_ACT_CONTACT` | *(empty)* | EU AI Act contact |
| `SENTRY_DSN` | *(empty)* | Sentry error tracking DSN |

---

## 8. Health Checks

### Endpoint Summary

| Service | Endpoint | Method | Expected |
|---------|----------|--------|----------|
| Backend | `/health` | GET | `200 OK` |
| ML Engine | `/health` | GET | `200 OK` |
| Frontend | `/` | GET | `200 OK` |
| nginx | `/health` | GET | `200 OK` |
| PostgreSQL | `pg_isready` | Shell | Exit 0 |
| Redis | `redis-cli ping` | Shell | `PONG` |
| Qdrant | `/healthz` | GET | `200 OK` |
| MinIO | `/minio/health/live` | GET | `200 OK` |
| Celery | `celery inspect ping` | Shell | OK response |

### Health Check Script

```bash
./scripts/healthcheck.sh
```

### Docker Health Check Configuration

All services include Docker health checks with configurable intervals, timeouts, retries, and start periods. See `docker-compose.yml` for per-service configuration.

---

## 9. Monitoring Setup

### Prometheus

Configuration at `infra/monitoring/prometheus/prometheus.yml`:

- **Global scrape interval:** 15s
- **Evaluation interval:** 15s
- **Scrape timeout:** 10s
- **Retention:** 30 days
- **Alerting:** Alertmanager at `alertmanager:9093`

**Scrape targets:**

| Job | Endpoint | Port |
|-----|----------|------|
| Backend | `/metrics` | 8000 |
| ML Engine | `/metrics` | 8000 |
| Qdrant | `/metrics` | 6333 |
| RabbitMQ | `/metrics` | 15692 |
| MLflow | `/metrics` | 5000 |
| Node Exporter | `/metrics` | 9100 |
| PostgreSQL Exporter | `/metrics` | 9187 |
| Redis Exporter | `/metrics` | 9121 |
| NVIDIA GPU Exporter | `/metrics` | 9445 |

### Grafana

**Access:** `http://localhost:3001` (default: `admin` / `admin`)
**Pre-provisioned datasources:**

| Name | Type | URL |
|------|------|-----|
| Prometheus | prometheus | `http://prometheus:9090` |
| Loki | loki | `http://loki:3100` |
| Tempo | tempo | `http://tempo:3200` |
| PostgreSQL | postgres | `postgres:5432` |

**Pre-provisioned dashboards** (at `infra/monitoring/grafana/dashboards/`):
- VeriUnlearn Overview
- Service Health
- ML Engine Performance
- Celery Queue Monitoring
- GPU Utilization

### Loki

**Configuration:** `infra/monitoring/loki/loki.yml`
- Filesystem storage at `/loki/chunks` and `/loki/rules`
- Schema v11 with `boltdb-shipper`
- No authentication (internal network)

---

## 10. Logging (Loki)

### Log Collection

Logs are collected via the Docker Compose logging driver and shipped to Loki. The Grafana agent or Promtail (not yet configured) should be set up for production deployments.

### Log Format

All services output JSON-structured logs for easy parsing:

```json
{"level":"INFO","timestamp":"2026-07-27T12:00:00Z","service":"backend","request_id":"del-req-abc123","message":"Unlearning job started"}
```

### Log Query Examples (LokiQL)

```logql
# All errors in the last hour
{service="backend"} |= "ERROR" |= "5m"

# Unlearning jobs by request ID
{service="worker"} |= "del-req-bfe74a1b98f3"

# Request latency > 2s
{service="backend"} | json | duration > 2

# Error rate by endpoint
rate({service="backend"} |= "status=5" [5m])
```

---

## 11. Alerting (Alertmanager)

### Configuration

Configuration at `infra/monitoring/alertmanager/alertmanager.yml`.

### Routing

| Severity | Receiver | Channel |
|----------|----------|---------|
| Critical | PagerDuty | On-call escalation |
| Warning | Slack | `#veriunlearn-warnings` |
| Compliance | Slack | `#veriunlearn-compliance` |
| Default | Slack | `#veriunlearn-alerts` |

### Alert Rules

Defined in `infra/monitoring/prometheus/alerts.yml`. Key alerts:

| Alert | Condition | Severity | Response |
|-------|-----------|----------|----------|
| `HighErrorRate` | 5xx rate > 1% for 5m | Critical | Check backend logs |
| `HighLatency` | p99 > 2s for 5m | Critical | Scale backends, check DB |
| `ServiceDown` | `up == 0` for 1m | Critical | Investigate container/k8s |
| `DiskSpaceLow` | Disk < 20% for 5m | Critical | Clean up or expand volume |
| `UnlearningQueueGrowing` | Queue > 100 for 10m | Warning | Scale workers |
| `DeletionQueueGrowing` | Queue > 50 for 10m | Warning | Scale workers, check ML Engine |
| `CertificateExpiring` | Expiry < 30 days | Warning | Renew certificate |
| `GPUMemoryHigh` | GPU > 90% for 5m | Critical | Scale GPU nodes |
| `TrainingJobFailed` | Status == "failed" | Critical | Investigate ML Engine |
| `DatabaseConnectionsHigh` | Connections > 100 | Warning | Check connection pooling |

### Setup

```bash
# Alertmanager requires webhook URLs
export SLACK_WEBHOOK_URL="https://hooks.slack.com/services/..."
export PAGERDUTY_ROUTING_KEY="..."

# Update infra/monitoring/alertmanager/alertmanager.yml with actual URLs
# Restart to apply
docker compose --profile monitoring up -d alertmanager
```

---

## 12. Backup and Restore

### PostgreSQL

```bash
# Backup
docker compose exec -T postgres pg_dump -U veriunlearn veriunlearn > backup_$(date +%Y%m%d_%H%M%S).sql

# Restore
cat backup.sql | docker compose exec -T postgres psql -U veriunlearn veriunlearn

# Automated backup (cron)
0 2 * * * cd /opt/veriunlearn && docker compose exec -T postgres pg_dump -U veriunlearn veriunlearn | gzip > backups/postgres/daily_$(date +\%Y\%m\%d).sql.gz
```

### MinIO

```bash
# Backup using mc client
docker compose exec minio mc alias local http://localhost:9000 $MINIO_ROOT_USER $MINIO_ROOT_PASSWORD
docker compose exec minio mc mirror local/models backups/minio/models/

# Restore
docker compose exec minio mc mirror backups/minio/models/ local/models/
```

### Qdrant

```bash
# Snapshot via API
curl -X POST 'http://localhost:6333/collections/veriunlearn/snapshots'

# Copy snapshot
docker cp $(docker compose ps -q qdrant):/qdrant/storage/snapshots/veriunlearn/ .
```

### Redis

```bash
# BGSAVE (persists RDB to /data)
docker compose exec redis redis-cli -a $REDIS_PASSWORD BGSAVE

# Copy RDB file
docker cp $(docker compose ps -q redis):/data/dump.rdb ./redis-backup.rdb
```

---

## 13. Disaster Recovery

### Recovery Time Objectives

| Service | RTO | RPO |
|---------|-----|-----|
| PostgreSQL | 1 hour | 5 minutes |
| MinIO | 2 hours | 1 hour |
| Qdrant | 2 hours | 1 hour |
| Redis | 30 minutes | 5 minutes |
| Application | 30 minutes | — |

### Recovery Procedures

#### Full Stack Recovery

```bash
# 1. Restore infrastructure
terraform apply

# 2. Deploy application
helm upgrade --install veriunlearn ./infra/kubernetes/helm/veriunlearn \
  --namespace veriunlearn --create-namespace

# 3. Restore databases
gunzip -c latest_postgres_backup.sql.gz | kubectl exec -i deploy/postgres -- psql -U veriunlearn

# 4. Restore object storage
docker compose exec minio mc mirror backup/minio/ local/

# 5. Restore vector store
curl -X POST -F "snapshot=@qdrant_snapshot.snapshot" 'http://localhost:6333/collections/veriunlearn/snapshots/upload'
curl -X PUT 'http://localhost:6333/collections/veriunlearn/snapshots/recover' \
  -H 'Content-Type: application/json' \
  -d '{"location": "file:///qdrant/storage/snapshots/veriunlearn/snapshot.snapshot"}'

# 6. Verify health
./scripts/healthcheck.sh
```

#### Quick Recovery (Docker Compose)

```bash
# Restart failed service
docker compose up -d --force-recreate <service>

# Rebuild and restart
docker compose build <service>
docker compose up -d --force-recreate <service>

# Full stack restart
docker compose down && docker compose up -d
```

---

## 14. Scaling Guidelines

### Vertical Scaling

| Service | Dev (CPU/Mem) | Production (CPU/Mem) | GPU |
|---------|--------------|----------------------|-----|
| backend | 1 core / 1 GB | 2 cores / 2 GB | — |
| worker | 1 core / 1 GB | 2 cores / 4 GB | — |
| ml-engine | 2 cores / 4 GB | 8 cores / 32 GB | 1× NVIDIA A10G+ |
| postgres | 1 core / 1 GB | 4 cores / 8 GB | — |
| redis | 0.5 core / 512 MB | 2 cores / 4 GB | — |
| qdrant | 1 core / 1 GB | 4 cores / 8 GB | — |
| minio | 1 core / 1 GB | 4 cores / 8 GB | — |
| frontend | 0.5 core / 512 MB | 1 core / 1 GB | — |

### Horizontal Scaling

- **Backend:** Scale behind nginx (round-robin). Stateless — can scale to 10+ replicas.
- **Workers:** Scale independently. Each worker processes one job at a time. `CONCURRENCY` controls sub-processes per worker.
- **ML Engine:** Scale for parallel unlearning jobs. GPU-backed instances are typically limited by GPU count.
- **PostgreSQL:** Use connection pooling (PgBouncer) for high concurrency. Consider read replicas.
- **Qdrant:** Supports multi-node clustering for horizontal scaling.

### Capacity Planning

```
requests_per_second = R
avg_processing_time = T seconds
workers_needed = R × T × safety_factor (1.5)

Example: R=10 req/s, T=30s → 10 × 30 × 1.5 = 450 workers (unlikely)
Most deployments: 4–16 workers sufficient.
```

---

## 15. Security Hardening

### Secret Management

1. **Generate strong secrets:**
   ```bash
   openssl rand -hex 32  # JWT_SECRET_KEY, APP_SECRET_KEY, ML_ENGINE_API_KEY
   openssl rand -hex 32  # POSTGRES_PASSWORD, REDIS_PASSWORD, MINIO_ROOT_PASSWORD
   openssl rand -hex 16  # GRAFANA_ADMIN_PASSWORD
   ```

2. **Never commit `.env` to version control.** It is in `.gitignore`.

3. **Helm deployments:** Use Sealed Secrets, External Secrets Operator, or Vault.

4. **Rotate secrets quarterly** and after any security incident.

### Container Security

- **Non-root users:** All containers run as non-root (USER directive in Dockerfiles).
- **Read-only filesystem:** Use `read_only: true` where possible.
- **No privilege escalation:** `security_opt: [no-new-privileges:true]`.
- **Capability drops:** `cap_drop: [ALL]` and add only required capabilities.
- **Image scanning:** Scan with Trivy or Snyk in CI/CD.

### Network Security

- **Internal network:** All services communicate over the internal `veriunlearn-network` bridge.
- **Ingress only through nginx:** No direct exposure of internal services.
- **Metrics restriction:** `/metrics` endpoint restricted to internal IP ranges (10.0.0.0/8, 172.16.0.0/12, 192.168.0.0/16).
- **Rate limiting:** Auth endpoints rate-limited at 5 req/s (nginx).

### Kubernetes Security

- **Network policies:** Restrict pod-to-pod communication.
- **Pod security standards:** Enforce `restricted` profile.
- **Service accounts:** Dedicated service account per component.
- **Secrets:** Encrypted at rest (KMS), never in environment variables in manifests.

### Compliance

- **Audit logging:** All mutation operations logged to immutable audit hash chain.
- **Certificate management:** Deletion certificates signed with Ed25519.
- **Retention policies:** Certificates valid for 1 year; audit logs retained for 7 years.

---

## 16. TLS/SSL Configuration

### Docker Compose (nginx)

The nginx configuration at `nginx/default.conf` includes security headers:

```
Strict-Transport-Security: max-age=31536000; includeSubDomains
X-Content-Type-Options: nosniff
X-Frame-Options: DENY
X-XSS-Protection: 1; mode=block
Referrer-Policy: strict-origin-when-cross-origin
Permissions-Policy: camera=(), microphone=(), geolocation=()
```

**Production TLS setup:**

```bash
# Generate Let's Encrypt certificate (manual)
docker compose run --rm certbot certonly --webroot \
  -w /var/www/certbot -d api.veriunlearn.com

# Or use Traefik (infra/docker/docker-compose.yml for dev)
# Traefik automatically handles Let's Encrypt ACME challenges
```

### Kubernetes (cert-manager)

```yaml
apiVersion: cert-manager.io/v1
kind: ClusterIssuer
metadata:
  name: letsencrypt-prod
spec:
  acme:
    server: https://acme-v02.api.letsencrypt.org/directory
    email: admin@veriunlearn.com
    privateKeySecretRef:
      name: letsencrypt-prod
    solvers:
      - http01:
          ingress:
            class: nginx
```

### Ingress TLS

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: veriunlearn-ingress
  annotations:
    cert-manager.io/cluster-issuer: letsencrypt-prod
spec:
  ingressClassName: nginx
  tls:
    - hosts:
        - api.veriunlearn.com
      secretName: veriunlearn-tls
  rules:
    - host: api.veriunlearn.com
      http:
        paths:
          - path: /api
            pathType: Prefix
            backend:
              service:
                name: backend
                port:
                  number: 8000
          - path: /
            pathType: Prefix
            backend:
              service:
                name: frontend
                port:
                  number: 3000
```

---

*See also: [DEPLOYMENT_CHECKLIST.md](DEPLOYMENT_CHECKLIST.md), [MONITORING_GUIDE.md](MONITORING_GUIDE.md), [DEMO_PACKAGE.md](DEMO_PACKAGE.md), [deployment.md](deployment.md), `docker-compose.yml`.*
