# VeriUnlearn Demo Assets

Static, version-controllable JSON artifacts that let a new user or judge explore
the VeriUnlearn platform without running the heavy ML pipeline. These mirror the
canonical entities defined in `infra/scripts/seed_demo_data.py` and the responses
returned by the live API.

## Folders

| Folder | Files | Maps to API endpoint |
| --- | --- | --- |
| `datasets/` | `cifar10.json`, `cifar100.json`, `tiny_imagenet.json` | `GET /api/v1/datasets` |
| `models/` | `resnet18.json`, `resnet50.json`, `vit_b16.json` | `GET /api/v1/models` |
| `deletion-requests/` | `sample-requests.json` | `GET /api/v1/unlearning/requests` |
| `verification-certificates/` | `sample-certificates.json` | `GET /api/v1/certificates` |
| `benchmark-reports/` | `sample-report.json` | `GET /api/v1/benchmarks` |

## Regenerating

All JSON files are produced deterministically by the generator script:

```bash
python scripts/generate_demo_assets.py
```

The script uses only the Python standard library and a fixed random seed, so
output is reproducible across machines and commits.

## Entity reference

- **Datasets**: `cifar10` (10 classes, 50k samples, 168MB), `cifar100` (100
  classes, 50k, 169MB), `tiny_imagenet` (200 classes, 100k, 237MB).
- **Models**: `resnet18` (11.2M params), `resnet50` (25.6M), `vit_b16` (86.6M),
  all PyTorch, Apache-2.0, LoRA adapters supported.
- **Algorithms**: `sisa`, `influence`, `certified`, `hybrid`.
- **Benchmark metrics**: `accuracy`, `f1_macro`, `mia_success_rate`,
  `privacy_leakage`, `latency_ms`, `deletion_fraction`, `forget_rate`,
  `model_inversion_resistance`.
- **Certificates**: merkle/root hashes over a 7-step proof chain
  (`Initialize unlearning request` → `Load model checkpoint` →
  `Apply unlearning algorithm` → `Verify parameter delta` →
  `Compute inclusion test` → `Generate zero-knowledge proof` →
  `Submit to certificate chain`).
