# llm_toxicity_tiered Phase B run report

## Approval

Phase B was approved by the repository owner on parent issue 251 in comment https://github.com/METResearchGroup/mirrorView-task/issues/251#issuecomment-5578378098 (2026-09-08). That comment signs off on #254 / PR #263, the seven ten-post smokes, and the aggregate cost.

## Pinned identity

| Field | Value |
|-------|-------|
| Dataset id | `twitter_5901767a-e609-46fc-9a17-742516b548f2` |
| Preprocessed run | `2026_09_08-01:48:08` |
| Preprocessed row count | 6,408 |
| Campaign id | `twitter_2026_09_08_014808_llm_features_v1` |
| Feature name | `llm_toxicity_tiered` |
| Run id | `twitter_2026_09_08_014808_llm_features_v1:llm_toxicity_tiered` |
| Model id | `gpt-5.4-nano` |
| Batch size | 2,000 |
| Prompt source | `data_platform/generate_features/llm_toxicity_tiered/generate_feature.py` |
| Prompt hash | `1b22e0603119a3360fa9b3370b5157162323b00709fdb0eead1954eca9133c6b` |
| Accepted label values | `low`, `medium`, `high` |
| Label column | `toxicity_tier` |

## S3 artifacts

| Artifact | URI |
|----------|-----|
| `final.parquet` | `s3://mirrorview-experimental-artifacts/data_platform/data/twitter/twitter_5901767a-e609-46fc-9a17-742516b548f2/features/twitter_2026_09_08_014808_llm_features_v1/llm_toxicity_tiered/final.parquet` |
| `manifest.json` | `s3://mirrorview-experimental-artifacts/data_platform/data/twitter/twitter_5901767a-e609-46fc-9a17-742516b548f2/features/twitter_2026_09_08_014808_llm_features_v1/llm_toxicity_tiered/manifest.json` |
| `progress.jsonl` | `s3://mirrorview-experimental-artifacts/data_platform/data/twitter/twitter_5901767a-e609-46fc-9a17-742516b548f2/features/twitter_2026_09_08_014808_llm_features_v1/llm_toxicity_tiered/progress.jsonl` |
| Feature prefix | `s3://mirrorview-experimental-artifacts/data_platform/data/twitter/twitter_5901767a-e609-46fc-9a17-742516b548f2/features/twitter_2026_09_08_014808_llm_features_v1/llm_toxicity_tiered/` |
| `batches/part-00000.parquet` | `s3://mirrorview-experimental-artifacts/data_platform/data/twitter/twitter_5901767a-e609-46fc-9a17-742516b548f2/features/twitter_2026_09_08_014808_llm_features_v1/llm_toxicity_tiered/batches/part-00000.parquet` |
| `batches/part-00001.parquet` | `s3://mirrorview-experimental-artifacts/data_platform/data/twitter/twitter_5901767a-e609-46fc-9a17-742516b548f2/features/twitter_2026_09_08_014808_llm_features_v1/llm_toxicity_tiered/batches/part-00001.parquet` |
| `batches/part-00002.parquet` | `s3://mirrorview-experimental-artifacts/data_platform/data/twitter/twitter_5901767a-e609-46fc-9a17-742516b548f2/features/twitter_2026_09_08_014808_llm_features_v1/llm_toxicity_tiered/batches/part-00002.parquet` |
| `batches/part-00003.parquet` | `s3://mirrorview-experimental-artifacts/data_platform/data/twitter/twitter_5901767a-e609-46fc-9a17-742516b548f2/features/twitter_2026_09_08_014808_llm_features_v1/llm_toxicity_tiered/batches/part-00003.parquet` |

`final.parquet` SHA-256: `1011fa84ab7303463d3bcefed04de705232d171f662d03961f88c71f8e3747c6`

`manifest.json` SHA-256: `d25a94cf238021570a6ab3c70c7a2715f338807b88c4314b53c3f9e0744106d0`

`manifest.json` records `model_id=gpt-5.4-nano` and `expected_row_count=6408`. The campaign writer does not store an `engine_type` field on the manifest. Production used the OpenAI Batch engine only.

`smoke/resume_evidence.json` is absent, as required for this feature.

## Run timing

| Metric | Value |
|--------|-------|
| Wall-clock start (UTC) | `2026-09-08T04:54:54Z` |
| Wall-clock end (UTC) | `2026-09-08T05:13:28Z` |
| Wall-clock hours | 0.31 |
| Throughput | 20,708 rows/hour |
| Resume or reattach events during Phase B | 0 |

## Cost

| Metric | Value |
|--------|-------|
| Smoke estimated full run (avg) | $0.333793 |
| Smoke estimated full run (max) | $0.347634 |
| Actual cost (5 OpenAI batches) | $0.332803 |
| Input tokens | 2,446,934 |
| Output tokens | 140,976 |
| Pricing | Batch API `gpt-5.4-nano`: $0.10/M input, $0.625/M output |

## Label counts

| Label | Count |
|-------|-------|
| `low` | 5004 |
| `medium` | 1115 |
| `high` | 289 |
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
| Accepted `toxicity_tier` values only | pass |
| Smoke objects remain on S3 | pass |

## OpenAI Batch job ids

5 distinct provider batch ids. The smoke batch id is `batch_6a9f7160c9888190997f6bb8b5b2d826`. The first full-run batch id is `batch_6a9f95249f0c8190bcf02ceab9f27f48` (part 0 expansion). The last batch id is `batch_6a9f990a58088190823d7cb539371fdc` (part 3). Full list is in `manifest.json` `batches[].provider_batch_ids`.

## Git smoke copies

Temporary Git copies under `docs/plans/2026-09-08_twitter_llm_smoke_7c6e6a/reports/smoke/` were removed after Phase B. S3 smoke objects under `s3://mirrorview-experimental-artifacts/data_platform/data/twitter/twitter_5901767a-e609-46fc-9a17-742516b548f2/features/twitter_2026_09_08_014808_llm_features_v1/llm_toxicity_tiered/smoke/` remain.
