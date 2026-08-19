# Phase 6 — Security Evaluation, Privacy Benchmarking & Research Benchmark Suite

**VeriUnlearn** — reproducible, publication-quality experimental results for verifiable machine unlearning.

Phase 6 adds a full research layer on top of the Phases 1–5 codebase: a non-destructive 6-method benchmark engine, a four-family attack suite, a versioned experiment manager, a performance profiler, an IEEE-ready research metrics calculator, and CSV/Excel/JSON report exports. All existing Phases 1–5 code is untouched; everything here is additive.

---

## 1. Newly Created Files

### Backend — services
| File | Purpose |
|---|---|
| `backend/app/services/benchmark_engine.py` | Non-destructive 6-method benchmark (original, full retrain, SISA, influence, certified, VeriUnlearn) with utility, cost, privacy metrics; persists rows + profiler timings |
| `backend/app/services/experiments.py` | Experiment manager: create, version, environment capture, history, compare |
| `backend/app/services/research_metrics.py` | Forget Quality Score, Privacy Gain, Knowledge Retention, Accuracy Drop, Utility Loss, Deletion Efficiency, Verification Overhead, Compliance Readiness; LaTeX + CSV rendering |
| `backend/app/services/profiler.py` | Performance profiler: psutil CPU/RAM/disk sampling, timed contexts, per-metric persistence, API latency hook |
| `backend/app/services/attacks.py` | Attack engine (rewritten, additive): full MIA metrics, model inversion, data extraction, poisoning suite (backdoor/label_flip/gradient) + backward-compatible `backdoor_persistence` |
| `backend/app/services/reporting.py` | Research report generator: benchmark DataFrame → CSV / JSON / Excel (openpyxl) |

### Backend — API, schemas, repositories, tests
| File | Purpose |
|---|---|
| `backend/app/api/v1/research.py` | All Phase 6 endpoints (see §8) |
| `backend/app/schemas/research.py` | Request schemas with validation (bounds on sample sizes, fractions, seeds) |
| `backend/app/repositories/research_repo.py` | Repositories for the 6 new tables |
| `backend/tests/test_phase6.py` | 11 tests: benchmark, attacks, metrics, experiments, exports |

### Frontend (new `/research` section)
| File | Purpose |
|---|---|
| `frontend/app/(app)/research/layout.tsx` | Sub-navigation tabs (Dashboard, Benchmark, Experiments, Attack Suite, Performance) |
| `frontend/app/(app)/research/page.tsx` | Research dashboard: security posture, privacy matrix, recent experiments |
| `frontend/app/(app)/research/benchmark/page.tsx` | Run benchmark, persisted results, radar + bar charts, CSV/JSON/Excel exports |
| `frontend/app/(app)/research/experiments/page.tsx` | Experiment manager: create, list, version |
| `frontend/app/(app)/research/experiments/[id]/page.tsx` | Experiment detail: environment, parameters, version history, benchmark bars |
| `frontend/app/(app)/research/attacks/page.tsx` | Attack suite: MIA stages, inversion, extraction, poisoning charts |
| `frontend/app/(app)/research/performance/page.tsx` | Live system metrics + time-series charts (8s auto-refresh) |

---

## 2. Modified Files (all additive)

| File | Change |
|---|---|
| `backend/app/db/models.py` | Added 6 tables: `experiments`, `benchmark_results`, `attack_results`, `performance_metrics`, `privacy_scores`, `experiment_history` |
| `backend/app/repositories/__init__.py` | Export new repositories |
| `backend/app/schemas/__init__.py` | Export new schemas |
| `backend/app/api/v1/router.py` | Registered `research` router |
| `backend/requirements.txt` | Added `psutil`, `openpyxl` |
| `frontend/app/(app)/layout.tsx` | Added “Research Hub” nav item |

No existing API, endpoint, or Phases 1–5 behavior was changed or removed.

---

## 3. Database Migrations

`backend/alembic/versions/e3bb87e588e3_phase6_research_benchmark_suite.py` — creates exactly the 6 new tables:

```
experiments, benchmark_results, attack_results, performance_metrics, privacy_scores, experiment_history
```

Apply with:

```bash
cd backend
../.venv/Scripts/python -m alembic upgrade head
```

Verified incremental: it depends on the Phase 5 head (`203c60186717`) and only adds new tables (no alters/drops).

---

## 4. Benchmark Framework Documentation

### Design
`BenchmarkEngine` (SOLID: engine composes SISA / Influence / Certified services via their public interfaces, persists through `BenchmarkRepository`).

**Non-destructive by construction.** Every method operates on in-memory shard clones loaded from persisted weights; the production model's DB rows and weight files are never mutated. This makes benchmarking safe against a live deployment.

### Methods compared
| Method | Operation |
|---|---|
| `original` | Untouched model — baseline |
| `full_retrain` | Retrain every shard from scratch (in-memory) |
| `sisa` | Retrain only affected shards (selective) |
| `influence` | First-order influence gradient scrub on in-memory clones |
| `certified` | Newton-step certified removal with provable bound |
| `veriunlearn` | Certified removal + full verification-engine run (overhead captured) |

### Metrics per row
Utility: accuracy, precision, recall, F1. Cost: deletion/training seconds, inference latency (ms). Privacy/security: MIA AUC before/after, privacy gain, forgetting score, recovery rate. Derived: utility loss, knowledge retention, deletion efficiency, verification seconds. `certified_bound` on certified rows.

### Reproducibility
Fixed `seed` (default 42) drives a `numpy.default_rng` permutation for delete/holdout splits; MIA probes use derived seeds (`seed+1…5`). Experiment linkage via `experiment_id` captures parameters + environment.

---

## 5. Security Evaluation Documentation

### Membership Inference (`POST /attack/mia`)
Confidence-separation attack scored with AUC plus accuracy/precision/recall/F1, **privacy leakage** (AUC − 0.5), and **membership confidence** (mean posterior). Accepts `deleted_record_ids` to probe original → post-unlearning → post-verification stages.

### Model Inversion (`POST /attack/inversion`)
Gradient-ascent reconstruction of a prototypical member of a target class; reports reconstruction error, **information leakage**, and **similarity score** vs. a class prototype.

### Data Extraction (`POST /attack/extraction`)
Given `deleted_record_ids`, checks whether tombstoned records are still recoverable via embeddings, vectors, metadata, or served text. Text channel counts **served** text (tombstones are excluded from queries), not stored text — a deletion that keeps records for audit does not count as leakage.

### Poisoning Suite (`POST /attack/poisoning`)
Simulates `backdoor` (trigger feature), `label_flip`, and `gradient` poisoning on a shard, unlearns the poisoned rows, and reports: trigger-fire rate before/after, **persistence ratio**, **detection rate**, **removal success**, **robustness score**, **residual influence**.

### Ethics
All attacks run against synthetic or locally-seeded benchmark data (e.g. Adult Census with synthesized PII). No real personal data is used; results are aggregated metrics only.

---

## 6. Experiment Workflow & Reproducibility Guide

1. **Create** `POST /experiments` with `name`, `seed`, `parameters`, optional `dataset_id` — the service snapshots environment (python, key package versions, platform, CPU count).
2. **Run** `POST /benchmark/run` with `experiment_id` — the experiment transitions to `running`, rows persist, then `completed` with a `result_summary`.
3. **Version** `POST /experiments/{id}/version` — creates a new version row with a fresh `version` counter and (optionally) new parameters; history is preserved in `experiment_history`.
4. **Compare** `POST /experiments/compare` (≥2 ids) — side-by-side result summaries.
5. **Export** `GET /benchmark/export?format=csv|json|xlsx` — IEEE-ready tables.

Reproducibility guarantees: seed control everywhere, environment snapshot, dataset/model version linkage, immutable experiment history, and all benchmark rows persisted with timestamps.

---

## 7. Performance Analysis Documentation

`PerformanceProfiler` samples process + system CPU, RAM, and disk via `psutil`, persists samples as `performance_metrics`, and provides:
- **Timed contexts** (`@timed` / `record`) used across benchmark methods (`benchmark.<method>.deletion` series).
- **Live snapshot** for the `/metrics/system` endpoint.

Documented bottleneck: MIA AUC probes and per-method evaluations are O(shards × eval_size) — acceptable for research-scale models; see §13.

---

## 8. API Documentation

All endpoints under `/api/v1`, JWT-protected, with validation + structured logging.

| Method | Path | Description |
|---|---|---|
| POST | `/benchmark/run` | Run full 6-method benchmark (non-destructive) |
| GET | `/benchmark/results` | Persisted benchmark rows (optional `method` filter) |
| GET | `/benchmark/history` | Distinct benchmark runs grouped by dataset/experiment |
| GET | `/benchmark/export` | CSV / JSON / XLSX download |
| POST | `/attack/mia` | Membership-inference report (multi-stage) |
| POST | `/attack/inversion` | Model inversion simulator |
| POST | `/attack/extraction` | Deleted-knowledge extraction test |
| POST | `/attack/poisoning` | Poisoning/backdoor/label/gradient suite |
| GET | `/attack/results` | Persisted attack results (optional `model_id` filter) |
| GET | `/metrics/system` | Live + persisted system resource metrics |
| GET | `/metrics/privacy` | Research metrics matrix + compliance readiness + LaTeX table |
| GET | `/metrics/security` | Aggregated attack outcomes (MIA AUC, poisoning persistence, extraction rate) |
| POST | `/experiments` | Create experiment |
| GET | `/experiments` | List experiments |
| GET | `/experiments/{id}` | Experiment detail + history + benchmark rows |
| POST | `/experiments/{id}/version` | Branch a new version |
| POST | `/experiments/compare` | Side-by-side comparison |

OpenAPI docs auto-generated at `/docs` (Swagger) and `/redoc`.

---

## 9. Testing Instructions & CI Integration

```bash
cd backend
../.venv/Scripts/python -m pytest tests -q        # full suite: 50 tests (39 prior + 11 Phase 6)
```

Phase 6 coverage: `test_phase6.py` — benchmark run + persistence, MIA metrics, inversion, extraction, poisoning, research metrics matrix, experiment create/version/history, CSV/JSON/XLSX exports.

CI (`.github/workflows/ci.yml`) runs `python -m pytest tests -q` on push/PR — the benchmark suite is therefore exercised on every change.

Frontend: `cd frontend && npm run build` (all new pages type-check and lint).

---

## 10. Manual Experiment Guide

1. Upload a dataset → train a model (Phases 1–2 flow).
2. **Research Hub → Experiments → New experiment** (set a seed, attach the dataset).
3. **Benchmark tab** → pick the dataset + experiment → Run. Watch the 6-method table, radar chart, and persisted rows.
4. **Attack Suite** → select the model → run MIA, inversion, extraction, poisoning; compare verdicts.
5. **Performance tab** → watch live CPU/RAM/disk samples accumulate every 8s.
6. **Dashboard tab** → confirm forget-quality matrix, compliance readiness, and security posture update.
7. **Experiments → Open** → inspect environment snapshot, parameters, version history, and benchmark bars.
8. **Benchmark tab → CSV/JSON/Excel** → download the export for the paper.

---

## 11. IEEE-Ready Benchmark Tables & Figures

- **Table**: `GET /metrics/privacy` returns `latex_table` — a ready-to-paste LaTeX `booktabular` of methods × metrics (forget quality, privacy gain, retention, accuracy drop, utility loss, deletion efficiency, verification overhead). CSV equivalent via the same endpoint or `ResearchMetricsCalculator.to_csv`.
- **Figures** (frontend, exportable): accuracy/deletion bar chart, research-metric radar, MIA stage AUC bars, poisoning persistence bars, system time-series lines.
- Every figure renders from persisted data with fixed seeds → reproducible across runs.

---

## 12. CSV & Excel Export Formats

`GET /benchmark/export?format=csv|json|xlsx`

- **CSV** (`benchmark-results.csv`): one row per method × run — `method,dataset_id,model_id,deleted_records,eval_records,accuracy,precision,recall,f1,deletion_seconds,training_seconds,utility_loss,knowledge_retention,forgetting_score,privacy_gain,recovery_rate,mia_auc_before,mia_auc_after,deletion_efficiency,verification_seconds,certified_bound,created_at`.
- **Excel** (`benchmark-results.xlsx`): same columns via openpyxl.
- **JSON** (`benchmark-results.json`): full records including nested metrics dict.

---

## 13. Known Limitations

1. **In-memory benchmark scale** — methods are evaluated on the persisted shard clones; very large shards/eval sizes are memory-bound. `eval_size` capped at 2000.
2. **MIA is confidence-based** — no shadow-model training; AUC separation of deleted vs. live confidence is a first-order proxy (documented as such in the code).
3. **Recovery rate is fixed at 0.0** — true extraction probing requires an LLM/embedding-level harness (deferred; the metric slot is wired for Phase 7+).
4. **Verification overhead measured on one run** — the `veriunlearn` row runs the verification engine once; variance across runs is not yet aggregated.
5. **Performance series are process-local per host** — samples persist, but the live endpoint reflects the current process only.
6. **No GPU metrics yet** — profiler covers CPU/RAM/disk; GPU counters are a documented extension point.

---

## 14. Extension Points for Phase 7 (Compliance Dashboard, Deployment, Monitoring, Admin)

Not implemented now — integration hooks only:

1. **Compliance dashboard wiring** — `ResearchMetricsCalculator.compliance_readiness()` already returns a weighted composite (resolution, certificate integrity, verification health, audit-chain intact); Phase 7 can surface it directly in the compliance UI and export it to the audit trail.
2. **Benchmark-triggered monitoring** — `performance_metrics` rows are keyed by `experiment_id` and `metric`; production monitoring can alert on `benchmark.*.deletion` latency regressions.
3. **Admin experiments** — `ExperimentRepository` and the service layer are ready for admin-only experiment management + quota enforcement; no admin scoping added yet.
4. **Deployment** — the non-destructive benchmark engine is safe to run inside a deployed container (documented above); Docker/CI can add a nightly benchmark job that posts results to `/benchmark/run`.
5. **Privacy score history** — `privacy_scores` persist per-method matrices on each `/metrics/privacy` call, giving Phase 7 a time-series of compliance/privacy readiness for trend charts.
6. **Recovery-rate harness** — the `recovery_rate` metric field is pre-wired in every benchmark row; a Phase 7+ embedding-extraction harness can fill it without schema changes.
