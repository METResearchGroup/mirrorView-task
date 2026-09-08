# political_stance Phase B run report

## Approval

Phase B started after explicit owner LGTM on 2026-09-07. GitHub issue comments were not posted (read-only token). Issue #227, PR https://github.com/METResearchGroup/mirrorView-task/pull/247.

## Pinned identity

| Field | Value |
|-------|-------|
| Dataset id | `reddit_3d8a2c41-9b17-4e6f-a5d0-8c1b2e4f6079` |
| Preprocessed run | `2026_09_03-23:39:28` |
| Preprocessed row count | 400,000 |
| Campaign id | `reddit_2026_09_03_233928_llm_features_v1` |
| Feature name | `political_stance` |
| Run id | `reddit_2026_09_03_233928_llm_features_v1:political_stance` |
| Model id | `gpt-5.4-nano` |
| Engine | OpenAI Batch `gpt-5.4-nano` |
| Batch size | 2000 |
| Prompt source | `data_platform/generate_features/political_stance/generate_feature.py` → `SYSTEM_PROMPT` |
| Prompt hash | `706ada488b0308fc4ad34cf7556b6a7d581624cb8cf24b26e018723629037687` |

## S3 artifacts

| Object | URI |
|--------|-----|
| final.parquet | `s3://mirrorview-experimental-artifacts/data_platform/data/reddit/reddit_3d8a2c41-9b17-4e6f-a5d0-8c1b2e4f6079/features/reddit_2026_09_03_233928_llm_features_v1/political_stance/final.parquet` |
| manifest.json | `s3://mirrorview-experimental-artifacts/data_platform/data/reddit/reddit_3d8a2c41-9b17-4e6f-a5d0-8c1b2e4f6079/features/reddit_2026_09_03_233928_llm_features_v1/political_stance/manifest.json` |
| progress.jsonl | `s3://mirrorview-experimental-artifacts/data_platform/data/reddit/reddit_3d8a2c41-9b17-4e6f-a5d0-8c1b2e4f6079/features/reddit_2026_09_03_233928_llm_features_v1/political_stance/progress.jsonl` |

`final.parquet` SHA-256 (file bytes, not ETag): `a034021e56646cabb69dc2ba8baf81d1042581cd710edbdd576702b26e801d24`

## Run summary

| Metric | Value |
|--------|-------|
| Wall-clock start | 2026-09-07T04:53:20Z |
| Wall-clock end | 2026-09-07T20:46:03Z |
| Wall-clock hours | 15.88 |
| Throughput | 25,189 rows/hour |
| Rows in final.parquet | 400,000 |
| failed_row_count | 0 |
| Batch parts written | 200 |
| errors.jsonl lines | 0 |

## Label counts

| Label | Count |
|-------|------:|
| `left` | 68,107 |
| `neutral` | 30,954 |
| `right` | 36,116 |
| `unclear` | 264,823 |
| **Total** | **400,000** |

## Cost

| Metric | Value |
|--------|-------|
| Smoke estimated full run (avg) | $23.744 |
| Smoke estimated full run (max) | $30.04 |
| Pricing | OpenAI Batch `gpt-5.4-nano` |

Actual provider usage for the 400,000-row run is on the OpenAI batch objects listed in `progress.jsonl`. This report records the smoke-scaled estimate, not a live usage invoice.

## final.parquet completion rule

`final.parquet` was written once every input id was labeled exactly once. `row_count + failed_row_count == 400,000`. Unique `source_record_id` count is 400,000. SHA-256 is of the object bytes.

## Validation results

| Check | Result |
|-------|--------|
| final.parquet SHA-256 matches manifest | `a034021e56646cabb69dc2ba8baf81d1042581cd710edbdd576702b26e801d24` |
| Row accounting | 400,000 + 0 failed = 400,000 |
| Unique `source_record_id` | 400,000 |
| Label nulls | 0 |
| `engine_type` | `openai` |
| Batch parts | 200 |
| Smoke ids in part-00000 | PASS |
| errors.jsonl | empty |
