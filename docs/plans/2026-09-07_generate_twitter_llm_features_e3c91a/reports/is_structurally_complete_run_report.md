# is_structurally_complete Phase B run report

## Approval

Phase B was approved by the repository owner on parent issue 232 in comment https://github.com/METResearchGroup/mirrorView-task/issues/232#issuecomment-5564895800 (2026-09-07). That comment signs off on Step 1 (PR #238), the seven ten-post smokes, and the aggregate cost.

## Pinned identity

| Field | Value |
|-------|-------|
| Dataset id | `twitter_fba4ddb2-fcf7-4a13-a7cc-0d98db44b547` |
| Preprocessed run | `2026_09_06-19:28:47` |
| Preprocessed row count | 6,374 |
| Campaign id | `twitter_2026_09_06_192847_llm_features_v1` |
| Feature name | `is_structurally_complete` |
| Run id | `twitter_2026_09_06_192847_llm_features_v1:is_structurally_complete` |
| Model id | `gpt-5.4-nano` |
| Batch size | 2,000 |
| Prompt source | `data_platform/generate_features/is_structurally_complete/generate_feature.py` |
| Prompt hash | `1ba4625039f7a7f056943be4d35890fa9483bfe4d51378bccd1bdea0041925bd` |
| Accepted label values | boolean `true` or `false` |
| Label column | `is_structurally_complete` |

## S3 artifacts

| Artifact | URI |
|----------|-----|
| `final.parquet` | `s3://mirrorview-experimental-artifacts/data_platform/data/twitter/twitter_fba4ddb2-fcf7-4a13-a7cc-0d98db44b547/features/twitter_2026_09_06_192847_llm_features_v1/is_structurally_complete/final.parquet` |
| `manifest.json` | `s3://mirrorview-experimental-artifacts/data_platform/data/twitter/twitter_fba4ddb2-fcf7-4a13-a7cc-0d98db44b547/features/twitter_2026_09_06_192847_llm_features_v1/is_structurally_complete/manifest.json` |
| `progress.jsonl` | `s3://mirrorview-experimental-artifacts/data_platform/data/twitter/twitter_fba4ddb2-fcf7-4a13-a7cc-0d98db44b547/features/twitter_2026_09_06_192847_llm_features_v1/is_structurally_complete/progress.jsonl` |
| Feature prefix | `s3://mirrorview-experimental-artifacts/data_platform/data/twitter/twitter_fba4ddb2-fcf7-4a13-a7cc-0d98db44b547/features/twitter_2026_09_06_192847_llm_features_v1/is_structurally_complete/` |
| `batches/part-00000.parquet` | `s3://mirrorview-experimental-artifacts/data_platform/data/twitter/twitter_fba4ddb2-fcf7-4a13-a7cc-0d98db44b547/features/twitter_2026_09_06_192847_llm_features_v1/is_structurally_complete/batches/part-00000.parquet` |
| `batches/part-00001.parquet` | `s3://mirrorview-experimental-artifacts/data_platform/data/twitter/twitter_fba4ddb2-fcf7-4a13-a7cc-0d98db44b547/features/twitter_2026_09_06_192847_llm_features_v1/is_structurally_complete/batches/part-00001.parquet` |
| `batches/part-00002.parquet` | `s3://mirrorview-experimental-artifacts/data_platform/data/twitter/twitter_fba4ddb2-fcf7-4a13-a7cc-0d98db44b547/features/twitter_2026_09_06_192847_llm_features_v1/is_structurally_complete/batches/part-00002.parquet` |
| `batches/part-00003.parquet` | `s3://mirrorview-experimental-artifacts/data_platform/data/twitter/twitter_fba4ddb2-fcf7-4a13-a7cc-0d98db44b547/features/twitter_2026_09_06_192847_llm_features_v1/is_structurally_complete/batches/part-00003.parquet` |

`final.parquet` SHA-256: `76a8a0c83ffff41eb5842cb3581d4014e629baa5afd4f4ae2e073fc928d1939c`

`manifest.json` SHA-256: `4aec69422431046445e1f29603c5506141a523c34fad54cfa8f47f85d64d19b6`

`manifest.json` records `model_id=gpt-5.4-nano` and `expected_row_count=6374`. The campaign writer does not store an `engine_type` field on the manifest. Production used the OpenAI Batch engine only.

`smoke/resume_evidence.json` is absent, as required for this feature.

## Run timing

| Metric | Value |
|--------|-------|
| Wall-clock start (UTC) | `2026-09-07T05:12:07Z` |
| Wall-clock end (UTC) | `2026-09-07T05:31:11Z` |
| Wall-clock hours | 0.32 |
| Throughput | 20,058 rows/hour |
| Resume or reattach events during Phase B | 0 |

## Cost

| Metric | Value |
|--------|-------|
| Smoke estimated full run (avg) | $0.415202 |
| Smoke estimated full run (max) | $0.428651 |
| Actual cost (5 OpenAI batches) | $0.418948 |
| Input tokens | 3,313,052 |
| Output tokens | 140,228 |
| Pricing | Batch API `gpt-5.4-nano`: $0.10/M input, $0.625/M output |

## Label counts

| Label | Count |
|-------|-------|
| `true` | 5994 |
| `false` | 380 |
| **Total in final** | **6,374** |
| `failed_row_count` | 0 |

No `errors.jsonl` was written. Unique `source_record_id` count in `final.parquet` is 6,374.

## Retries and provider batches

| Metric | Value |
|--------|-------|
| Distinct OpenAI batch ids | 5 |
| Parts with more than one provider batch id | 1 (part 0: smoke batch plus full-run batch) |
| `part-00003` rows | 374 |
| Smoke fold on `part-00000` | original smoke `batch_id` and `request_id` preserved |

Part 0 lists two provider batch ids because the ten smoke rows were labeled in Phase A and the remaining 1,990 rows in part 0 were labeled in the first Phase B batch.

## final.parquet completion rule

`final.parquet` was written once every input id was labeled exactly once. `manifest.json` `final_parquet` reports `row_count=6374` and `failed_row_count=0`.

## Watcher milestones

Watcher `--once` on `is_news_or_opinion` after production printed `github_write_skipped=true` and `boundary_crossed=false`. The 10,000-row milestone is absent at 6,374 rows, so no rolling markdown comment body was rendered. The watcher CLI did not write to GitHub.

## Validation results

| Check | Result |
|-------|--------|
| Unique `source_record_id` | pass (6,374) |
| `part-00003` rows | pass (374) |
| Four batch parts `part-00000` through `part-00003` | pass (2,000 / 2,000 / 2,000 / 374) |
| Smoke rows in `part-00000` keep original `batch_id` and `request_id` | pass |
| `final.parquet` SHA-256 matches manifest | pass |
| Accepted `is_structurally_complete` values only | pass |
| Smoke objects remain on S3 | pass |

## OpenAI Batch job ids

5 distinct provider batch ids. The smoke batch id is `batch_6a9e326b262c8190863503ca884c633a`. The first full-run batch id is `batch_6a9e47abfda0819097eefd375190ab56` (part 0 expansion). The last batch id is `batch_6a9e4a8a47508190b49ef7ee9e8eb5f6` (part 3). Full list is in `manifest.json` `batches[].provider_batch_ids`.

## Git smoke copies

Temporary Git copies under `docs/plans/2026-09-07_generate_twitter_llm_features_e3c91a/reports/smoke/` were removed after Phase B. S3 smoke objects under `s3://mirrorview-experimental-artifacts/data_platform/data/twitter/twitter_fba4ddb2-fcf7-4a13-a7cc-0d98db44b547/features/twitter_2026_09_06_192847_llm_features_v1/is_structurally_complete/smoke/` remain.
