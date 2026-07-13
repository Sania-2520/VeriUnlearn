# VeriUnlearn API Reference

## ML Engine Endpoints (`/`)

### Unlearning
| Method | Path | Description |
|--------|------|-------------|
| POST | `/unlearn` | Execute unlearning via hybrid controller |
| POST | `/unlearn/e2e` | End-to-end unlearning pipeline |
| GET | `/unlearn/e2e/history` | E2E deletion history |
| GET | `/unlearn/e2e/stats` | E2E pipeline statistics |

### Proof & Verification
| Method | Path | Description |
|--------|------|-------------|
| POST | `/proof/generate` | Generate Merkle proof |
| POST | `/proof/verify` | Verify signature |
| POST | `/proof/generate-zksnark` | Generate zk-SNARK proof |
| POST | `/proof/verify-zksnark` | Verify zk-SNARK proof |
| POST | `/certificate` | Generate deletion certificate |

### Evaluation
| Method | Path | Description |
|--------|------|-------------|
| POST | `/evaluate/mia` | Membership inference attack |
| POST | `/evaluate/privacy` | Privacy evaluation report |

### Training
| Method | Path | Description |
|--------|------|-------------|
| POST | `/train/lora` | LoRA fine-tuning |
| GET | `/train/checkpoints` | List training checkpoints |
| POST | `/train/checkpoints/{id}/load` | Load checkpoint |

### Adapter Lifecycle
| Method | Path | Description |
|--------|------|-------------|
| POST | `/adapters/register` | Register new adapter version |
| POST | `/adapters/activate` | Activate adapter version |
| POST | `/adapters/deactivate` | Deactivate adapter version |
| POST | `/adapters/mark-failed` | Mark version as failed |
| POST | `/adapters/{name}/rollback` | Rollback to previous version |
| GET | `/adapters` | List all adapters |
| GET | `/adapters/{name}/versions` | Get version history |
| GET | `/adapters/{name}/active` | Get active version |
| POST | `/adapters/canary/setup` | Setup canary deployment |
| POST | `/adapters/{name}/canary/promote` | Promote canary |
| GET | `/adapters/{name}/routing` | Get routing rule |
| POST | `/adapters/metrics` | Record request metrics |
| GET | `/adapters/{name}/latency` | Get latency stats |
| GET | `/adapters/{name}/health` | Get adapter health |

### Explainability
| Method | Path | Description |
|--------|------|-------------|
| POST | `/explain/samples` | Explain individual samples |
| POST | `/explain/features` | Global feature importance |
| POST | `/explain/compare` | Before/after unlearning comparison |
| POST | `/explain/privacy-heatmap` | Privacy risk heatmap |
| POST | `/explain/drift` | Model drift analysis |
| GET | `/explain/methods` | List available methods |

### Continual Learning
| Method | Path | Description |
|--------|------|-------------|
| GET | `/continual/stats` | Continual learning statistics |
| POST | `/continual/tasks` | Register new task |
| GET | `/continual/tasks` | List tasks |
| GET | `/continual/tasks/{id}` | Get task details |
| POST | `/continual/samples` | Record training sample |
| POST | `/continual/ewc/estimate` | Estimate EWC Fisher |
| GET | `/continual/ewc/state` | EWC state |
| POST | `/continual/replay/sample` | Sample from replay buffer |
| GET | `/continual/replay/stats` | Replay buffer stats |
| POST | `/continual/drift/record` | Record drift metric |
| GET | `/continual/drift/alerts` | Get drift alerts |
| GET | `/continual/drift/state` | Current drift state |

### Benchmarks
| Method | Path | Description |
|--------|------|-------------|
| POST | `/benchmarks/run` | Run benchmark suite |
| GET | `/benchmarks/summary` | Benchmark summary |
| GET | `/benchmarks/results` | All benchmark results |
| GET | `/benchmarks/config` | Benchmark configuration |

### Inference
| Method | Path | Description |
|--------|------|-------------|
| POST | `/inference/generate` | Text generation |
| POST | `/inference/generate/stream` | Streaming generation |
| POST | `/inference/batch` | Batch generation |
| POST | `/inference/adapters/load` | Load LoRA adapter |
| POST | `/inference/adapters/unload` | Unload adapter |
| GET | `/inference/adapters` | List loaded adapters |
| GET | `/inference/metrics` | Inference metrics |
| GET | `/inference/health` | Inference health |

### RAG
| Method | Path | Description |
|--------|------|-------------|
| POST | `/rag/documents/ingest` | Ingest document |
| GET | `/rag/documents` | List documents |
| GET | `/rag/documents/{id}` | Get document |
| DELETE | `/rag/documents/{id}` | Delete document |
| POST | `/rag/search` | Semantic search |

### Model Registry
| Method | Path | Description |
|--------|------|-------------|
| POST | `/registry/versions` | Register model version |
| GET | `/registry/versions` | List all versions |
| GET | `/registry/versions/{name}` | List model versions |
| GET | `/registry/versions/{name}/{id}` | Get version |
| POST | `/registry/versions/{name}/{id}/rollback` | Rollback version |
| POST | `/registry/versions/{name}/{id}/verify` | Verify integrity |

### System
| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Engine health check |
| GET | `/controller/health` | Controller health |
| GET | `/controller/metrics` | Controller metrics |
| GET | `/mlflow/experiment-stats` | MLflow stats |
| GET | `/mlflow/runs` | List MLflow runs |

## Backend API (`/api/v1`)

| Prefix | Description |
|--------|-------------|
| `/auth` | Authentication & registration |
| `/auth/api-keys` | API key management |
| `/users` | User management |
| `/chat` | Chat sessions & messaging |
| `/providers` | AI provider configuration |
| `/rag` | RAG document management |
| `/memory` | Memory entries |
| `/unlearning` | Unlearning requests & jobs |
| `/verify` | Proof verification |
| `/security` | Security assessments |
| `/audit` | Audit log |
| `/compliance` | Compliance & webhooks |
| `/admin` | Admin settings |
| `/explain` | Explainability proxy |

## Architecture

```
┌──────────────┐     ┌──────────────────┐     ┌──────────────┐
│   Frontend   │────▶│   Backend API    │────▶│  ML Engine   │
│  (Next.js)   │     │  (FastAPI)       │     │  (FastAPI)   │
└──────────────┘     └──────────────────┘     └──────────────┘
                            │                        │
                            ▼                        ▼
                     ┌──────────────┐     ┌──────────────────┐
                     │  PostgreSQL  │     │   MLflow         │
                     │  (SQLAlchemy)│     │   (experiments)  │
                     └──────────────┘     └──────────────────┘
```

## Core ML Modules

- **Unlearning**: SISA, Influence Functions, Certified Removal, Hybrid Adaptive Controller
- **Verification**: Merkle Tree, Ed25519 Signatures, zk-SNARKs, Privacy Evaluation
- **Training**: LoRA Trainer, Model Registry, RAG Pipeline, Conversational Pipeline
- **Explainability**: SHAP, LIME, Integrated Gradients, Feature Attribution, Drift Detection
- **Continual Learning**: EWC, Replay Buffer, Drift Detection
- **Lifecycle**: Adapter Versioning, Canary Deployments, A/B Testing, Rollback
- **Evaluation**: MIA, Privacy, Benchmark Suite, Quality Metrics
