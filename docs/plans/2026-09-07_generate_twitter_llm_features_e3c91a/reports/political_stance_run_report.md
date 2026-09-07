# political_stance Phase B run report

## Approval

Phase B was approved by the repository owner on parent issue 232 in comment https://github.com/METResearchGroup/mirrorView-task/issues/232#issuecomment-5564895800 (2026-09-07). That comment signs off on Step 1 (PR #238), the seven ten-post smokes, and the aggregate cost.

## Pinned identity

| Field | Value |
|-------|-------|
| Dataset id | `twitter_fba4ddb2-fcf7-4a13-a7cc-0d98db44b547` |
| Preprocessed run | `2026_09_06-19:28:47` |
| Preprocessed row count | 6,374 |
| Campaign id | `twitter_2026_09_06_192847_llm_features_v1` |
| Feature name | `political_stance` |
| Run id | `twitter_2026_09_06_192847_llm_features_v1:political_stance` |
| Model id | `gpt-5.4-nano` |
| Batch size | 2,000 |
| Prompt source | `data_platform/generate_features/political_stance/generate_feature.py` |
| Prompt hash | `706ada488b0308fc4ad34cf7556b6a7d581624cb8cf24b26e018723629037687` |
| Accepted label values | `left`, `right`, `neutral`, `unclear` |
| Label column | `political_stance` |

## S3 artifacts

| Artifact | URI |
|----------|-----|
| `final.parquet` | `s3://mirrorview-experimental-artifacts/data_platform/data/twitter/twitter_fba4ddb2-fcf7-4a13-a7cc-0d98db44b547/features/twitter_2026_09_06_192847_llm_features_v1/political_stance/final.parquet` |
| `manifest.json` | `s3://mirrorview-experimental-artifacts/data_platform/data/twitter/twitter_fba4ddb2-fcf7-4a13-a7cc-0d98db44b547/features/twitter_2026_09_06_192847_llm_features_v1/political_stance/manifest.json` |
| `progress.jsonl` | `s3://mirrorview-experimental-artifacts/data_platform/data/twitter/twitter_fba4ddb2-fcf7-4a13-a7cc-0d98db44b547/features/twitter_2026_09_06_192847_llm_features_v1/political_stance/progress.jsonl` |
| Feature prefix | `s3://mirrorview-experimental-artifacts/data_platform/data/twitter/twitter_fba4ddb2-fcf7-4a13-a7cc-0d98db44b547/features/twitter_2026_09_06_192847_llm_features_v1/political_stance/` |
| `batches/part-00000.parquet` | `s3://mirrorview-experimental-artifacts/data_platform/data/twitter/twitter_fba4ddb2-fcf7-4a13-a7cc-0d98db44b547/features/twitter_2026_09_06_192847_llm_features_v1/political_stance/batches/part-00000.parquet` |
| `batches/part-00001.parquet` | `s3://mirrorview-experimental-artifacts/data_platform/data/twitter/twitter_fba4ddb2-fcf7-4a13-a7cc-0d98db44b547/features/twitter_2026_09_06_192847_llm_features_v1/political_stance/batches/part-00001.parquet` |
| `batches/part-00002.parquet` | `s3://mirrorview-experimental-artifacts/data_platform/data/twitter/twitter_fba4ddb2-fcf7-4a13-a7cc-0d98db44b547/features/twitter_2026_09_06_192847_llm_features_v1/political_stance/batches/part-00002.parquet` |
| `batches/part-00003.parquet` | `s3://mirrorview-experimental-artifacts/data_platform/data/twitter/twitter_fba4ddb2-fcf7-4a13-a7cc-0d98db44b547/features/twitter_2026_09_06_192847_llm_features_v1/political_stance/batches/part-00003.parquet` |

`final.parquet` SHA-256: `de7a67c77ffe98ccf439dca6f6ededb347a4658303424b9955d9a0e7d63d9c2e`

`manifest.json` SHA-256: `4f5dd74b01394bcfc5a7890ba9da2a5095e157cd6dbd3367734539e4229533e2`

`manifest.json` records `model_id=gpt-5.4-nano` and `expected_row_count=6374`. The campaign writer does not store an `engine_type` field on the manifest. Production used the OpenAI Batch engine only.

`smoke/resume_evidence.json` is absent, as required for this feature.

## Run timing

| Metric | Value |
|--------|-------|
| Wall-clock start (UTC) | `2026-09-07T05:31:18Z` |
| Wall-clock end (UTC) | `2026-09-07T05:42:44Z` |
| Wall-clock hours | 0.19 |
| Throughput | 33,450 rows/hour |
| Resume or reattach events during Phase B | 0 |

## Cost

| Metric | Value |
|--------|-------|
| Smoke estimated full run (avg) | $0.367079 |
| Smoke estimated full run (max) | $0.383715 |
| Actual cost (5 OpenAI batches) | $0.370964 |
| Input tokens | 2,943,360 |
| Output tokens | 122,605 |
| Pricing | Batch API `gpt-5.4-nano`: $0.10/M input, $0.625/M output |

## Label counts

| Label | Count |
|-------|-------|
| `neutral` | 2191 |
| `unclear` | 1499 |
| `right` | 1483 |
| `left` | 1201 |
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
| Accepted `political_stance` values only | pass |
| Smoke objects remain on S3 | pass |

## OpenAI Batch job ids

5 distinct provider batch ids. The smoke batch id is `batch_6a9e32bdd1f0819084f3c5be41303bf0`. The first full-run batch id is `batch_6a9e4c2b0e2c8190a6fbd7dee56b7011` (part 0 expansion). The last batch id is `batch_6a9e4e7fd4ac819092decde09438c60f` (part 3). Full list is in `manifest.json` `batches[].provider_batch_ids`.

## Git smoke copies

Temporary Git copies under `docs/plans/2026-09-07_generate_twitter_llm_features_e3c91a/reports/smoke/` were removed after Phase B. S3 smoke objects under `s3://mirrorview-experimental-artifacts/data_platform/data/twitter/twitter_fba4ddb2-fcf7-4a13-a7cc-0d98db44b547/features/twitter_2026_09_06_192847_llm_features_v1/political_stance/smoke/` remain.
