# is_news_or_opinion Phase B run report

## Approval

Phase B was approved by the repository owner on parent issue 232 in comment https://github.com/METResearchGroup/mirrorView-task/issues/232#issuecomment-5564895800 (2026-09-07). That comment signs off on Step 1 (PR #238), the seven ten-post smokes, and the aggregate cost.

## Pinned identity

| Field | Value |
|-------|-------|
| Dataset id | `twitter_fba4ddb2-fcf7-4a13-a7cc-0d98db44b547` |
| Preprocessed run | `2026_09_06-19:28:47` |
| Preprocessed row count | 6,374 |
| Campaign id | `twitter_2026_09_06_192847_llm_features_v1` |
| Feature name | `is_news_or_opinion` |
| Run id | `twitter_2026_09_06_192847_llm_features_v1:is_news_or_opinion` |
| Model id | `gpt-5.4-nano` |
| Batch size | 2,000 |
| Prompt source | `data_platform/generate_features/is_news_or_opinion/generate_feature.py` |
| Prompt hash | `dcf52b33629bac70030fd8db9707824c38ff917f4acc65617a035c1e142acbf6` |
| Accepted label values | `news`, `opinion`, `neither` |
| Label column | `category` |

## S3 artifacts

| Artifact | URI |
|----------|-----|
| `final.parquet` | `s3://mirrorview-experimental-artifacts/data_platform/data/twitter/twitter_fba4ddb2-fcf7-4a13-a7cc-0d98db44b547/features/twitter_2026_09_06_192847_llm_features_v1/is_news_or_opinion/final.parquet` |
| `manifest.json` | `s3://mirrorview-experimental-artifacts/data_platform/data/twitter/twitter_fba4ddb2-fcf7-4a13-a7cc-0d98db44b547/features/twitter_2026_09_06_192847_llm_features_v1/is_news_or_opinion/manifest.json` |
| `progress.jsonl` | `s3://mirrorview-experimental-artifacts/data_platform/data/twitter/twitter_fba4ddb2-fcf7-4a13-a7cc-0d98db44b547/features/twitter_2026_09_06_192847_llm_features_v1/is_news_or_opinion/progress.jsonl` |
| Feature prefix | `s3://mirrorview-experimental-artifacts/data_platform/data/twitter/twitter_fba4ddb2-fcf7-4a13-a7cc-0d98db44b547/features/twitter_2026_09_06_192847_llm_features_v1/is_news_or_opinion/` |
| `batches/part-00000.parquet` | `s3://mirrorview-experimental-artifacts/data_platform/data/twitter/twitter_fba4ddb2-fcf7-4a13-a7cc-0d98db44b547/features/twitter_2026_09_06_192847_llm_features_v1/is_news_or_opinion/batches/part-00000.parquet` |
| `batches/part-00001.parquet` | `s3://mirrorview-experimental-artifacts/data_platform/data/twitter/twitter_fba4ddb2-fcf7-4a13-a7cc-0d98db44b547/features/twitter_2026_09_06_192847_llm_features_v1/is_news_or_opinion/batches/part-00001.parquet` |
| `batches/part-00002.parquet` | `s3://mirrorview-experimental-artifacts/data_platform/data/twitter/twitter_fba4ddb2-fcf7-4a13-a7cc-0d98db44b547/features/twitter_2026_09_06_192847_llm_features_v1/is_news_or_opinion/batches/part-00002.parquet` |
| `batches/part-00003.parquet` | `s3://mirrorview-experimental-artifacts/data_platform/data/twitter/twitter_fba4ddb2-fcf7-4a13-a7cc-0d98db44b547/features/twitter_2026_09_06_192847_llm_features_v1/is_news_or_opinion/batches/part-00003.parquet` |

`final.parquet` SHA-256: `f999ad42141a10ba82194979f3cf3f5673655db7e50d4696bf8100a2fed5fbaa`

`manifest.json` SHA-256: `bcf3ea67da954b6053543db1371c1f4044bb8d81e46fe4cc01df1554967fb349`

`manifest.json` records `model_id=gpt-5.4-nano` and `expected_row_count=6374`. The campaign writer does not store an `engine_type` field on the manifest. Production used the OpenAI Batch engine only.

`smoke/resume_evidence.json` is present (interrupt-and-resume during Phase A).

## Run timing

| Metric | Value |
|--------|-------|
| Wall-clock start (UTC) | `2026-09-07T04:13:10Z` |
| Wall-clock end (UTC) | `2026-09-07T04:29:20Z` |
| Wall-clock hours | 0.27 |
| Throughput | 23,656 rows/hour |
| Resume or reattach events during Phase B | 0 |

## Cost

| Metric | Value |
|--------|-------|
| Smoke estimated full run (avg) | $0.279117 |
| Smoke estimated full run (max) | $0.294160 |
| Actual cost (5 OpenAI batches) | $0.283128 |
| Input tokens | 2,127,488 |
| Output tokens | 112,606 |
| Pricing | Batch API `gpt-5.4-nano`: $0.10/M input, $0.625/M output |

## Label counts

| Label | Count |
|-------|-------|
| `opinion` | 3493 |
| `news` | 2126 |
| `neither` | 755 |
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
| Accepted `category` values only | pass |
| Smoke objects remain on S3 | pass |

## OpenAI Batch job ids

5 distinct provider batch ids. The smoke batch id is `batch_6a9e31241ed48190beafb0e5fb58e91d`. The first full-run batch id is `batch_6a9e39e24ba88190986bbe5b0c2410a1` (part 0 expansion). The last batch id is `batch_6a9e3d4b413881908d55a34f20d6c328` (part 3). Full list is in `manifest.json` `batches[].provider_batch_ids`.

## Git smoke copies

Temporary Git copies under `docs/plans/2026-09-07_generate_twitter_llm_features_e3c91a/reports/smoke/` were removed after Phase B. S3 smoke objects under `s3://mirrorview-experimental-artifacts/data_platform/data/twitter/twitter_fba4ddb2-fcf7-4a13-a7cc-0d98db44b547/features/twitter_2026_09_06_192847_llm_features_v1/is_news_or_opinion/smoke/` remain.
