# VeriUnlearn — Database Schema

## Version 1.0.0 — Enterprise Data Architecture

---

## 1. PostgreSQL Schema

### 1.1 Tenant Management

```sql
-- Tenants (organizations)
CREATE TABLE tenants (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    slug VARCHAR(128) UNIQUE NOT NULL,
    domain VARCHAR(255),
    plan VARCHAR(50) NOT NULL DEFAULT 'starter',
        -- starter, professional, enterprise, custom
    settings JSONB NOT NULL DEFAULT '{}',
        -- tenant-specific configurations
    features JSONB NOT NULL DEFAULT '{}',
        -- feature flags
    max_users INTEGER NOT NULL DEFAULT 10,
    max_storage_gb INTEGER NOT NULL DEFAULT 10,
    max_api_requests_per_min INTEGER NOT NULL DEFAULT 1000,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_tenants_slug ON tenants(slug);
CREATE INDEX idx_tenants_domain ON tenants(domain);

-- Tenant API keys
CREATE TABLE tenant_api_keys (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    key_hash VARCHAR(255) NOT NULL,
    key_prefix VARCHAR(8) NOT NULL,
    scopes JSONB NOT NULL DEFAULT '[]',
    expires_at TIMESTAMPTZ,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    last_used_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_tenant_api_keys_tenant ON tenant_api_keys(tenant_id);
CREATE INDEX idx_tenant_api_keys_prefix ON tenant_api_keys(key_prefix);
```

### 1.2 User Management

```sql
-- Users
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    full_name VARCHAR(255) NOT NULL,
    avatar_url VARCHAR(512),
    role VARCHAR(50) NOT NULL DEFAULT 'member',
        -- admin, member, viewer, unlearning_auditor, compliance_officer
    is_email_verified BOOLEAN NOT NULL DEFAULT FALSE,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    is_locked BOOLEAN NOT NULL DEFAULT FALSE,
    locked_until TIMESTAMPTZ,
    failed_login_attempts INTEGER NOT NULL DEFAULT 0,
    last_login_at TIMESTAMPTZ,
    last_login_ip INET,
    mfa_enabled BOOLEAN NOT NULL DEFAULT FALSE,
    mfa_secret VARCHAR(255),
    preferences JSONB NOT NULL DEFAULT '{}',
        -- theme, language, notifications, etc.
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_users_tenant ON users(tenant_id);
CREATE INDEX idx_users_email ON users(email);
CREATE UNIQUE INDEX idx_users_tenant_email ON users(tenant_id, email);

-- OAuth accounts
CREATE TABLE oauth_accounts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    provider VARCHAR(50) NOT NULL,
        -- google, github
    provider_user_id VARCHAR(255) NOT NULL,
    provider_email VARCHAR(255),
    access_token TEXT,
    refresh_token TEXT,
    expires_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(provider, provider_user_id)
);

CREATE INDEX idx_oauth_accounts_user ON oauth_accounts(user_id);

-- Sessions
CREATE TABLE sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    refresh_token_hash VARCHAR(255) NOT NULL,
    access_token_jti VARCHAR(255) UNIQUE NOT NULL,
    user_agent TEXT,
    ip_address INET,
    device_name VARCHAR(255),
    is_revoked BOOLEAN NOT NULL DEFAULT FALSE,
    expires_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    revoked_at TIMESTAMPTZ
);

CREATE INDEX idx_sessions_user ON sessions(user_id);
CREATE INDEX idx_sessions_refresh ON sessions(refresh_token_hash);
CREATE INDEX idx_sessions_jti ON sessions(access_token_jti);
```

### 1.3 Chat & Conversations

```sql
-- Chat sessions (conversations)
CREATE TABLE chat_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    title VARCHAR(255) NOT NULL DEFAULT 'New Chat',
    folder_id UUID REFERENCES chat_folders(id) ON DELETE SET NULL,
    ai_provider_id UUID REFERENCES ai_providers(id) ON DELETE SET NULL,
    model VARCHAR(255),
    system_prompt TEXT,
    temperature REAL DEFAULT 0.7,
    max_tokens INTEGER DEFAULT 4096,
    is_pinned BOOLEAN NOT NULL DEFAULT FALSE,
    is_archived BOOLEAN NOT NULL DEFAULT FALSE,
    is_deleted BOOLEAN NOT NULL DEFAULT FALSE,
    deleted_at TIMESTAMPTZ,
    message_count INTEGER NOT NULL DEFAULT 0,
    total_tokens INTEGER NOT NULL DEFAULT 0,
    total_cost REAL NOT NULL DEFAULT 0.0,
    metadata JSONB NOT NULL DEFAULT '{}',
    last_activity_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_chat_sessions_user ON chat_sessions(user_id);
CREATE INDEX idx_chat_sessions_tenant ON chat_sessions(tenant_id);
CREATE INDEX idx_chat_sessions_folder ON chat_sessions(folder_id);
CREATE INDEX idx_chat_sessions_pinned ON chat_sessions(user_id, is_pinned) WHERE is_pinned = TRUE;
CREATE INDEX idx_chat_sessions_deleted ON chat_sessions(deleted_at) WHERE is_deleted = TRUE;
CREATE INDEX idx_chat_sessions_activity ON chat_sessions(last_activity_at DESC);

-- Chat folders
CREATE TABLE chat_folders (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    parent_id UUID REFERENCES chat_folders(id) ON DELETE CASCADE,
    sort_order INTEGER NOT NULL DEFAULT 0,
    is_deleted BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_chat_folders_user ON chat_folders(user_id);
CREATE INDEX idx_chat_folders_parent ON chat_folders(parent_id);

-- Messages
CREATE TABLE messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID NOT NULL REFERENCES chat_sessions(id) ON DELETE CASCADE,
    parent_id UUID REFERENCES messages(id),
    role VARCHAR(50) NOT NULL,
        -- user, assistant, system, tool
    content TEXT NOT NULL,
    content_type VARCHAR(50) NOT NULL DEFAULT 'text',
        -- text, markdown, latex, code, image, audio
    content_rendered TEXT,
    metadata JSONB NOT NULL DEFAULT '{}',
        -- token_count, cost, model, provider, latency, etc.
    is_streaming BOOLEAN NOT NULL DEFAULT FALSE,
    is_regenerated BOOLEAN NOT NULL DEFAULT FALSE,
    is_edited BOOLEAN NOT NULL DEFAULT FALSE,
    feedback VARCHAR(50),
        -- like, dislike, null
    tokens_input INTEGER DEFAULT 0,
    tokens_output INTEGER DEFAULT 0,
    cost REAL DEFAULT 0.0,
    latency_ms INTEGER,
    model_used VARCHAR(255),
    provider_used VARCHAR(255),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_messages_session ON messages(session_id);
CREATE INDEX idx_messages_parent ON messages(parent_id);
CREATE INDEX idx_messages_created ON messages(session_id, created_at);
```

### 1.4 AI Providers

```sql
-- AI Providers
CREATE TABLE ai_providers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    provider_type VARCHAR(100) NOT NULL,
        -- openai, anthropic, google, azure, ollama, vllm, huggingface
    api_base_url VARCHAR(512),
    api_key_encrypted TEXT,
    models JSONB NOT NULL DEFAULT '[]',
        -- list of available model names
    config JSONB NOT NULL DEFAULT '{}',
        -- provider-specific configuration
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    priority INTEGER NOT NULL DEFAULT 0,
    rate_limit_per_min INTEGER DEFAULT 1000,
    cost_per_input_token REAL DEFAULT 0.0,
    cost_per_output_token REAL DEFAULT 0.0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(tenant_id, provider_type)
);

CREATE INDEX idx_ai_providers_tenant ON ai_providers(tenant_id);
```

### 1.5 RAG & Documents

```sql
-- Documents
CREATE TABLE documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    filename VARCHAR(512) NOT NULL,
    original_filename VARCHAR(512) NOT NULL,
    file_type VARCHAR(50) NOT NULL,
        -- pdf, docx, txt, csv, png, jpg, etc.
    file_size_bytes BIGINT NOT NULL,
    storage_path VARCHAR(1024) NOT NULL,
    storage_bucket VARCHAR(255) NOT NULL,
    mime_type VARCHAR(127),
    page_count INTEGER,
    status VARCHAR(50) NOT NULL DEFAULT 'pending',
        -- pending, processing, indexed, failed, deleted
    error_message TEXT,
    chunk_count INTEGER DEFAULT 0,
    metadata JSONB NOT NULL DEFAULT '{}',
    content_hash VARCHAR(64),
    is_deleted BOOLEAN NOT NULL DEFAULT FALSE,
    deleted_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_documents_tenant ON documents(tenant_id);
CREATE INDEX idx_documents_user ON documents(user_id);
CREATE INDEX idx_documents_status ON documents(status);
CREATE INDEX idx_documents_type ON documents(file_type);

-- Document chunks
CREATE TABLE document_chunks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    chunk_index INTEGER NOT NULL,
    content TEXT NOT NULL,
    content_hash VARCHAR(64) NOT NULL,
    token_count INTEGER NOT NULL DEFAULT 0,
    metadata JSONB NOT NULL DEFAULT '{}',
        -- section, page_number, heading, etc.
    embedding_id UUID,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(document_id, chunk_index)
);

CREATE INDEX idx_document_chunks_document ON document_chunks(document_id);

-- OCR results
CREATE TABLE ocr_results (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    page_number INTEGER NOT NULL,
    raw_text TEXT NOT NULL,
    confidence REAL,
    bounding_boxes JSONB,
    language VARCHAR(50),
    processing_time_ms INTEGER,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(document_id, page_number)
);

CREATE INDEX idx_ocr_results_document ON ocr_results(document_id);
```

### 1.6 Memory System

```sql
-- Memory entries
CREATE TABLE memory_entries (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    session_id UUID REFERENCES chat_sessions(id) ON DELETE CASCADE,
    memory_type VARCHAR(50) NOT NULL,
        -- session, conversation, persistent, user, workspace
    category VARCHAR(100),
        -- fact, preference, context, summary, entity
    content JSONB NOT NULL,
        -- flexible content structure
    importance REAL DEFAULT 1.0,
        -- 0.0 to 1.0 for memory consolidation
    access_count INTEGER NOT NULL DEFAULT 0,
    last_accessed_at TIMESTAMPTZ,
    expires_at TIMESTAMPTZ,
    metadata JSONB NOT NULL DEFAULT '{}',
    is_deleted BOOLEAN NOT NULL DEFAULT FALSE,
    deleted_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_memory_entries_user ON memory_entries(user_id);
CREATE INDEX idx_memory_entries_tenant ON memory_entries(tenant_id);
CREATE INDEX idx_memory_entries_session ON memory_entries(session_id);
CREATE INDEX idx_memory_entries_type ON memory_entries(memory_type);
CREATE INDEX idx_memory_entries_importance ON memory_entries(importance DESC);
CREATE INDEX idx_memory_entries_expires ON memory_entries(expires_at) WHERE expires_at IS NOT NULL;
```

### 1.7 Unlearning Engine

```sql
-- Unlearning requests
CREATE TABLE unlearning_requests (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    requested_by UUID NOT NULL REFERENCES users(id),
    target_type VARCHAR(50) NOT NULL,
        -- conversation, message, document, embedding, memory, user_data
    target_id UUID NOT NULL,
    reason VARCHAR(255),
    gdpr_article VARCHAR(50),
        -- 17, 16, 32
    status VARCHAR(50) NOT NULL DEFAULT 'pending',
        -- pending, queued, processing, completed, failed, verified
    priority VARCHAR(20) NOT NULL DEFAULT 'normal',
        -- low, normal, high, critical
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_unlearning_requests_tenant ON unlearning_requests(tenant_id);
CREATE INDEX idx_unlearning_requests_status ON unlearning_requests(status);
CREATE INDEX idx_unlearning_requests_target ON unlearning_requests(target_type, target_id);

-- Unlearning jobs
CREATE TABLE unlearning_jobs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    request_id UUID NOT NULL REFERENCES unlearning_requests(id) ON DELETE CASCADE,
    algorithm VARCHAR(100) NOT NULL,
        -- sisa, influence_function, certified_removal, approximate, hybrid
    model_id UUID REFERENCES model_versions(id),
    status VARCHAR(50) NOT NULL DEFAULT 'pending',
        -- pending, processing, completed, failed
    progress REAL DEFAULT 0.0,
    error_message TEXT,
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    processing_time_ms INTEGER,
    results JSONB,
        -- unlearning metrics, influenced parameters, etc.
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_unlearning_jobs_request ON unlearning_jobs(request_id);
CREATE INDEX idx_unlearning_jobs_algorithm ON unlearning_jobs(algorithm);
CREATE INDEX idx_unlearning_jobs_status ON unlearning_jobs(status);

-- Deletion queue
CREATE TABLE deletion_queue (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    job_id UUID REFERENCES unlearning_jobs(id) ON DELETE SET NULL,
    resource_type VARCHAR(50) NOT NULL,
        -- postgres, redis, qdrant, minio, cache, memory, model
    resource_id VARCHAR(255) NOT NULL,
    operation VARCHAR(50) NOT NULL,
        -- delete, nullify, forget, prune
    priority INTEGER NOT NULL DEFAULT 0,
    status VARCHAR(50) NOT NULL DEFAULT 'pending',
        -- pending, processing, completed, failed
    retry_count INTEGER NOT NULL DEFAULT 0,
    max_retries INTEGER NOT NULL DEFAULT 3,
    error_message TEXT,
    locked_until TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_deletion_queue_tenant ON deletion_queue(tenant_id);
CREATE INDEX idx_deletion_queue_status ON deletion_queue(status);
CREATE INDEX idx_deletion_queue_priority ON deletion_queue(priority DESC, created_at);
CREATE INDEX idx_deletion_queue_locked ON deletion_queue(locked_until) WHERE locked_until IS NOT NULL;

-- Model versions
CREATE TABLE model_versions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    version INTEGER NOT NULL,
    parent_version_id UUID REFERENCES model_versions(id),
    algorithm VARCHAR(100),
    checkpoint_path VARCHAR(1024),
    model_weights_hash VARCHAR(64),
    metrics JSONB NOT NULL DEFAULT '{}',
        -- accuracy, f1, loss, etc.
    config JSONB NOT NULL DEFAULT '{}',
        -- training config, architecture, hyperparameters
    status VARCHAR(50) NOT NULL DEFAULT 'active',
        -- training, active, archived, deprecated
    is_unlearned BOOLEAN NOT NULL DEFAULT FALSE,
    shard_count INTEGER DEFAULT 1,
    total_data_points INTEGER DEFAULT 0,
    removed_data_points INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(tenant_id, name, version)
);

CREATE INDEX idx_model_versions_tenant ON model_versions(tenant_id);
CREATE INDEX idx_model_versions_parent ON model_versions(parent_version_id);

-- Model shards (for SISA)
CREATE TABLE model_shards (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    model_version_id UUID NOT NULL REFERENCES model_versions(id) ON DELETE CASCADE,
    shard_index INTEGER NOT NULL,
    checkpoint_path VARCHAR(1024),
    data_range JSONB NOT NULL,
        -- data point range for this shard
    data_point_count INTEGER NOT NULL DEFAULT 0,
    metrics JSONB NOT NULL DEFAULT '{}',
    status VARCHAR(50) NOT NULL DEFAULT 'active',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(model_version_id, shard_index)
);

CREATE INDEX idx_model_shards_version ON model_shards(model_version_id);
```

### 1.8 Verification & Proofs

```sql
-- Deletion proofs
CREATE TABLE deletion_proofs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    job_id UUID NOT NULL REFERENCES unlearning_jobs(id) ON DELETE CASCADE,
    request_id UUID NOT NULL REFERENCES unlearning_requests(id),
    proof_type VARCHAR(50) NOT NULL,
        -- merkle, zksnark, hybrid
    merkle_root VARCHAR(64) NOT NULL,
    merkle_tree_depth INTEGER NOT NULL,
    merkle_tree JSONB NOT NULL,
        -- serialized tree for verification
    signature_algorithm VARCHAR(50) NOT NULL DEFAULT 'ed25519',
    signature_hex TEXT NOT NULL,
    public_key_hex TEXT NOT NULL,
    zk_proof JSONB,
        -- zkSNARK proof if applicable
    certificate TEXT,
        -- X.509-compatible deletion certificate
    certificate_hash VARCHAR(64),
    verified BOOLEAN NOT NULL DEFAULT FALSE,
    verified_at TIMESTAMPTZ,
    metadata JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at TIMESTAMPTZ
);

CREATE INDEX idx_deletion_proofs_tenant ON deletion_proofs(tenant_id);
CREATE INDEX idx_deletion_proofs_job ON deletion_proofs(job_id);
CREATE INDEX idx_deletion_proofs_request ON deletion_proofs(request_id);
CREATE INDEX idx_deletion_proofs_merkle ON deletion_proofs(merkle_root);

-- Proof verification log
CREATE TABLE proof_verifications (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    proof_id UUID NOT NULL REFERENCES deletion_proofs(id) ON DELETE CASCADE,
    verifier_id UUID REFERENCES users(id),
    verification_method VARCHAR(50) NOT NULL,
        -- api, cli, blockchain, manual
    is_valid BOOLEAN NOT NULL,
    details JSONB NOT NULL DEFAULT '{}',
    verified_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_proof_verifications_proof ON proof_verifications(proof_id);
```

### 1.9 Audit System

```sql
-- Audit events (immutable)
CREATE TABLE audit_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    event_type VARCHAR(100) NOT NULL,
        -- user.login, chat.delete, unlearning.complete, proof.generate, etc.
    event_version VARCHAR(20) NOT NULL DEFAULT '1.0',
    actor_id UUID,
    actor_type VARCHAR(50) NOT NULL DEFAULT 'user',
        -- user, system, api_key, admin
    resource_type VARCHAR(50),
    resource_id UUID,
    action VARCHAR(50) NOT NULL,
        -- create, read, update, delete, unlearn, verify, export
    status VARCHAR(50) NOT NULL,
        -- success, failure, pending
    metadata JSONB NOT NULL DEFAULT '{}',
        -- rich event context
    changes JSONB,
        -- before/after snapshots for sensitive operations
    ip_address INET,
    user_agent TEXT,
    session_id UUID,
    request_id VARCHAR(255),
    merkle_node_hash VARCHAR(64),
    previous_event_hash VARCHAR(64),
    event_hash VARCHAR(64) NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(event_hash)
);

CREATE INDEX idx_audit_events_tenant ON audit_events(tenant_id);
CREATE INDEX idx_audit_events_type ON audit_events(event_type);
CREATE INDEX idx_audit_events_actor ON audit_events(actor_id, actor_type);
CREATE INDEX idx_audit_events_resource ON audit_events(resource_type, resource_id);
CREATE INDEX idx_audit_events_timestamp ON audit_events(timestamp DESC);
CREATE INDEX idx_audit_events_merkle ON audit_events(previous_event_hash);

-- Audit chain (Merkle chain)
CREATE TABLE audit_chain_heads (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    last_event_hash VARCHAR(64) NOT NULL,
    chain_length BIGINT NOT NULL DEFAULT 0,
    merkle_root VARCHAR(64),
    blockchain_tx_hash VARCHAR(255),
    blockchain_network VARCHAR(50),
    anchored_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_audit_chain_heads_tenant ON audit_chain_heads(tenant_id);
```

### 1.10 Security Reports

```sql
-- Security reports
CREATE TABLE security_reports (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    model_version_id UUID REFERENCES model_versions(id),
    report_type VARCHAR(50) NOT NULL,
        -- membership_inference, model_extraction, privacy_leakage, model_inversion, full_audit
    status VARCHAR(50) NOT NULL DEFAULT 'pending',
    results JSONB NOT NULL DEFAULT '{}',
    scores JSONB NOT NULL DEFAULT '{}',
        -- mi_score, extraction_score, inversion_score, overall_score
    risk_level VARCHAR(20) NOT NULL DEFAULT 'low',
        -- low, medium, high, critical
    recommendations JSONB,
    attack_config JSONB,
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_security_reports_tenant ON security_reports(tenant_id);
CREATE INDEX idx_security_reports_model ON security_reports(model_version_id);
CREATE INDEX idx_security_reports_type ON security_reports(report_type);
```

### 1.11 Compliance

```sql
-- Compliance reports
CREATE TABLE compliance_reports (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    report_type VARCHAR(50) NOT NULL,
        -- gdpr, ai_act, dpdp
    report_period_start DATE NOT NULL,
    report_period_end DATE NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'draft',
        -- draft, generated, reviewed, published
    overall_score REAL,
    sections JSONB NOT NULL DEFAULT '{}',
    findings JSONB NOT NULL DEFAULT '[]',
    recommendations JSONB NOT NULL DEFAULT '[]',
    risk_score REAL,
    generated_by UUID REFERENCES users(id),
    generated_at TIMESTAMPTZ,
    published_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_compliance_reports_tenant ON compliance_reports(tenant_id);
CREATE INDEX idx_compliance_reports_type ON compliance_reports(report_type, report_period_start);

-- Deletion certificates
CREATE TABLE deletion_certificates (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    request_id UUID NOT NULL REFERENCES unlearning_requests(id),
    proof_id UUID REFERENCES deletion_proofs(id),
    certificate_hash VARCHAR(64) UNIQUE NOT NULL,
    certificate_data TEXT NOT NULL,
        -- full certificate JSON
    signature TEXT NOT NULL,
    issued_by UUID REFERENCES users(id),
    issued_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at TIMESTAMPTZ,
    revoked_at TIMESTAMPTZ,
    revocation_reason TEXT
);

CREATE INDEX idx_deletion_certificates_tenant ON deletion_certificates(tenant_id);
CREATE INDEX idx_deletion_certificates_hash ON deletion_certificates(certificate_hash);
```

---

## 2. Redis Schema

### 2.1 Cache Patterns

```
# Session cache
sessions:{session_id} → { user_id, tenant_id, role, expires_at }
TTL: match JWT expiry

# Rate limiting
ratelimit:{tenant_id}:{endpoint} → { count, window_start }
TTL: 60 seconds

# Chat streaming
chat:stream:{session_id}:{message_id} → SSE events queue
TTL: 5 minutes after completion

# Provider rate limiting
provider:{tenant_id}:{provider_type} → { tokens_used, reset_at }
TTL: sliding window

# OAuth state
oauth:{state} → { provider, redirect_uri, code_verifier }
TTL: 10 minutes

# Email verification
verify:email:{token} → { user_id, email }
TTL: 24 hours

# Password reset
reset:password:{token} → { user_id, email }
TTL: 1 hour

# Lockout tracking
lockout:{user_id} → { attempts, last_attempt }
TTL: 15 minutes after last attempt

# Unlearning job locks
unlearning:lock:{job_id} → { worker_id, acquired_at }
TTL: 10 minutes (heartbeat-based)

# Model cache predictions
model:cache:{model_hash}:{input_hash} → { output, confidence }
TTL: configurable (minutes to hours)

# Document processing locks
doc:processing:{document_id} → { worker_id }
TTL: 30 minutes

# Embedding cache
embedding:{text_hash}:{model} → vector
TTL: 24 hours
```

### 2.2 Pub/Sub Channels

```
chat:message:{session_id} — real-time message delivery
unlearning:progress:{job_id} — job progress updates
notifications:user:{user_id} — user notifications
system:alerts — system-wide alerts
deployment:status — deployment status updates
```

---

## 3. Qdrant Schema

### 3.1 Collections

```yaml
# Document embeddings collection
documents:
  vectors:
    size: 1536  # or 768/1024 depending on model
    distance: Cosine
  payload:
    - document_id: UUID
    - chunk_id: UUID
    - tenant_id: UUID
    - content: Text
    - metadata: JSON
  index:
    - tenant_id: keyword
    - document_id: keyword
    - created_at: datetime

# Memory embeddings collection
memory:
  vectors:
    size: 1536
    distance: Cosine
  payload:
    - memory_id: UUID
    - user_id: UUID
    - tenant_id: UUID
    - type: Keyword
    - content: Text
  index:
    - user_id: keyword
    - tenant_id: keyword
    - type: keyword

# Conversation context collection
conversations:
  vectors:
    size: 1536
    distance: Cosine
  payload:
    - session_id: UUID
    - message_id: UUID
    - tenant_id: UUID
    - role: Keyword
    - content: Text
    - timestamp: Datetime
  index:
    - session_id: keyword
    - tenant_id: keyword
```

---

## 4. MinIO Buckets

```
veriunlearn/
├── documents/
│   ├── {tenant_id}/
│   │   ├── {year}/{month}/{day}/{document_id}.{ext}
│   │   └── ...
├── uploads/
│   ├── {tenant_id}/
│   │   ├── images/{user_id}/{filename}
│   │   ├── audio/{user_id}/{filename}
│   │   └── temp/{session_id}/
├── models/
│   ├── {tenant_id}/
│   │   ├── checkpoints/{model_version_id}/
│   │   ├── exports/{model_version_id}/
│   │   └── shards/{model_version_id}/
├── proofs/
│   ├── {tenant_id}/
│   │   ├── certificates/{proof_id}.json
│   │   └── trees/{proof_id}.json
├── exports/
│   ├── {tenant_id}/
│   │   ├── conversations/{export_id}.md
│   │   └── data/{export_id}.json
└── temp/
    └── processing/{worker_id}/
```

---

## 5. Migration Strategy

### 5.1 Alembic Configuration

All migrations are managed via Alembic with the following strategy:

- **Base migration**: Initial schema creation
- **Feature migrations**: Per-domain feature additions
- **Data migrations**: Backfill and transform operations
- **Index operations**: Online index creation (CONCURRENTLY)

### 5.2 Migration Guidelines

- All migrations must be reversible
- Never remove columns without deprecation period
- Use `WITH (ONLINE = ON)` for large tables
- Test migrations against staging with production-sized data
- Zero-downtime migrations via blue/green deployment pattern

---

*This schema is designed for horizontal scalability, tenant isolation, and GDPR compliance. Indexes and partitioning strategies support multi-terabyte workloads.*
