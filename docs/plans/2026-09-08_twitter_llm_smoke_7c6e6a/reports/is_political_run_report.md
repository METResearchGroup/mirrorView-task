# is_political Phase B run report

## Approval

Phase B was approved by the repository owner on parent issue 251 in comment https://github.com/METResearchGroup/mirrorView-task/issues/251#issuecomment-5578378098 (2026-09-08). That comment signs off on #254 / PR #263, the seven ten-post smokes, and the aggregate cost.

## Pinned identity

| Field | Value |
|-------|-------|
| Dataset id | `twitter_5901767a-e609-46fc-9a17-742516b548f2` |
| Preprocessed run | `2026_09_08-01:48:08` |
| Preprocessed row count | 6,408 |
| Campaign id | `twitter_2026_09_08_014808_llm_features_v1` |
| Feature name | `is_political` |
| Run id | `twitter_2026_09_08_014808_llm_features_v1:is_political` |
| Model id | `gpt-5.4-nano` |
| Batch size | 2,000 |
| Prompt source | `data_platform/generate_features/is_political/generate_feature.py` |
| Prompt hash | `d1d8c0ab2c180b7fb511c67bde49de7b9c465e9d21d45210c196559ae6c958a1` |
| Accepted label values | boolean `true` or `false` |
| Label column | `is_political` |

## S3 artifacts

| Artifact | URI |
|----------|-----|
| `final.parquet` | `s3://mirrorview-experimental-artifacts/data_platform/data/twitter/twitter_5901767a-e609-46fc-9a17-742516b548f2/features/twitter_2026_09_08_014808_llm_features_v1/is_political/final.parquet` |
| `manifest.json` | `s3://mirrorview-experimental-artifacts/data_platform/data/twitter/twitter_5901767a-e609-46fc-9a17-742516b548f2/features/twitter_2026_09_08_014808_llm_features_v1/is_political/manifest.json` |
| `progress.jsonl` | `s3://mirrorview-experimental-artifacts/data_platform/data/twitter/twitter_5901767a-e609-46fc-9a17-742516b548f2/features/twitter_2026_09_08_014808_llm_features_v1/is_political/progress.jsonl` |
| Feature prefix | `s3://mirrorview-experimental-artifacts/data_platform/data/twitter/twitter_5901767a-e609-46fc-9a17-742516b548f2/features/twitter_2026_09_08_014808_llm_features_v1/is_political/` |
| `batches/part-00000.parquet` | `s3://mirrorview-experimental-artifacts/data_platform/data/twitter/twitter_5901767a-e609-46fc-9a17-742516b548f2/features/twitter_2026_09_08_014808_llm_features_v1/is_political/batches/part-00000.parquet` |
| `batches/part-00001.parquet` | `s3://mirrorview-experimental-artifacts/data_platform/data/twitter/twitter_5901767a-e609-46fc-9a17-742516b548f2/features/twitter_2026_09_08_014808_llm_features_v1/is_political/batches/part-00001.parquet` |
| `batches/part-00002.parquet` | `s3://mirrorview-experimental-artifacts/data_platform/data/twitter/twitter_5901767a-e609-46fc-9a17-742516b548f2/features/twitter_2026_09_08_014808_llm_features_v1/is_political/batches/part-00002.parquet` |
| `batches/part-00003.parquet` | `s3://mirrorview-experimental-artifacts/data_platform/data/twitter/twitter_5901767a-e609-46fc-9a17-742516b548f2/features/twitter_2026_09_08_014808_llm_features_v1/is_political/batches/part-00003.parquet` |

`final.parquet` SHA-256: `f981f44ea8e9b42c3160d158a5de388b6fed0cbbfdb94a71d85ea340c56e8c53`

`manifest.json` SHA-256: `6df5db12221cadc3bcb201081c14e0f1c65eb2f1c395075ab8031006fadffa93`

`manifest.json` records `model_id=gpt-5.4-nano` and `expected_row_count=6408`. The campaign writer does not store an `engine_type` field on the manifest. Production used the OpenAI Batch engine only.

`smoke/resume_evidence.json` is absent, as required for this feature.

## Run timing

| Metric | Value |
|--------|-------|
| Wall-clock start (UTC) | `2026-09-08T03:17:09Z` |
| Wall-clock end (UTC) | `2026-09-08T03:34:34Z` |
| Wall-clock hours | 0.29 |
| Throughput | 22,075 rows/hour |
| Resume or reattach events during Phase B | 0 |

## Cost

| Metric | Value |
|--------|-------|
| Smoke estimated full run (avg) | $0.275961 |
| Smoke estimated full run (max) | $0.289802 |
| Actual cost (5 OpenAI batches) | $0.274971 |
| Input tokens | 2,068,862 |
| Output tokens | 108,936 |
| Pricing | Batch API `gpt-5.4-nano`: $0.10/M input, $0.625/M output |

## Label counts

| Label | Count |
|-------|-------|
| `true` | 5159 |
| `false` | 1249 |
| **Total in final** | **6,408** |
| `failed_row_count` | 0 |

No `errors.jsonl` was written. Unique `source_record_id` count in `final.parquet` is 6,408.

## Retries and provider batches

| Metric | Value |
|--------|-------|
| Distinct OpenAI batch ids | 5 |
| Parts with more than one provider batch id | 1 (part 0: smoke batch plus full-run batch) |
| `part-00003` rows | 408 |
| Smoke fold on `part-00000` | original smoke `batch_id` and `request_id` preserved |

Part 0 lists two provider batch ids because the ten smoke rows were labeled in Phase A and the remaining 1,990 rows in part 0 were labeled in the first Phase B batch.

## final.parquet completion rule

`final.parquet` was written once every input id was labeled exactly once. `manifest.json` `final_parquet` reports `row_count=6408` and `failed_row_count=0`.

## Watcher milestones

Watcher `--once` on `is_news_or_opinion` after production printed `github_write_skipped=true` and `boundary_crossed=false`. The 10,000-row milestone is absent at 6,408 rows, so no rolling markdown comment body was rendered. The watcher CLI did not write to GitHub.

## Validation results

| Check | Result |
|-------|--------|
| Unique `source_record_id` | pass (6,408) |
| `part-00003` rows | pass (408) |
| Four batch parts `part-00000` through `part-00003` | pass (2,000 / 2,000 / 2,000 / 408) |
| Smoke rows in `part-00000` keep original `batch_id` and `request_id` | pass |
| `final.parquet` SHA-256 matches manifest | pass |
| Accepted `is_political` values only | pass |
| Smoke objects remain on S3 | pass |

## OpenAI Batch job ids

5 distinct provider batch ids. The smoke batch id is `batch_6a9f6f1b5e048190b44c4ccdb7dde0aa`. The first full-run batch id is `batch_6a9f7e3fd7b48190ac48bfe7b00e2d1d` (part 0 expansion). The last batch id is `batch_6a9f81c31040819087961d5adcaf943b` (part 3). Full list is in `manifest.json` `batches[].provider_batch_ids`.

## Git smoke copies

Temporary Git copies under `docs/plans/2026-09-08_twitter_llm_smoke_7c6e6a/reports/smoke/` were removed after Phase B. S3 smoke objects under `s3://mirrorview-experimental-artifacts/data_platform/data/twitter/twitter_5901767a-e609-46fc-9a17-742516b548f2/features/twitter_2026_09_08_014808_llm_features_v1/is_political/smoke/` remain.
