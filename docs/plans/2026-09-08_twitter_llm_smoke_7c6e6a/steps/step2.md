# Step 2: Run seven primary-prefix smokes and commit Git copies

## Scope

- **Caller:** `data_platform/generate_features/smoke_twitter_campaign.py` `main`.
- **Task:** Run a ten-post OpenAI Batch smoke for each of the seven features in YAML order, write objects under the primary `{feature}/smoke/` prefix, and commit the temporary Git copies.
- **Out of scope:** `--smoke-prefix`, a new interrupt CLI flag, production `generate_twitter_features.py`, `*_run_report.md`, pytest, product Python edits, labeling 6,408 rows.

## Files to inspect (read-only)

- `/workspace/data_platform/generate_features/smoke_twitter_campaign.py`
- `/workspace/data_platform/generate_features/configs/twitter/mirrorview_2026-09-07_llm_features_v1.yaml`

## Files allowed to change

- `/workspace/docs/plans/2026-09-08_twitter_llm_smoke_7c6e6a/reports/smoke/is_news_or_opinion/**`
- `/workspace/docs/plans/2026-09-08_twitter_llm_smoke_7c6e6a/reports/smoke/is_political/**`
- `/workspace/docs/plans/2026-09-08_twitter_llm_smoke_7c6e6a/reports/smoke/is_likely_spam/**`
- `/workspace/docs/plans/2026-09-08_twitter_llm_smoke_7c6e6a/reports/smoke/is_self_contained/**`
- `/workspace/docs/plans/2026-09-08_twitter_llm_smoke_7c6e6a/reports/smoke/is_structurally_complete/**`
- `/workspace/docs/plans/2026-09-08_twitter_llm_smoke_7c6e6a/reports/smoke/political_stance/**`
- `/workspace/docs/plans/2026-09-08_twitter_llm_smoke_7c6e6a/reports/smoke/llm_toxicity_tiered/**`

## Files forbidden to change

- Any file under `/workspace/data_platform/`
- Any file under `/workspace/lib/`
- Any file under `/workspace/tests/`
- `/workspace/docs/plans/2026-09-07_generate_twitter_llm_features_e3c91a/**`
- `/workspace/docs/plans/2026-09-07_twitter_sync_preprocess_llm_curate_4a9cd5/**`
- Any committed parquet or csv label file

## Work

Export AWS credentials, then run one feature at a time. Wait for each OpenAI Batch job before starting the next feature. Copy each command log to `/opt/cursor/artifacts/`.

```bash
export AWS_ACCESS_KEY_ID="$LAB_AWS_ACCESS_KEY_ID"
export AWS_SECRET_ACCESS_KEY="$LAB_AWS_ACCESS_KEY_SECRET"
export PYTHONPATH=.
```

Do not pass `--smoke-prefix`. Do not pass a new interrupt flag. Interrupt and resume happens inside the smoke caller only for `is_news_or_opinion`.

```bash
PYTHONPATH=. uv run python data_platform/generate_features/smoke_twitter_campaign.py \
  --campaign-id twitter_2026_09_08_014808_llm_features_v1 \
  --dataset-id twitter_5901767a-e609-46fc-9a17-742516b548f2 \
  --preprocessed-run 2026_09_08-01:48:08 \
  --feature is_news_or_opinion \
  --output-dir docs/plans/2026-09-08_twitter_llm_smoke_7c6e6a/reports/smoke/is_news_or_opinion
```

Repeat with `--feature` and `--output-dir` for `is_political`, `is_likely_spam`, `is_self_contained`, `is_structurally_complete`, `political_stance`, and `llm_toxicity_tiered`.

After each feature, confirm `git branch --show-current` is `cursor/epic-251-255-smoke-generate-seven-llm-8500`, then commit that feature's Git copies. Keep the copies. Do not delete them in this step.

Expected Git files per feature:

- `{feature}_cost_report.json`
- `{feature}_s3_checks.txt`
- `{feature}_resume_evidence.json` only for `is_news_or_opinion`

Do not commit parquet or csv label files.

## Expected stdout (each feature)

```text
smoke_rows=10
full_run_row_count=6408
s3_smoke_output_ok=true
no_batches_prefix_objects=true
```

For `is_news_or_opinion` also:

```text
s3_smoke_resume_evidence_ok=true
```

For the other six also:

```text
resume_evidence_absent=true
```

Exit code 0.

## Pass

- All seven commands exit 0.
- Each cost report has `estimated_full_run_usd_avg` and `estimated_full_run_usd_max`.
- Resume evidence is present only for `is_news_or_opinion`.
- Temporary Git copies are committed and still present.

## Fail

- A command writes `batches/part-*.parquet`.
- A feature other than `is_news_or_opinion` writes `resume_evidence.json`.
- `--smoke-prefix` is passed.
- `--full-run-row-count 6374` is used.
- Product Python changes.
- Phase B production starts.
