# Step 2: Run seven primary-prefix smokes and commit Git copies

## Scope

- **Caller:** `data_platform/generate_features/smoke_twitter_campaign.py` `main`.
- **Task:** Run a ten-post OpenAI Batch smoke for each of the seven features in YAML order, write objects under the primary `{feature}/smoke/` prefix, and commit the temporary Git copies.
- **Out of scope:** `--smoke-prefix`, a new interrupt CLI flag, production `generate_twitter_features.py`, `*_run_report.md`, pytest, product Python edits, labeling 6,374 rows.

## Files to inspect (read-only)

- `/workspace/data_platform/generate_features/smoke_twitter_campaign.py`
- `/workspace/data_platform/generate_features/configs/twitter/mirrorview_2026-09-05_llm_features_v1.yaml`
- `/workspace/docs/plans/2026-09-07_generate_twitter_llm_features_e3c91a/campaign_contract.md`

## Files allowed to change

- `/workspace/docs/plans/2026-09-07_generate_twitter_llm_features_e3c91a/reports/smoke/is_news_or_opinion/**`
- `/workspace/docs/plans/2026-09-07_generate_twitter_llm_features_e3c91a/reports/smoke/is_political/**`
- `/workspace/docs/plans/2026-09-07_generate_twitter_llm_features_e3c91a/reports/smoke/is_likely_spam/**`
- `/workspace/docs/plans/2026-09-07_generate_twitter_llm_features_e3c91a/reports/smoke/is_self_contained/**`
- `/workspace/docs/plans/2026-09-07_generate_twitter_llm_features_e3c91a/reports/smoke/is_structurally_complete/**`
- `/workspace/docs/plans/2026-09-07_generate_twitter_llm_features_e3c91a/reports/smoke/political_stance/**`
- `/workspace/docs/plans/2026-09-07_generate_twitter_llm_features_e3c91a/reports/smoke/llm_toxicity_tiered/**`

## Files forbidden to change

- Any file under `/workspace/data_platform/`
- Any file under `/workspace/lib/`
- Any file under `/workspace/tests/`
- `/workspace/docs/plans/2026-09-07_generate_twitter_llm_features_e3c91a/plan.md`
- `/workspace/docs/plans/2026-09-07_generate_twitter_llm_features_e3c91a/campaign_contract.md`
- `/workspace/docs/plans/2026-09-07_generate_twitter_llm_features_e3c91a/steps/step1.md`
- `/workspace/docs/plans/2026-09-07_generate_twitter_llm_features_e3c91a/steps/step2.md`
- `/workspace/docs/plans/2026-09-07_generate_twitter_llm_features_e3c91a/steps/step3.md`
- `/workspace/docs/plans/2026-09-07_generate_twitter_llm_features_e3c91a/reports/*_run_report.md`
- Any committed parquet or csv label file

## Work

Export AWS credentials, then run one feature at a time. Wait for each OpenAI Batch job before starting the next feature. Copy each command log to `/opt/cursor/artifacts/`.

```bash
export AWS_ACCESS_KEY_ID="$LAB_AWS_ACCESS_KEY_ID"
export AWS_SECRET_ACCESS_KEY="$LAB_AWS_ACCESS_KEY_SECRET"
```

Do not pass `--smoke-prefix`. Do not pass a new interrupt flag. Interrupt and resume happens inside the smoke caller only for `is_news_or_opinion`.

```bash
PYTHONPATH=. uv run python data_platform/generate_features/smoke_twitter_campaign.py \
  --campaign-id twitter_2026_09_06_192847_llm_features_v1 \
  --dataset-id twitter_fba4ddb2-fcf7-4a13-a7cc-0d98db44b547 \
  --preprocessed-run 2026_09_06-19:28:47 \
  --feature is_news_or_opinion \
  --output-dir docs/plans/2026-09-07_generate_twitter_llm_features_e3c91a/reports/smoke/is_news_or_opinion
```

Repeat with `--feature` and `--output-dir` for `is_political`, `is_likely_spam`, `is_self_contained`, `is_structurally_complete`, `political_stance`, and `llm_toxicity_tiered`.

After each feature, confirm `git branch --show-current` is `cursor/epic-232-234-smoke-generate-seven-llm-features-8500`, then commit that feature's Git copies. Keep the copies. Do not delete them in this step.

Expected Git files per feature:

- `{feature}_cost_report.json`
- `{feature}_s3_checks.txt`
- `{feature}_resume_evidence.json` only for `is_news_or_opinion`

Do not commit parquet or csv label files.

## Expected stdout (each feature)

```text
smoke_rows=10
full_run_row_count=6374
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
- Product Python changes.
- Phase B production starts.
