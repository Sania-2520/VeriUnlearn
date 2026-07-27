# VeriUnlearn — Monitoring Guide

## 1. Overview

The VeriUnlearn monitoring stack provides real-time observability into all services, ML engine performance, unlearning job tracking, and compliance alerting. The stack is opt-in via the `monitoring` Docker Compose profile.

### Stack Components

| Component | Service | Port | Purpose |
|-----------|---------|------|---------|
| Prometheus | `prometheus` | 9090 | Metrics collection & alert evaluation |
| Grafana | `grafana` | 3001 | Visualization & dashboards |
| Loki | `loki` | 3100 | Log aggregation |
| Alertmanager | `alertmanager` | 9093 | Alert routing & notification |
| Tempo | *(optional)* | 3200 | Distributed tracing |

### Architecture

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  Backend    │────▶│  Prometheus │◀────│  ML Engine  │
│  /metrics   │     │  :9090      │     │  /metrics   │
└─────────────┘     └──────┬──────┘     └─────────────┘
                          │
                    ┌──────▼──────┐     ┌─────────────┐
                    │ Alertmanager│◀────│  Alert Rules │
                    │  :9093      │     │  alerts.yml  │
                    └──────┬──────┘     └─────────────┘
                           │
              ┌────────────┼────────────┐
              │            │            │
        ┌─────▼────┐ ┌────▼────┐ ┌─────▼────┐
        │ Slack    │ │PagerDuty│ │  Email   │
        └──────────┘ └─────────┘ └──────────┘

┌─────────────┐     ┌─────────────┐
│  Services   │────▶│    Loki     │
│  (logs)     │     │   :3100     │
└─────────────┘     └──────┬──────┘
                           │
                    ┌──────▼──────┐
                    │   Grafana   │
                    │   :3001     │
                    └─────────────┘
```

---

## 2. Prometheus Configuration

### Configuration File

Located at `infra/monitoring/prometheus/prometheus.yml`:

```yaml
global:
  scrape_interval: 15s
  evaluation_interval: 15s
  scrape_timeout: 10s

alerting:
  alertmanagers:
    - static_configs:
        - targets: ["alertmanager:9093"]

rule_files:
  - "alerts.yml"

scrape_configs:
  - job_name: "veriunlearn-backend"
    metrics_path: /metrics
    static_configs:
      - targets: ["backend:8000"]
        labels:
          service: "backend"
          environment: "development"

  - job_name: "veriunlearn-ml-engine"
    metrics_path: /metrics
    static_configs:
      - targets: ["ml-engine:8000"]
        labels:
          service: "ml-engine"
          environment: "development"
```

### Scrape Targets

| Job | Target | Port | Metrics Path | Scrape Interval |
|-----|--------|------|-------------|-----------------|
| `veriunlearn-backend` | backend | 8000 | `/metrics` | 15s |
| `veriunlearn-ml-engine` | ml-engine | 8000 | `/metrics` | 15s |
| `node` | node-exporter | 9100 | `/metrics` | 15s |
| `postgres` | postgres-exporter | 9187 | `/metrics` | 15s |
| `redis` | redis-exporter | 9121 | `/metrics` | 15s |
| `qdrant` | qdrant | 6333 | `/metrics` | 15s |
| `rabbitmq` | rabbitmq | 15692 | `/metrics` | 15s |
| `mlflow` | mlflow | 5000 | `/metrics` | 15s |
| `nvidia-gpu` | nvidia-exporter | 9445 | `/metrics` | 15s |
| `training-metrics` | ml-engine | 8001 | `/metrics` | 30s |

### Storage

- **Type:** TSDB (local filesystem)
- **Path:** `/prometheus`
- **Retention:** 30 days
- **Snapshot:** Prometheus supports snapshot backups for long-term storage

### Startup

```bash
docker compose --profile monitoring up -d prometheus
```

### Key Metrics

| Metric | Type | Description |
|--------|------|-------------|
| `http_requests_total` | Counter | Total HTTP requests by method, endpoint, status |
| `http_request_duration_seconds` | Histogram | Request latency distribution |
| `http_requests_in_flight` | Gauge | Current concurrent requests |
| `unlearning_queue_size` | Gauge | Pending unlearning jobs |
| `unlearning_job_duration_seconds` | Histogram | Unlearning job duration |
| `unlearning_jobs_total` | Counter | Total jobs by status (completed/failed) |
| `inference_request_duration_seconds` | Histogram | ML inference latency |
| `deletion_certificate_expiry_days` | Gauge | Days until certificate expiry |
| `up` | Gauge | Service up/down status (1/0) |
| `scrape_duration_seconds` | Summary | Scrape duration per target |

---

## 3. Grafana Dashboards

### Access

- **URL:** `http://localhost:3001`
- **Default credentials:** `admin` / `admin` (change in `.env`)
- **Pre-provisioned datasources:**
  - Prometheus (`http://prometheus:9090`)
  - Loki (`http://loki:3100`)
  - Tempo (`http://tempo:3200`)
  - PostgreSQL (`postgres:5432`)

### Datasource Configuration

Located at `infra/monitoring/grafana/datasources/datasources.yml`:

```yaml
apiVersion: 1
datasources:
  - name: Prometheus
    type: prometheus
    access: proxy
    url: http://prometheus:9090
    isDefault: true
    editable: false

  - name: Loki
    type: loki
    access: proxy
    url: http://loki:3100
    editable: false

  - name: Tempo
    type: tempo
    access: proxy
    url: http://tempo:3200
    editable: false

  - name: PostgreSQL
    type: postgres
    access: proxy
    url: postgres:5432
    database: veriunlearn
    user: veriunlearn
    secureJsonData:
      password: veriunlearn
    jsonData:
      sslmode: disable
```

### Pre-Provisioned Dashboards

Dashboards are auto-loaded from `infra/monitoring/grafana/dashboards/` on startup.

#### Dashboard 1: VeriUnlearn Overview

**Panels:**
- **Request Rate (RPS):** Graph of HTTP requests per second by endpoint
- **Error Rate (%):** 5xx responses as percentage of total
- **Latency (p95, p99):** Request latency percentiles
- **Active Users:** Concurrent authenticated sessions
- **Service Health:** `up` metric for all services
- **Queue Depth:** Celery unlearning queue size

**Query examples:**
```promql
# Request rate by endpoint
rate(http_requests_total{service="backend"}[5m])

# Error rate
rate(http_requests_total{service="backend", status=~"5.."}[5m]) / rate(http_requests_total{service="backend"}[5m])

# p99 latency
histogram_quantile(0.99, sum(rate(http_request_duration_seconds_bucket{service="backend"}[5m])) by (le))
```

#### Dashboard 2: ML Engine Performance

**Panels:**
- **Inference Latency (p50, p95, p99):** ML inference request duration
- **Inference Throughput:** Requests per second
- **GPU Utilization:** GPU memory and compute usage
- **Model Load Time:** Time to load model checkpoint
- **Unlearning Job Duration:** Histogram of job completion times
- **Algorithm Distribution:** Pie chart of algorithm usage (SISA, Influence, Certified, Hybrid)

#### Dashboard 3: Celery Queue Monitoring

**Panels:**
- **Queue Length:** Active unlearning queue size
- **Worker Availability:** Number of active Celery workers
- **Job Status Distribution:** Completed / running / failed / queued
- **Task Duration by Type:** Average processing time by algorithm
- **Worker Resource Usage:** CPU/memory per worker

#### Dashboard 4: Service Health

**Panels:**
- **Uptime:** Service uptime since last restart
- **Memory Usage:** Container memory usage vs limits
- **CPU Usage:** Container CPU usage vs limits
- **Disk Usage:** Persistent volume utilization
- **Network I/O:** Bytes sent/received per service
- **Restart Count:** Container restart count

#### Dashboard 5: Compliance & Audit

**Panels:**
- **Deletion Requests (24h):** Number of deletion requests submitted
- **Certificate Issuance Rate:** Certificates issued per hour
- **Certificate Status Distribution:** Valid / expiring / expired
- **Compliance Webhook Status:** Recent webhook delivery status
- **Audit Log Entries:** Entries in the audit hash chain

---

## 4. Alert Rules

### Configuration

Located at `infra/monitoring/prometheus/alerts.yml`:

### Alert Catalog

#### Critical Alerts

| Alert Name | Expression | For | Description |
|------------|-----------|-----|-------------|
| `HighErrorRate` | `rate(http_requests_total{status=~"5.."}[5m]) / rate(http_requests_total[5m]) > 0.01` | 5m | HTTP error rate > 1% |
| `HighLatency` | `histogram_quantile(0.99, ...) > 2` | 5m | p99 latency > 2s |
| `ServiceDown` | `up{job=~"veriunlearn-.*"} == 0` | 1m | Service unreachable |
| `DiskSpaceLow` | `node_filesystem_avail_bytes / ... < 0.2` | 5m | Less than 20% disk free |
| `GPUMemoryHigh` | `nvidia_gpu_memory_used_bytes / ... > 0.9` | 5m | GPU memory > 90% |
| `TrainingJobFailed` | `training_status == "failed"` | 0m | Training job failed |
| `InferenceLatencyHigh` | `histogram_quantile(0.99, ...) > 5` | 5m | Inference p99 > 5s |
| `MLflowServiceDown` | `up{job="mlflow"} == 0` | 2m | MLflow unreachable |

#### Warning Alerts

| Alert Name | Expression | For | Description |
|------------|-----------|-----|-------------|
| `UnlearningQueueGrowing` | `unlearning_queue_size > 100` | 10m | Queue > 100 items |
| `DeletionQueueGrowing` | `unlearning_queue_size > 50` | 10m | Queue > 50 (compliance) |
| `DatabaseConnectionsHigh` | `pg_stat_activity_count > 100` | 5m | > 100 DB connections |
| `CertificateExpiring` | `deletion_certificate_expiry_days < 30` | 1h | Cert expires < 30 days |
| `ModelRegistryStorageLow` | `mlflow_registry_disk_usage > 0.9` | 10m | MLflow disk > 90% |

### Response Procedures

#### HighErrorRate

1. Check Loki logs: `{service="backend"} |= "ERROR"`
2. Check recent deployments or config changes
3. Verify database connectivity
4. Check upstream dependencies (MinIO, Qdrant)
5. Scale backend if under load

#### ServiceDown

1. Check container status: `docker compose ps`
2. Check logs: `docker compose logs <service> --tail=50`
3. Restart service: `docker compose up -d --force-recreate <service>`
4. If persistent, check resource limits and OOM killer

#### HighLatency

1. Identify slow endpoint from Grafana breakdown
2. Check database query performance
3. Check Redis cache hit ratio
4. Scale backend replicas
5. Consider read replicas for PostgreSQL

#### UnlearningQueueGrowing

1. Check worker count: `docker compose ps worker`
2. Scale workers: `docker compose up -d --scale worker=<N>`
3. Check ML Engine health and resource usage
4. Review if any worker process is stuck
5. Restart unresponsive workers

---

## 5. Log Aggregation with Loki

### Configuration

Located at `infra/monitoring/loki/loki.yml`:

```yaml
auth_enabled: false

server:
  http_listen_port: 3100

common:
  path_prefix: /loki
  storage:
    filesystem:
      chunks_directory: /loki/chunks
      rules_directory: /loki/rules
  replication_factor: 1
  ring:
    instance_addr: 127.0.0.1
    kvstore:
      store: inmemory

schema_config:
  configs:
    - from: 2020-10-24
      store: boltdb-shipper
      object_store: filesystem
      schema: v11
      index:
        prefix: index_
        period: 24h
```

### Log Format

All services output JSON-structured logs:

```json
{
  "level": "INFO",
  "timestamp": "2026-07-27T12:00:00.000Z",
  "service": "backend",
  "trace_id": "abc123def456",
  "request_id": "del-req-abc123",
  "method": "POST",
  "path": "/api/v1/unlearning/requests",
  "status": 201,
  "duration_ms": 1423,
  "message": "Unlearning request created"
}
```

### LogQL Queries

```logql
# All errors in last hour
{service="backend"} |= "ERROR"

# Specific request trace
{service="worker"} |= "del-req-bfe74a1b98f3"

# Slow requests (> 2s)
{service="backend"} | json | duration_ms > 2000

# Error rate per minute
rate({service="backend"} | json | status >= 500 [1m])

# Failed unlearning jobs
{service="worker"} | json | message = "Unlearning job failed"

# Correlate backend and worker logs by trace ID
{service=~"backend|worker"} |= "trace_id=abc123"
```

### Log Retention

- **Default:** 30 days (filesystem storage)
- **Production:** Consider using S3/GCS object store for cost-effective long-term retention
- **Compliance:** Audit logs require 7-year retention (store separately)

---

## 6. Distributed Tracing (Tempo)

### Overview

Distributed tracing is configured via OpenTelemetry (OTel) and Tempo. Traces track requests across the backend, Celery workers, and ML Engine.

### Configuration

```bash
# Enable OTel in backend
OTEL_EXPORTER_OTLP_ENDPOINT=http://otel-collector:4317
```

### Trace Flow

```
Frontend → nginx → Backend → Celery → ML Engine
                ↓
           PostgreSQL / Redis / Qdrant / MinIO
```

### Trace Context Propagation

- Trace ID is propagated via W3C Trace Context headers
- Celery tasks inherit the parent span
- ML Engine operations are instrumented as child spans
- All database queries are captured as spans

### Viewing Traces in Grafana

1. Open Grafana → Explore
2. Select Tempo datasource
3. Search by trace ID, service name, or duration
4. View span waterfall with timing breakdown

---

## 7. Key Metrics to Monitor

### Application Metrics

| Metric | Threshold | Severity | Action |
|--------|-----------|----------|--------|
| `http_requests_total` | Monitor trend | Info | Capacity planning |
| `http_request_duration_seconds` p99 | < 500ms | Warning | Optimize or scale |
| Error rate (5xx) | < 1% | Critical | Investigate immediately |
| `http_requests_in_flight` | < 100 | Warning | Check concurrency limits |

### Unlearning Metrics

| Metric | Threshold | Severity | Action |
|--------|-----------|----------|--------|
| `unlearning_queue_size` | < 50 | Warning | Scale workers |
| `unlearning_job_duration_seconds` | < 300 (5 min) | Warning | Check ML Engine |
| `unlearning_jobs_total{status="failed"}` | 0 in last hour | Critical | Investigate failures |
| `deletion_certificate_expiry_days` | > 30 | Warning | Renew certificates |

### ML Engine Metrics

| Metric | Threshold | Severity | Action |
|--------|-----------|----------|--------|
| `inference_request_duration_seconds` p99 | < 5s | Critical | Scale GPU resources |
| GPU utilization | < 90% | Warning | Check GPU memory |
| Model load time | < 30s | Warning | Optimize model loading |

### Infrastructure Metrics

| Metric | Threshold | Severity | Action |
|--------|-----------|----------|--------|
| Container memory usage | < 80% of limit | Warning | Increase limit |
| Container CPU usage | < 80% of limit | Warning | Scale horizontally |
| Disk usage | < 80% | Warning | Clean up or expand |
| `up` metric | == 1 | Critical | Restart service |

### Compliance Metrics

| Metric | Threshold | Severity | Action |
|--------|-----------|----------|--------|
| Deletion request SLA breach | 0 | Critical | Process backlog |
| Certificate expiry count | 0 | Warning | Renew certificates |
| Audit log gaps | 0 | Critical | Verify hash chain integrity |

---

## 8. Alert Response Procedures

### On-Call Rotation

- **Schedule:** Weekly rotation, 24/7 coverage
- **Handoff:** Monday 10:00 AM local time
- **Escalation:** Primary → Secondary → Engineering Manager

### Alert Triage Matrix

| Severity | Response Time | Notification | Channel |
|----------|--------------|-------------|---------|
| Critical | 5 minutes | Phone + Slack | PagerDuty + `#veriunlearn-alerts` |
| Warning | 30 minutes | Slack | `#veriunlearn-warnings` |
| Info | Next business day | Slack | `#veriunlearn-monitoring` |

### Incident Response Steps

#### Step 1: Acknowledge
```bash
# Check if anyone is already working on it
# Respond in Slack incident thread
# Ack in PagerDuty if configured
```

#### Step 2: Triage
```bash
# 1. Check Grafana — what changed?
# 2. Check Loki — what errors are occurring?
# 3. Check Prometheus — related alerts?
# 4. Determine blast radius
```

#### Step 3: Mitigate
- Apply rollback if deployment-related
- Scale resources if capacity-related
- Restart service if transient error
- Redirect traffic if zone failure

#### Step 4: Resolve
- Verify metrics return to baseline
- Confirm all services healthy
- Update incident status
- Communicate resolution

#### Step 5: Post-Mortem
- Root cause analysis
- Timeline of events
- Action items with owners
- Runbook updates

### Runbook Links

| Service | Health Check | Restart Command | Logs |
|---------|-------------|----------------|------|
| Backend | `curl localhost:8000/health` | `docker compose restart backend` | `docker compose logs backend` |
| ML Engine | `curl localhost:8001/health` | `docker compose restart ml-engine` | `docker compose logs ml-engine` |
| Worker | `celery inspect ping` | `docker compose restart worker` | `docker compose logs worker` |
| PostgreSQL | `pg_isready` | `docker compose restart postgres` | `docker compose logs postgres` |
| Redis | `redis-cli ping` | `docker compose restart redis` | `docker compose logs redis` |
| Qdrant | `curl localhost:6333/healthz` | `docker compose restart qdrant` | `docker compose logs qdrant` |
| MinIO | `curl localhost:9000/minio/health/live` | `docker compose restart minio` | `docker compose logs minio` |

---

## 9. Troubleshooting

### Prometheus Not Scraping

```bash
# Check Prometheus target status
curl http://localhost:9090/api/v1/targets

# Check service discovery
curl http://localhost:9090/api/v1/service-discovery

# Verify metrics endpoint
curl http://localhost:8000/metrics | head -20

# Check Prometheus logs
docker compose logs prometheus --tail=50
```

### Grafana Dashboards Not Loading

```bash
# Check datasource health
curl -u admin:$GRAFANA_PASSWORD http://localhost:3001/api/datasources

# Verify datasource provisioning
ls -la infra/monitoring/grafana/datasources/

# Check Grafana logs
docker compose logs grafana --tail=50

# Restart Grafana to reload provisioning
docker compose restart grafana
```

### Loki Not Receiving Logs

```bash
# Check Loki readiness
curl http://localhost:3100/ready

# Query Loki for any data
curl -G http://localhost:3100/loki/api/v1/query_range \
  --data-urlencode 'query={service="backend"}' \
  --data-urlencode 'start='$(date -d '1 hour ago' +%s)000000000 \
  --data-urlencode 'end='$(date +%s)000000000

# Check Loki logs
docker compose logs loki --tail=50
```

### Alerts Not Firing

```bash
# Check Alertmanager status
curl http://localhost:9093/api/v2/status

# List active alerts in Prometheus
curl http://localhost:9090/api/v1/alerts

# Test alert rule
curl -X POST http://localhost:9090/api/v1/rules

# Check Alertmanager logs
docker compose logs alertmanager --tail=50
```

---

## 10. Maintenance

### Upgrade Prometheus

```bash
# 1. Stop Prometheus
docker compose --profile monitoring stop prometheus

# 2. Backup data
docker compose run --rm -v prometheus-data:/prometheus alpine tar czf /tmp/prometheus-backup.tar.gz -C /prometheus .

# 3. Update image tag in docker-compose.yml
# 4. Restart
docker compose --profile monitoring up -d prometheus
```

### Extend Retention

```yaml
# In docker-compose.yml prometheus command section
- "--storage.tsdb.retention.time=60d"
```

### Add New Scrape Target

```yaml
# In infra/monitoring/prometheus/prometheus.yml
scrape_configs:
  - job_name: "new-service"
    metrics_path: /metrics
    static_configs:
      - targets: ["new-service:8000"]
```

### Add New Grafana Dashboard

1. Create JSON dashboard
2. Place in `infra/monitoring/grafana/dashboards/`
3. Restart Grafana to auto-provision

---

*See also: [Deployment Guide](DEPLOYMENT_GUIDE.md), [Deployment Checklist](DEPLOYMENT_CHECKLIST.md), [infra/monitoring/](../infra/monitoring/).*
