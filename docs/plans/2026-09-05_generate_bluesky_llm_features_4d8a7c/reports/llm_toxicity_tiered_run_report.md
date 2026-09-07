# llm_toxicity_tiered Phase B run report

## Approval

Phase B started after explicit chat approval on 2026-09-06 ("Approved, run Phase B"). A comment on the parent campaign issue could not be posted because the GitHub token in this environment has no write scope.

## Pinned identity

| Field | Value |
|-------|-------|
| Dataset id | `bluesky_7e2c4a91-3b5f-4d8e-a6c1-0f9b8d2e5a73` |
| Preprocessed run | `2026_09_03-23:51:30` |
| Preprocessed row count | 200000 |
| Campaign id | `bluesky_2026_09_03_235130_llm_features_v1` |
| Feature name | `llm_toxicity_tiered` |
| Run id | `bluesky_2026_09_03_235130_llm_features_v1:llm_toxicity_tiered` |
| Model id | `gpt-5.4-nano` |
| Batch size | 2000 |
| Prompt path | `data_platform/generate_features/llm_toxicity_tiered/generate_feature.py` |
| Prompt hash (SHA-256) | `1b22e0603119a3360fa9b3370b5157162323b00709fdb0eead1954eca9133c6b` |
| Label field | `toxicity_tier` |
| Accepted values | `low`, `medium`, `high` |

## S3 artifacts

| Object | URI |
|--------|-----|
| final.parquet | `s3://mirrorview-experimental-artifacts/data_platform/data/bluesky/bluesky_7e2c4a91-3b5f-4d8e-a6c1-0f9b8d2e5a73/features/bluesky_2026_09_03_235130_llm_features_v1/llm_toxicity_tiered/final.parquet` |
| manifest.json | `s3://mirrorview-experimental-artifacts/data_platform/data/bluesky/bluesky_7e2c4a91-3b5f-4d8e-a6c1-0f9b8d2e5a73/features/bluesky_2026_09_03_235130_llm_features_v1/llm_toxicity_tiered/manifest.json` |
| progress.jsonl | `s3://mirrorview-experimental-artifacts/data_platform/data/bluesky/bluesky_7e2c4a91-3b5f-4d8e-a6c1-0f9b8d2e5a73/features/bluesky_2026_09_03_235130_llm_features_v1/llm_toxicity_tiered/progress.jsonl` |

## Run timing

| Metric | Value |
|--------|-------|
| Wall clock start (UTC) | 2026-09-06T10:35:09Z |
| Wall clock end (UTC) | 2026-09-06T21:23:13Z |
| Wall clock hours | 10.80 |
| Throughput | 18517 rows/hour |

The campaign CLI ran once in tmux session `phaseb-llm_toxicity_tiered` and exited with code 0. There were no Phase B resume or reattach events.

## Smoke estimate vs actual cost

Phase A smoke (`smoke/cost_report.json` and local `llm_toxicity_tiered_cost_report.json`) used ten posts with `gpt-5.4-nano` Batch pricing at $0.10 per million input tokens and $0.625 per million output tokens.

| Metric | Value |
|--------|-------|
| Smoke avg input tokens per request | 389.7 |
| Smoke avg output tokens per request | 22.0 |
| Estimated full run (average) | $10.544 |
| Estimated full run (max input) | $11.350 |
| Actual input tokens (101 provider batches) | 77452337 |
| Actual output tokens | 4400000 |
| Actual cost | $10.495 |
| Retries (parts with more than one provider batch id, excluding part 0) | 0 |
| Rows with attempt_count > 1 | 0 |
| Error rate | 0% (0 permanently failed ids) |

Part 0 lists two provider batch ids (`batch_6a9cf5c5b3148190ae06abd99c2c932f` from smoke and `batch_6a9d41e67df08190b93ebdff35e0823a` from the first production chunk). That is expected. It is not a retry.

## final.parquet completion rule

`final.parquet` was written once every input id had a label or was recorded as permanently failed. No ids were permanently failed, so `row_count` is 200000 and `failed_row_count` is 0. The sum `row_count + failed_row_count` equals 200000. Failed ids are excluded from the Parquet file and counted only in `manifest.json`.

## Label counts

| toxicity_tier | Count |
|---------------|-------|
| low | 161040 |
| medium | 33346 |
| high | 5614 |

The Perspective API feature `is_toxic_tiered` was not run. No objects exist under that prefix.

## Watcher milestones

The progress watcher ran with `--once` at each poll. Milestone bodies were saved locally because the environment had no GitHub write token. They were not posted as issue comments.

| Boundary rows | Durable rows at milestone | Estimated cost | Active batch | Updated (UTC) |
|---------------|---------------------------|----------------|--------------|---------------|
| 10000 | 10000 | $0.53 | batch_6a9d503db5988190ae7eb820d1a8edf7 | 2026_09_06-11:40:12 |
| 24000 | 24000 | $1.27 | batch_6a9d585636f88190babf556eb585a371 | 2026_09_06-12:11:02 |
| 30000 | 30000 | $1.58 | batch_6a9d5c0cc4948190adea756ef74e52d1 | 2026_09_06-12:31:37 |
| 40000 | 40000 | $2.11 | batch_6a9d63ac1c408190969b31ae0b9a3f11 | 2026_09_06-13:01:34 |
| 50000 | 52000 | $2.74 | batch_6a9d719f2b708190ba3f4d23e0f640b7 | 2026_09_06-14:03:03 |
| 60000 | 62000 | $3.27 | batch_6a9d76b152f08190a450045180501915 | 2026_09_06-14:23:19 |
| 70000 | 72000 | $3.80 | batch_6a9d7dc2bdf481908178fae25dc5797f | 2026_09_06-14:53:42 |
| 80000 | 82000 | $4.32 | batch_6a9d86fd97d88190afe4b5d0d573511e | 2026_09_06-15:34:10 |
| 90000 | 92000 | $4.85 | batch_6a9d90acf06481909621d376ed09f3e0 | 2026_09_06-16:14:39 |
| 100000 | 100000 | $5.27 | batch_6a9d997d8de88190af86bbe12eb94d21 | 2026_09_06-16:55:06 |
| 110000 | 110000 | $5.80 | batch_6a9da7677aa48190a9a5be215f24ca7c | 2026_09_06-17:55:52 |
| 120000 | 122000 | $6.43 | batch_6a9db1849f9c8190bd873aea9198e6ca | 2026_09_06-18:36:21 |
| 130000 | 130000 | $6.85 | batch_6a9db9bb45488190b729069518411c69 | 2026_09_06-19:06:45 |
| 140000 | 142000 | $7.49 | batch_6a9dc0134764819097269bc76ac6196b | 2026_09_06-19:37:10 |
| 150000 | 156000 | $8.22 | batch_6a9dc5729b0881908f939a4cfd547a76 | 2026_09_06-19:57:25 |
| 160000 | 162000 | $8.54 | batch_6a9dc7ff84748190964258c842eae308 | 2026_09_06-20:07:33 |
| 170000 | 172000 | $9.07 | batch_6a9dcc7c05e081909596e63094137c5b | 2026_09_06-20:27:57 |
| 180000 | 182000 | $9.60 | batch_6a9dd14b8cc08190900dd44286f28b5f | 2026_09_06-20:48:11 |
| 190000 | 192000 | $10.12 | batch_6a9dd558f7a08190aad7ccb33c18f98e | 2026_09_06-21:08:25 |
| 200000 | 200000 | $10.54 | idle | 2026_09_06-21:23:56 |

## Validation results

All checks passed (24/24) on 2026-09-06 after download to `/tmp/phaseb/llm_toxicity_tiered/`.

| Check | Result |
|-------|--------|
| Q44 columns | PASS |
| Row count 200000 (failed_row_count 0) | PASS |
| manifest.final_parquet.row_count match | PASS |
| Unique source_record_id | PASS |
| Single run_id | PASS |
| Accepted toxicity_tier values | PASS |
| final.parquet SHA-256 vs manifest | PASS |
| 100 batch objects part-00000..part-00099 | PASS |
| Batch row sum 200000 | PASS |
| part-00000 smoke rows unchanged | PASS |
| part-00000 has 1990 new rows | PASS |
| No objects under campaigns/, shards/, final/ | PASS |
| active_openai_batch.json absent | PASS |
| Batch objects tagged intermediate-artifact=true | PASS |
| final.parquet, manifest.json, progress.jsonl untagged | PASS |
| progress.jsonl: 100 batch lines, 1 final line | PASS |
| No retry parts beyond part 0 | PASS |
| No attempt_count > 1 | PASS |
| is_toxic_tiered prefix empty | PASS |
| Spot batch SHA-256 (parts 0, 50, 99) | PASS |

## OpenAI Batch job ids

101 unique provider batch ids across 100 parts (part 0 includes the smoke batch id). Full list is in `manifest.json` under each batch entry's `provider_batch_ids` field.
