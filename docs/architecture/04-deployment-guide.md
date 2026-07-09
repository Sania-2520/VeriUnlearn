# VeriUnlearn — Deployment Guide

## Production-grade deployment for enterprise environments

---

## 1. Quick Start (Development)

```bash
# Clone repository
git clone https://github.com/veriunlearn/veriunlearn.git
cd veriunlearn

# Copy environment file
cp .env.example .env

# Start development environment
docker compose -f infra/docker/docker-compose.yml up -d

# Apply database migrations
docker compose exec backend alembic upgrade head

# Access services
# Frontend: http://localhost:3000
# API: http://localhost:8000
# Docs: http://localhost:8000/docs
# Grafana: http://localhost:3001 (admin/admin)
```

---

## 2. Production Deployment (Kubernetes)

### 2.1 Prerequisites

- Kubernetes cluster (EKS, GKE, AKS, or self-managed)
- kubectl configured
- Helm v3 installed
- Container registry access (GHCR, ECR, GCR)

### 2.2 Infrastructure Setup

```bash
# Create namespace
kubectl create namespace veriunlearn-production

# Add Helm repositories
helm repo add bitnami https://charts.bitnami.com/bitnami
helm repo add jetstack https://charts.jetstack.io
helm repo update

# Install cert-manager
helm install cert-manager jetstack/cert-manager \
  --namespace cert-manager --create-namespace \
  --set installCRDs=true

# Install NGINX Ingress
helm install ingress-nginx ingress-nginx/ingress-nginx \
  --namespace ingress-nginx --create-namespace
```

### 2.3 Database Setup

```bash
# PostgreSQL (Production)
helm install postgresql bitnami/postgresql \
  --namespace veriunlearn-production \
  --set auth.username=veriunlearn \
  --set auth.password=<secure-password> \
  --set auth.database=veriunlearn \
  --set persistence.size=100Gi

# Redis
helm install redis bitnami/redis \
  --namespace veriunlearn-production \
  --set auth.password=<secure-password> \
  --set architecture=replication \
  --set master.persistence.size=50Gi
```

### 2.4 Deploy VeriUnlearn

```bash
# Deploy with Helm
helm upgrade --install veriunlearn ./infra/kubernetes/helm \
  --namespace veriunlearn-production \
  --values ./infra/kubernetes/helm/values/production.yaml \
  --set image.tag=<version> \
  --wait --timeout 15m
```

---

## 3. AWS Deployment (EKS)

### 3.1 Terraform

```bash
cd infra/terraform/environments/production

# Initialize
terraform init

# Plan
terraform plan -out=tfplan

# Apply
terraform apply tfplan
```

### 3.2 Manual Steps

```bash
# Configure kubectl
aws eks update-kubeconfig --name veriunlearn-production --region us-east-1

# Deploy secrets
kubectl create secret generic veriunlearn-secrets \
  --namespace veriunlearn-production \
  --from-literal=jwt-secret-key=<...> \
  --from-literal=database-url=<...>

# Apply Kubernetes manifests
kubectl apply -k infra/kubernetes/overlays/production
```

---

## 4. Environment Variables (Production)

See `.env.example` for complete list with descriptions.

Critical production settings:
```bash
ENVIRONMENT=production
DEBUG=false
LOG_LEVEL=INFO
DATABASE_URL=postgresql+asyncpg://user:pass@host:5432/veriunlearn
REDIS_URL=redis://:password@host:6379/0
JWT_SECRET_KEY=<256-bit-random-key>
JWT_ALGORITHM=RS256
CORS_ORIGINS=https://app.veriunlearn.com
```

---

## 5. Scaling

### 5.1 Horizontal Pod Autoscaling

```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
spec:
  minReplicas: 3
  maxReplicas: 20
  metrics:
    - type: Resource
      resource:
        name: cpu
        target:
          type: Utilization
          averageUtilization: 70
    - type: Resource
      resource:
        name: memory
        target:
          type: Utilization
          averageUtilization: 80
```

### 5.2 Target Sizing

| Service | Min | Max | CPU | Memory |
|---------|-----|-----|-----|--------|
| Backend API | 3 | 20 | 2 | 4Gi |
| Celery Worker | 2 | 10 | 4 | 8Gi |
| ML Engine | 1 | 5 | 8 | 32Gi |
| Frontend | 2 | 10 | 1 | 2Gi |

---

## 6. Backup & Disaster Recovery

### 6.1 Database Backups

```bash
# Automated daily backup
0 2 * * * pg_dump -U veriunlearn veriunlearn | gzip > /backups/veriunlearn-$(date +%Y%m%d).sql.gz

# Upload to S3
aws s3 cp /backups/veriunlearn-*.sql.gz s3://veriunlearn-backups/
```

### 6.2 DR Plan

- **RPO**: 1 hour (WAL streaming)
- **RTO**: 30 minutes (automated failover)
- **Multi-region**: Active-passive with Route53 failover

---

## 7. Monitoring Alerts

| Alert | Threshold | Action |
|-------|-----------|--------|
| API Error Rate | > 1% | PagerDuty notification |
| API Latency p99 | > 2s | Auto-scale + alert |
| Disk Usage | > 80% | Increase volume size |
| Unlearning Queue | > 1000 pending | Scale workers |
| Certificate Expiry | < 30 days | Email notification |

---

*For complete deployment documentation, see the `docs/deployment/` directory.*
