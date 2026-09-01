# Bluesky data-platform smoke (2026-08-28)

End-to-end smoke of `data_platform/` using `data_platform/ingestion/configs/bluesky/smoke.yaml`.

The pipeline ran ingest, preprocess, feature generation, and curate. Artifacts are copied here because `data_platform/data/` is gitignored.

- Results: [`RESULTS.md`](./RESULTS.md)
- Operator notes and gotchas: [`NOTES.md`](./NOTES.md)
- Configs used: [`smoke.yaml`](./smoke.yaml), [`curate_mirrorview.yaml`](./curate_mirrorview.yaml)
- Stage logs: [`run_logs/`](./run_logs/)
- Dataset copy: [`data/bluesky/bluesky_c0ffee00-0000-4000-8000-000000000100/`](./data/bluesky/bluesky_c0ffee00-0000-4000-8000-000000000100/)

## Run

From the repository root:

```bash
PYTHONPATH=. uv run python data_platform/ingestion/sync_bluesky.py \
  --config data_platform/ingestion/configs/bluesky/smoke.yaml

PYTHONPATH=. uv run python data_platform/preprocessing/preprocess_bluesky.py \
  --dataset-id bluesky_c0ffee00-0000-4000-8000-000000000100

PYTHONPATH=. uv run python data_platform/generate_features/generate_bluesky_features.py \
  --dataset-id bluesky_c0ffee00-0000-4000-8000-000000000100 --batch-size 64

PYTHONPATH=. uv run python data_platform/curate/curate_bluesky.py \
  --dataset-id bluesky_c0ffee00-0000-4000-8000-000000000100 --config mirrorview.yaml
```

Operator runbook: [`docs/runbooks/HOW_TO_RUN_DATA_INGESTION.md`](../../docs/runbooks/HOW_TO_RUN_DATA_INGESTION.md).
Architecture: [`docs/runbooks/DATA_INGESTION_PIPELINE_ARCHITECTURE.md`](../../docs/runbooks/DATA_INGESTION_PIPELINE_ARCHITECTURE.md).
