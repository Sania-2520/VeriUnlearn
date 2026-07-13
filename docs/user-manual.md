# User Manual — VeriUnlearn

## Getting Started

1. **Register** at `/auth/register`
2. **Verify** your email
3. **Login** with your credentials
4. **Enable MFA** in Settings for enhanced security
5. **Create an API key** for programmatic access

## Key Features

### Chat
- Conversational AI with RAG-powered context
- Upload documents for knowledge base augmentation
- Export chat history as JSON/PDF

### Machine Unlearning
- Submit deletion requests with GDPR/CMM/DPDP regulatory citation
- Choose algorithm (SISA, Influence, Certified, Hybrid)
- Generate cryptographic proof of deletion
- Verify proof via certificate chain

### LoRA Adapters
- Register fine-tuned LoRA adapters
- Version adapters with rollback support
- Canary deployment for gradual rollout
- Monitor latency, error rates, and health

### Explainability
- SHAP / LIME / Integrated Gradients analysis
- Privacy heatmaps showing data influence
- Drift detection between model versions
- Counterfactual explanations

### Continual Learning
- Monitor model drift in production
- Automatic EWC regularization
- Replay buffer for knowledge retention
- Configure drift thresholds

### Benchmarks
- Run unlearning benchmark suite
- Compare algorithms across datasets
- Export results as CSV/JSON
- View leaderboards

### Monitoring
- Real-time dashboards (Grafana)
- GPU utilization tracking
- API latency monitoring
- Prometheus metrics at `/metrics`

## Keyboard Shortcuts

| Shortcut | Action |
|---|---|
| `Ctrl+K` | Quick search |
| `Ctrl+Enter` | Send message |
| `Ctrl+Shift+N` | New chat session |
| `Escape` | Close modal |

## Troubleshooting

See `docs/troubleshooting-guide.md` for common issues and solutions.
