# is_news_or_opinion Phase B run report

## Approval

Phase B started after explicit owner LGTM on 2026-09-07. GitHub issue comments were not posted (read-only token). Issue #222, PR https://github.com/METResearchGroup/mirrorView-task/pull/242.

## Pinned identity

| Field | Value |
|-------|-------|
| Dataset id | `reddit_3d8a2c41-9b17-4e6f-a5d0-8c1b2e4f6079` |
| Preprocessed run | `2026_09_03-23:39:28` |
| Preprocessed row count | 400,000 |
| Campaign id | `reddit_2026_09_03_233928_llm_features_v1` |
| Feature name | `is_news_or_opinion` |
| Run id | `reddit_2026_09_03_233928_llm_features_v1:is_news_or_opinion` |
| Model id | `gpt-5.4-nano` |
| Engine | OpenAI Batch `gpt-5.4-nano` |
| Batch size | 2000 |
| Prompt source | `data_platform/generate_features/is_news_or_opinion/generate_feature.py` → `SYSTEM_PROMPT` |
| Prompt hash | `dcf52b33629bac70030fd8db9707824c38ff917f4acc65617a035c1e142acbf6` |

## S3 artifacts

| Object | URI |
|--------|-----|
| final.parquet | `s3://mirrorview-experimental-artifacts/data_platform/data/reddit/reddit_3d8a2c41-9b17-4e6f-a5d0-8c1b2e4f6079/features/reddit_2026_09_03_233928_llm_features_v1/is_news_or_opinion/final.parquet` |
| manifest.json | `s3://mirrorview-experimental-artifacts/data_platform/data/reddit/reddit_3d8a2c41-9b17-4e6f-a5d0-8c1b2e4f6079/features/reddit_2026_09_03_233928_llm_features_v1/is_news_or_opinion/manifest.json` |
| progress.jsonl | `s3://mirrorview-experimental-artifacts/data_platform/data/reddit/reddit_3d8a2c41-9b17-4e6f-a5d0-8c1b2e4f6079/features/reddit_2026_09_03_233928_llm_features_v1/is_news_or_opinion/progress.jsonl` |

`final.parquet` SHA-256 (file bytes, not ETag): `f75e63e66cf95afdc5267a04fa8e2b5b45326e7cba9f12873bb86e296a07d390`

## Run summary

| Metric | Value |
|--------|-------|
| Wall-clock start | 2026-09-07T04:53:20Z |
| Wall-clock end | 2026-09-07T20:07:26Z |
| Wall-clock hours | 15.24 |
| Throughput | 26,247 rows/hour |
| Rows in final.parquet | 400,000 |
| failed_row_count | 0 |
| Batch parts written | 200 |
| errors.jsonl lines | 0 |

## Label counts

| Label | Count |
|-------|------:|
| `neither` | 95,320 |
| `news` | 5,397 |
| `opinion` | 299,283 |
| **Total** | **400,000** |

## Cost

| Metric | Value |
|--------|-------|
| Smoke estimated full run (avg) | $18.224 |
| Smoke estimated full run (max) | $24.42 |
| Pricing | OpenAI Batch `gpt-5.4-nano` |

Actual provider usage for the 400,000-row run is on the OpenAI batch objects listed in `progress.jsonl`. This report records the smoke-scaled estimate, not a live usage invoice.

## final.parquet completion rule

`final.parquet` was written once every input id was labeled exactly once. `row_count + failed_row_count == 400,000`. Unique `source_record_id` count is 400,000. SHA-256 is of the object bytes.

## Validation results

| Check | Result |
|-------|--------|
| final.parquet SHA-256 matches manifest | `f75e63e66cf95afdc5267a04fa8e2b5b45326e7cba9f12873bb86e296a07d390` |
| Row accounting | 400,000 + 0 failed = 400,000 |
| Unique `source_record_id` | 400,000 |
| Label nulls | 0 |
| `engine_type` | `openai` |
| Batch parts | 200 |
| Smoke ids in part-00000 | PASS |
| errors.jsonl | empty |
