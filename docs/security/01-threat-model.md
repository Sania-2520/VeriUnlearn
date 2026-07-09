# VeriUnlearn — Threat Model & Security Architecture

## Version 1.0.0 — Enterprise Security

---

## 1. Threat Modeling Methodology

**Framework**: STRIDE + PASTA  
**Classification**: STRIDE per component, PASTA for business logic  
**Review Cadence**: Quarterly + per major release  

---

## 2. Asset Inventory

| Asset ID | Asset | Classification | Owner | Storage Location |
|----------|-------|---------------|-------|-----------------|
| A-001 | User credentials (password hashes) | Critical | Auth Service | PostgreSQL (encrypted) |
| A-002 | JWT signing keys | Critical | Auth Service | Vault |
| A-003 | AI provider API keys | Critical | AI Service | Vault (encrypted DB) |
| A-004 | User conversation data | Sensitive | Chat Service | PostgreSQL + MinIO |
| A-005 | Document content (RAG) | Sensitive | RAG Engine | MinIO + Qdrant |
| A-006 | Vector embeddings | Sensitive | RAG Engine | Qdrant |
| A-007 | Model weights | Critical | ML Engine | MinIO |
| A-008 | Deletion proofs | High | Verification Engine | PostgreSQL + MinIO |
| A-009 | Audit logs | High | Audit Service | EventStoreDB + PostgreSQL |
| A-010 | Deletion certificates | High | Verification Engine | PostgreSQL + MinIO |
| A-011 | Session tokens | Critical | Auth Service | Redis + PostgreSQL |
| A-012 | OAuth tokens | Critical | Auth Service | PostgreSQL (encrypted) |
| A-013 | Tenant configuration | High | Admin Service | PostgreSQL |
| A-014 | Compliance reports | High | Compliance Service | PostgreSQL |
| A-015 | Security reports | High | Security Engine | PostgreSQL |
| A-016 | Memory entries | Sensitive | Memory Service | PostgreSQL + Qdrant |

---

## 3. Trust Boundaries

```
┌─────────────────────────────────────────────────────────┐
│                     Internet                              │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐         │
│  │ Users       │  │ OAuth       │  │ AI Provider │         │
│  │ (Browser)   │  │ (Google/    │  │ APIs        │         │
│  │             │  │  GitHub)    │  │             │         │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘         │
└─────────┼─────────────────┼─────────────────┼──────────────┘
          │ TB-1            │ TB-2            │ TB-3
          ▼                  ▼                  ▼
┌─────────────────────────────────────────────────────────────────┐
│                    DMZ / Edge Layer                              │
│  ┌──────────────────────────────────────────────────────────┐    │
│  │  CloudFront / Cloudflare                                  │    │
│  │  - WAF, DDoS, TLS termination, Rate limiting              │    │
│  └──────────────────────────┬───────────────────────────────┘    │
│                              │ TB-4                              │
│                              ▼                                    │
│  ┌──────────────────────────────────────────────────────────┐    │
│  │  API Gateway (Kong/Traefik)                               │    │
│  │  - JWT validation, RBAC, Request validation              │    │
│  └──────────────────────────┬───────────────────────────────┘    │
│                              │ TB-5                              │
└──────────────────────────────┼──────────────────────────────────┘
                               │
┌──────────────────────────────┼──────────────────────────────────┐
│                   Internal Network (TB-6)                        │
│                               │                                   │
│  ┌───────────┐  ┌───────────┐┴┐┌───────────┐  ┌────────────┐   │
│  │Auth Svc   │  │Chat Svc   │  │RAG Engine │  │Unlearning  │   │
│  │           │  │           │  │           │  │  Engine    │   │
│  └─────┬─────┘  └─────┬─────┘  └─────┬─────┘  └──────┬─────┘   │
│        │               │              │                │          │
│  ┌─────┴─────────────────┴──────────────┴────────────────┴──┐   │
│  │                 Service Mesh (mTLS)                       │   │
│  └──────────────────────────────────────────────────────────┘   │
│                          │                                       │
│                           │ TB-7                                  │
│                          ▼                                       │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │                Data Layer (TB-8)                          │   │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐   │   │
│  │  │PostgreSQL│ │  Redis   │ │  Qdrant  │ │  MinIO   │   │   │
│  │  └──────────┘ └──────────┘ └──────────┘ └──────────┘   │   │
│  └──────────────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────────────┘
```

---

## 4. STRIDE Threat Analysis

### 4.1 API Gateway

| Threat | Risk | Mitigation |
|--------|------|------------|
| **S**poofing: Attacker impersonates gateway | High | mTLS between services |
| **T**ampering: Request modification | High | Request signing, TLS 1.3 |
| **R**epudiation: Malicious requests | Medium | Request logging, audit trail |
| **I**nformation Disclosure: Route discovery | Low | No debug endpoints in prod |
| **D**enial of Service | High | Rate limiting, WAF, DDoS protection |
| **E**levation of Privilege | High | Strict RBAC, JWT validation |

### 4.2 Auth Service

| Threat | Risk | Mitigation |
|--------|------|------------|
| **S**poofing: Brute force login | High | Rate limiting, account lockout |
| **S**poofing: JWT forgery | Critical | RS256 signatures, short expiry |
| **T**ampering: Token modification | Critical | Signature verification |
| **I**nformation Disclosure: Token leakage | High | HTTPS-only, secure cookies |
| **E**levation of Privilege: Role escalation | Critical | RBAC at API layer |
| **D**enial of Service: Account lockout | Medium | CAPTCHA, progressive delays |

### 4.3 Chat Service

| Threat | Risk | Mitigation |
|--------|------|------------|
| **S**poofing: Cross-tenant access | Critical | Tenant isolation checks |
| **I**nformation Disclosure: Conversation leakage | Critical | Row-level security |
| **T**ampering: Message injection | High | Input sanitization |
| **D**enial of Service: Stream exhaustion | Medium | Backpressure, circuit breakers |
| **R**epudiation: Message deletion | High | Soft delete + audit trail |

### 4.4 Unlearning Engine

| Threat | Risk | Mitigation |
|--------|------|------------|
| **T**ampering: Unlearning bypass | Critical | Cryptographic proof required |
| **R**epudiation: Incomplete deletion | Critical | Verification engine validation |
| **I**nformation Disclosure: Data retention | Critical | Secure wipe + proof |
| **E**levation of Privilege: Unauthorized unlearning | Critical | Strict authorization |
| **D**enial of Service: Queue overflow | Medium | Bounded queue, backpressure |

### 4.5 Verification Engine

| Threat | Risk | Mitigation |
|--------|------|------------|
| **T**ampering: Merkle tree manipulation | Critical | Ed25519 signatures |
| **S**poofing: Fake proofs | Critical | Signature verification |
| **R**epudiation: Proof rejection | High | Public verification APIs |
| **I**nformation Disclosure: Proof contents | Medium | Selective disclosure via zk |

### 4.6 Data Layer

| Threat | Risk | Mitigation |
|--------|------|------------|
| **I**nformation Disclosure: Data breach | Critical | AES-256 encryption |
| **T**ampering: Data corruption | High | Checksums, WAL |
| **D**enial of Service: Storage exhaustion | Medium | Auto-scaling, limits |
| **S**poofing: Unauthorized DB access | Critical | Network isolation, IAM |

---

## 5. Attack Trees

### 5.1 Data Breach Attack Tree

```
Goal: Exfiltrate User Conversation Data
├── 1.0 Compromise API Gateway
│   ├── 1.1 Exploit WAF bypass (Medium)
│   ├── 1.2 Steal JWT from client (High)
│   └── 1.3 TLS interception (Low)
├── 2.0 Compromise Auth Service
│   ├── 2.1 Brute force credentials (Medium)
│   ├── 2.2 OAuth token theft (High)
│   └── 2.3 Session hijacking (High)
├── 3.0 Direct Database Access
│   ├── 3.1 SQL injection (Low - mitigated by ORM)
│   ├── 3.2 Compromised credentials (High)
│   └── 3.3 Network-level access (Low)
├── 4.0 Side Channel
│   ├── 4.1 Timing attack on API (Low)
│   ├── 4.2 Cache poisoning (Medium)
│   └── 4.3 Inference from embeddings (Medium)
└── 5.0 Insider Threat
    ├── 5.1 Malicious admin (High)
    ├── 5.2 Compromised CI/CD (High)
    └── 5.3 Backup exposure (Medium)
```

### 5.2 Unlearning Bypass Attack Tree

```
Goal: Data persists after unlearning
├── 1.0 Bypass Deletion Queue
│   ├── 1.1 Queue message interception (Low)
│   ├── 1.2 Worker failure without retry (Medium)
│   └── 1.3 Partial deletion (Medium)
├── 2.0 Bypass Proof Generation
│   ├── 2.1 Merkle tree manipulation (Low)
│   ├── 2.2 Signature key compromise (High)
│   └── 2.3 Proof generation skip (Low)
├── 3.0 Data Shadow Copies
│   ├── 3.1 Backups containing deleted data (High)
│   ├── 3.2 Replicas not synced (High)
│   └── 3.3 Cache TTL not expired (Medium)
└── 4.0 Model Influence Persists
    ├── 4.1 SISA shard not retrained (Medium)
    ├── 4.2 Influence function miscalculation (Low)
    └── 4.3 Model quantization artifacts (Low)
```

---

## 6. Security Controls

### 6.1 Preventive Controls

| Control ID | Control | Implementation |
|------------|---------|----------------|
| PC-01 | Identity & Access Management | JWT + OAuth 2.0 + RBAC |
| PC-02 | Network Security | VPC, subnets, security groups |
| PC-03 | Encryption at Rest | AES-256 for all data stores |
| PC-04 | Encryption in Transit | TLS 1.3, mTLS for services |
| PC-05 | Input Validation | Pydantic schemas, sanitization |
| PC-06 | Rate Limiting | Token bucket per tenant/user |
| PC-07 | WAF | OWASP ModSecurity rules |
| PC-08 | Secure Config | External Secrets / Vault |
| PC-09 | Container Security | Distroless images, no root |
| PC-10 | API Security | OpenAPI validation, nonces |

### 6.2 Detective Controls

| Control ID | Control | Implementation |
|------------|---------|----------------|
| DC-01 | Audit Logging | Immutable Merkle chain |
| DC-02 | Intrusion Detection | Falco + OSSEC |
| DC-03 | Anomaly Detection | ML-based behavioral analysis |
| DC-04 | Vulnerability Scanning | Trivy, Snyk, Dependabot |
| DC-05 | Security Monitoring | Prometheus + Grafana alerts |
| DC-06 | Penetration Testing | Scheduled + CI/CD integrated |
| DC-07 | Threat Intelligence | Feodo Tracker + AlienVault OTX |

### 6.3 Corrective Controls

| Control ID | Control | Implementation |
|------------|---------|----------------|
| CC-01 | Incident Response | Runbook automation |
| CC-02 | Backup Restore | Point-in-time recovery |
| CC-03 | Model Rollback | Versioned model registry |
| CC-04 | Key Rotation | Automatic key rotation |
| CC-05 | Tenant Isolation | Complete data segregation |
| CC-06 | Rate Limit Bypass | Circuit breaker pattern |

---

## 7. Secret Management

```
┌─────────────────────────────────────────────┐
│           HashiCorp Vault                    │
│                                              │
│  Secrets Paths:                              │
│  ├── veriunlearn/{env}/database/*            │
│  ├── veriunlearn/{env}/redis/*               │
│  ├── veriunlearn/{env}/jwt/*                 │
│  ├── veriunlearn/{env}/oauth/*               │
│  ├── veriunlearn/{env}/ai-providers/*        │
│  ├── veriunlearn/{env}/minio/*               │
│  └── veriunlearn/{env}/encryption-keys/*     │
│                                              │
│  Policies:                                   │
│  ├── admin - full access                     │
│  ├── service-{name} - path-specific           │
│  └── audit - read-only                       │
│                                              │
│  Dynamic Secrets:                            │
│  ├── PostgreSQL - short-lived credentials    │
│  └── Redis - temporary access tokens         │
└─────────────────────────────────────────────┘
```

---

## 8. Security Compliance Mapping

| Requirement | GDPR | AI Act | SOC 2 | ISO 27001 | Implementation |
|-------------|------|--------|-------|-----------|----------------|
| Right to be Forgotten | Art. 17 | — | — | — | Unlearning Engine |
| Data Portability | Art. 20 | — | — | — | Export APIs |
| Data Encryption | Art. 32 | — | CC6.1 | A.10.1 | AES-256, TLS 1.3 |
| Access Control | Art. 25 | Art. 9 | CC6.3 | A.9.1 | RBAC, JWT |
| Audit Trail | Art. 30 | Art. 19 | CC3.2 | A.12.4 | Merkle Chain |
| Incident Response | Art. 33 | Art. 20 | CC7.2 | A.16.1 | Runbooks |
| Risk Assessment | Art. 35 | Art. 17 | — | A.6.1 | Security Engine |
| Model Transparency | — | Art. 13 | — | — | Model Lineage |
| Human Oversight | — | Art. 14 | — | — | Compliance Dashboard |
| Accuracy/Robustness | — | Art. 15 | — | — | Security Reports |

---

## 9. Incident Response Plan

### 9.1 Severity Levels

| Severity | Definition | Response Time | Escalation |
|----------|------------|--------------|------------|
| SEV-0 | Data breach, service outage | < 15 min | CISO, VP Eng |
| SEV-1 | Unlearning failure, auth bypass | < 30 min | Security Team |
| SEV-2 | Performance degradation, partial outage | < 2 hrs | On-call engineer |
| SEV-3 | Minor bugs, cosmetic issues | < 24 hrs | Dev team |

### 9.2 Response Phases

1. **Detection** — Automated alerts + monitoring
2. **Triage** — Determine severity, assemble response team
3. **Containment** — Isolate affected components, revoke access
4. **Eradication** — Remove threat, patch vulnerabilities
5. **Recovery** — Restore from clean backups, verify integrity
6. **Post-Mortem** — Root cause analysis, prevention plan

---

## 10. Security Testing Cadence

| Test Type | Frequency | Tool/Method |
|-----------|-----------|-------------|
| SAST | Every commit | Semgrep, Bandit |
| DAST | Weekly | OWASP ZAP |
| Dependency Scan | Daily | Dependabot, Snyk |
| Container Scan | Every build | Trivy |
| Secret Detection | Every commit | GitLeaks, TruffleHog |
| Penetration Test | Quarterly | External firm |
| Red Team | Bi-annual | Internal team |
| Bug Bounty | Continuous | HackerOne |
| Compliance Audit | Annual | External auditor |

---

## 11. Security Assumptions & Dependencies

### Assumptions
- Cloud provider (AWS/GCP/Azure) is responsible for physical security
- Employees follow secure development practices
- Third-party AI providers have adequate security
- Cryptographic primitives are correctly implemented

### Dependencies
- Vault availability for secret management
- Cloud KMS for key management
- Certificate transparency logs for PKI
- NTP for audit timestamp accuracy

---

*This threat model is a living document and must be updated as the platform evolves. Every architectural change must be reviewed against this document.*
