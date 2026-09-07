# is_self_contained Phase B run report

## Approval

Phase B was approved by the repository owner on parent issue 232 in comment https://github.com/METResearchGroup/mirrorView-task/issues/232#issuecomment-5564895800 (2026-09-07). That comment signs off on Step 1 (PR #238), the seven ten-post smokes, and the aggregate cost.

## Pinned identity

| Field | Value |
|-------|-------|
| Dataset id | `twitter_fba4ddb2-fcf7-4a13-a7cc-0d98db44b547` |
| Preprocessed run | `2026_09_06-19:28:47` |
| Preprocessed row count | 6,374 |
| Campaign id | `twitter_2026_09_06_192847_llm_features_v1` |
| Feature name | `is_self_contained` |
| Run id | `twitter_2026_09_06_192847_llm_features_v1:is_self_contained` |
| Model id | `gpt-5.4-nano` |
| Batch size | 2,000 |
| Prompt source | `data_platform/generate_features/is_self_contained/generate_feature.py` |
| Prompt hash | `73a5f17c6a3b6264b07168af7f6d24561a884df1ecfbc65764a111fae3045d7c` |
| Accepted label values | boolean `true` or `false` |
| Label column | `is_self_contained` |

## S3 artifacts

| Artifact | URI |
|----------|-----|
| `final.parquet` | `s3://mirrorview-experimental-artifacts/data_platform/data/twitter/twitter_fba4ddb2-fcf7-4a13-a7cc-0d98db44b547/features/twitter_2026_09_06_192847_llm_features_v1/is_self_contained/final.parquet` |
| `manifest.json` | `s3://mirrorview-experimental-artifacts/data_platform/data/twitter/twitter_fba4ddb2-fcf7-4a13-a7cc-0d98db44b547/features/twitter_2026_09_06_192847_llm_features_v1/is_self_contained/manifest.json` |
| `progress.jsonl` | `s3://mirrorview-experimental-artifacts/data_platform/data/twitter/twitter_fba4ddb2-fcf7-4a13-a7cc-0d98db44b547/features/twitter_2026_09_06_192847_llm_features_v1/is_self_contained/progress.jsonl` |
| Feature prefix | `s3://mirrorview-experimental-artifacts/data_platform/data/twitter/twitter_fba4ddb2-fcf7-4a13-a7cc-0d98db44b547/features/twitter_2026_09_06_192847_llm_features_v1/is_self_contained/` |
| `batches/part-00000.parquet` | `s3://mirrorview-experimental-artifacts/data_platform/data/twitter/twitter_fba4ddb2-fcf7-4a13-a7cc-0d98db44b547/features/twitter_2026_09_06_192847_llm_features_v1/is_self_contained/batches/part-00000.parquet` |
| `batches/part-00001.parquet` | `s3://mirrorview-experimental-artifacts/data_platform/data/twitter/twitter_fba4ddb2-fcf7-4a13-a7cc-0d98db44b547/features/twitter_2026_09_06_192847_llm_features_v1/is_self_contained/batches/part-00001.parquet` |
| `batches/part-00002.parquet` | `s3://mirrorview-experimental-artifacts/data_platform/data/twitter/twitter_fba4ddb2-fcf7-4a13-a7cc-0d98db44b547/features/twitter_2026_09_06_192847_llm_features_v1/is_self_contained/batches/part-00002.parquet` |
| `batches/part-00003.parquet` | `s3://mirrorview-experimental-artifacts/data_platform/data/twitter/twitter_fba4ddb2-fcf7-4a13-a7cc-0d98db44b547/features/twitter_2026_09_06_192847_llm_features_v1/is_self_contained/batches/part-00003.parquet` |

`final.parquet` SHA-256: `69d922ef1933ea3c236d5ea2ddced5e72cc940cfab31346afc6ccb23477f7da5`

`manifest.json` SHA-256: `b6ce3062da1202019d0f5d0df9c0f19ba897607c163e7ebc0cd4fd2626026b4d`

`manifest.json` records `model_id=gpt-5.4-nano` and `expected_row_count=6374`. The campaign writer does not store an `engine_type` field on the manifest. Production used the OpenAI Batch engine only.

`smoke/resume_evidence.json` is absent, as required for this feature.

## Run timing

| Metric | Value |
|--------|-------|
| Wall-clock start (UTC) | `2026-09-07T04:56:52Z` |
| Wall-clock end (UTC) | `2026-09-07T05:12:06Z` |
| Wall-clock hours | 0.25 |
| Throughput | 25,105 rows/hour |
| Resume or reattach events during Phase B | 0 |

## Cost

| Metric | Value |
|--------|-------|
| Smoke estimated full run (avg) | $0.354809 |
| Smoke estimated full run (max) | $0.368258 |
| Actual cost (5 OpenAI batches) | $0.358554 |
| Input tokens | 2,828,628 |
| Output tokens | 121,106 |
| Pricing | Batch API `gpt-5.4-nano`: $0.10/M input, $0.625/M output |

## Label counts

| Label | Count |
|-------|-------|
| `true` | 3634 |
| `false` | 2740 |
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
| Accepted `is_self_contained` values only | pass |
| Smoke objects remain on S3 | pass |

## OpenAI Batch job ids

5 distinct provider batch ids. The smoke batch id is `batch_6a9e321b19888190ab5668f73cc3e244`. The first full-run batch id is `batch_6a9e44196a0c81908ca7698374317647` (part 0 expansion). The last batch id is `batch_6a9e469613e8819080a49810377cc2d5` (part 3). Full list is in `manifest.json` `batches[].provider_batch_ids`.

## Git smoke copies

Temporary Git copies under `docs/plans/2026-09-07_generate_twitter_llm_features_e3c91a/reports/smoke/` were removed after Phase B. S3 smoke objects under `s3://mirrorview-experimental-artifacts/data_platform/data/twitter/twitter_fba4ddb2-fcf7-4a13-a7cc-0d98db44b547/features/twitter_2026_09_06_192847_llm_features_v1/is_self_contained/smoke/` remain.
