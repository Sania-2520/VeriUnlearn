# Production Deployment Guide — VeriUnlearn

## Prerequisites

- Docker 24+ and Docker Compose v2.20+
- NVIDIA GPU with CUDA 12.4+ (for ML Engine)
- NVIDIA Container Toolkit (`nvidia-ctk`)
- Domain with DNS pointing to the deployment host
- S3-compatible storage (MinIO, AWS S3, or GCS)
- Slack webhook URL for alertmanager notifications (optional)
- PagerDuty routing key (optional, for critical alerts)

---

## 1. Environment Configuration

Copy the example env file and fill in all secrets:

```bash
cp .env.example .env
```

Required overrides for production:

| Variable | Description |
|---|---|
| `JWT_SECRET_KEY` | 256-bit random key (`openssl rand -hex 32`) |
| `APP_SECRET_KEY` | 256-bit random key (`openssl rand -hex 32`) |
| `POSTGRES_PASSWORD` | Strong DB password (20+ chars) |
| `MINIO_ROOT_PASSWORD` | Strong MinIO password (20+ chars) |
| `REDIS_PASSWORD` | Redis AUTH password |
| `GRAFANA_ADMIN_PASSWORD` | Grafana admin password |

---

## 2. Deploy with Docker Compose

```bash
# Build and start all services
docker compose build
docker compose up -d

# Verify health
docker compose ps
curl http://localhost:8000/health
curl http://localhost:8001/health
```

### Service endpoints

| Service | Port |
|---|---|
| Backend API | `8000` |
| ML Engine | `8001` |
| Frontend | `3000` |
| Grafana | `3001` |
| Prometheus | `9090` |
| Alertmanager | `9093` |
| Loki | `3100` |

---

## 3. Kubernetes Deployment (EKS)

The Helm chart is at `infra/k8s/helm/`.

```bash
helm upgrade --install veriunlearn infra/k8s/helm/veriunlearn \
  --namespace veriunlearn --create-namespace \
  --set image.tag=latest \
  --set secrets.jwtSecret=$(openssl rand -hex 32)
```

For Terraform-managed EKS clusters:

```bash
cd infra/terraform/aws
terraform init
terraform plan -var="environment=production"
terraform apply -var="environment=production"
```

---

## 4. Monitoring & Alerting

### Prometheus
- Pre-configured scrape targets at `infra/monitoring/prometheus/prometheus.yml`
- Alert rules at `infra/monitoring/prometheus/alerts.yml`

### Alertmanager
- Configure receivers in `infra/monitoring/alertmanager/alertmanager.yml`
- Supported receivers: Slack, PagerDuty

### Grafana
- Provisioned dashboards at `infra/monitoring/grafana/dashboards/`
- Default credentials: `admin:admin` (change in `.env`)

### Loki
- Log aggregation at `infra/monitoring/loki/loki.yml`
- Queryable from Grafana (Loki datasource pre-provisioned)

---

## 5. SSL / TLS

Terminate TLS at the load balancer level (AWS ELB / Traefik).

For nginx-based SSL:
```nginx
server {
    listen 443 ssl;
    server_name veriunlearn.example.com;

    ssl_certificate /etc/nginx/certs/fullchain.pem;
    ssl_certificate_key /etc/nginx/certs/privkey.pem;

    # Forward to nginx HTTP (internal)
    location / { proxy_pass http://frontend; }
    location /api/ { proxy_pass http://backend; }
    location /ws/ { proxy_pass http://backend; }
}
```

---

## 6. CI/CD Pipeline

Two workflows in `.github/workflows/`:
- **`ci.yml`** — Runs on every push: lint, type-check, test (backend + ML engine + frontend), Docker build (on main)
- **`cd.yml`** — Deploys to EKS after successful CI on main

Secrets to configure in GitHub:
- `DOCKER_REGISTRY`, `DOCKER_USERNAME`, `DOCKER_PASSWORD`
- `KUBE_CONFIG` (base64-encoded kubeconfig)
- `SLACK_WEBHOOK` (deployment notifications)

---

## 7. Benchmark Execution

```bash
# Run full benchmark suite
python infra/scripts/run_benchmarks.py

# Generate publication-quality graphs
python infra/scripts/generate_graphs.py
```

Output goes to `infra/scripts/benchmark_results/graphs/`.

---

## 8. Seeding Demo Data

```bash
# After backend is running
python infra/scripts/seed_demo_data.py
```

---

## 9. Backup & Restore

### PostgreSQL
```bash
docker exec -t veriunlearn-postgres-1 pg_dump -U veriunlearn veriunlearn > backup.sql
docker exec -i veriunlearn-postgres-1 psql -U veriunlearn veriunlearn < backup.sql
```

### MinIO (model artifacts)
```bash
docker exec -t veriunlearn-minio-1 mc cp --recursive local/models/ backups/models/
```

### Prometheus (metrics)
- Data at `prometheus-data` volume; backup via Thanos or periodic volume snapshots.

### Grafana (dashboards)
- Dashboards are provisioned from `infra/monitoring/grafana/dashboards/` (git-versioned).

---

## 10. Scaling

### Horizontal scaling
```bash
docker compose up -d --scale worker=4
```

### Resource limits (docker-compose.yml)
```yaml
services:
  ml-engine:
    deploy:
      resources:
        limits:
          memory: 16G
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]
```

---

## 11. Upgrading

```bash
git pull origin main
docker compose build --no-cache
docker compose up -d
```

For DB migrations:
```bash
docker compose exec backend alembic upgrade head
```

---

## 12. Backup and Restore

For automated, whole-stack backups and recovery procedures, see:

- `docs/disaster-recovery.md` — DR plan, RPO/RTO targets, restore scenarios
- `scripts/backup.sh` — timestamped backup of Postgres/Redis/MinIO/Qdrant/app-data
- `scripts/restore.sh` — restores a backup produced by `backup.sh`

---

## 13. Troubleshooting

| Symptom | Likely Cause | Fix |
|---|---|---|
| Backend health fails | DB not ready | `docker compose logs postgres` |
| ML Engine fails | GPU not accessible | `nvidia-smi`; install nvidia-ctk |
| Celery tasks stuck | Redis unreachable | `docker compose logs redis` |
| Certificate generation fails | Qdrant index missing | Check Qdrant logs |
| Frontend 502 | Backend unhealthy | `curl localhost:8000/health` |
| High GPU memory | Model loaded on all GPUs | Set `CUDA_VISIBLE_DEVICES=0` |
