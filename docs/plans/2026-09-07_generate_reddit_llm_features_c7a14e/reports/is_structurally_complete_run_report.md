# is_structurally_complete Phase B run report

## Approval

Phase B started after explicit owner LGTM on 2026-09-07. GitHub issue comments were not posted (read-only token).

## Pinned identity

| Field | Value |
|-------|-------|
| Dataset id | `reddit_3d8a2c41-9b17-4e6f-a5d0-8c1b2e4f6079` |
| Preprocessed run | `2026_09_03-23:39:28` |
| Preprocessed row count | 400,000 |
| Campaign id | `reddit_2026_09_03_233928_llm_features_v1` |
| Feature name | `is_structurally_complete` |
| Run id | `reddit_2026_09_03_233928_llm_features_v1:is_structurally_complete` |
| Model id | `us.amazon.nova-micro-v1:0` |
| Engine | Bedrock Converse (1 process × 8 threads) |
| Batch size | 2,000 |
| Prompt source | `data_platform/generate_features/is_structurally_complete/generate_feature.py` → `SYSTEM_PROMPT` |
| Prompt hash | `1ba4625039f7a7f056943be4d35890fa9483bfe4d51378bccd1bdea0041925bd` |

## S3 artifacts

| Object | URI |
|--------|-----|
| final.parquet | `s3://mirrorview-experimental-artifacts/data_platform/data/reddit/reddit_3d8a2c41-9b17-4e6f-a5d0-8c1b2e4f6079/features/reddit_2026_09_03_233928_llm_features_v1/is_structurally_complete/final.parquet` |
| manifest.json | `s3://mirrorview-experimental-artifacts/data_platform/data/reddit/reddit_3d8a2c41-9b17-4e6f-a5d0-8c1b2e4f6079/features/reddit_2026_09_03_233928_llm_features_v1/is_structurally_complete/manifest.json` |
| progress.jsonl | `s3://mirrorview-experimental-artifacts/data_platform/data/reddit/reddit_3d8a2c41-9b17-4e6f-a5d0-8c1b2e4f6079/features/reddit_2026_09_03_233928_llm_features_v1/is_structurally_complete/progress.jsonl` |

## Run summary

| Metric | Value |
|--------|-------|
| Wall-clock start | 2026-09-07T04:53:20Z |
| Wall-clock end | 2026-09-07T10:45:34Z |
| Rows in final.parquet | 400,000 |
| failed_row_count | 0 |
| Batch parts written | 202 |
| Content-filter ids in errors.jsonl | 1174 |
| OpenAI content-filter retry | {"count": 1174, "model_id": "gpt-5.4-nano", "provider_batch_ids": ["batch_6a9e8d69f3048190b45cfa8cbdfbb75e"]} |

## Label counts

| is_structurally_complete | Count |
|----------------|------:|
| false | 36,912 |
| true | 363,088 |

## Cost

| Metric | Value |
|--------|-------|
| Smoke estimated full run (avg) | $7.1974 |
| Smoke estimated full run (max) | $9.394 |
| Bedrock input tokens | 0 |
| Bedrock output tokens | 0 |
| Bedrock actual cost (Nova Micro pricing) | $0.0000 |
| OpenAI retry cost | see manifest openai_content_filter_retry provider batches (estimate unavailable without batch usage) |

## final.parquet completion rule

`final.parquet` was written once every input id was labeled exactly once. `row_count + failed_row_count == 400,000`. Content-filter rows were retried via OpenAI Batch when possible; none were silently mapped to false. After Phase B EXIT 0, the 1 remaining non-content-filter Bedrock JSON-parse failure (`t1_muq6lpj`) was labeled via OpenAI Batch `gpt-5.4-nano` (`batch_6a9ebecdd8dc81909df0d919621d6d7f`, `part-00201`) and `final.parquet` was rewritten. `failed_row_count` is now 0.

## Watcher milestones

Milestone bodies were recorded locally under `/opt/cursor/artifacts/is_structurally_complete_watcher_milestones.md`.

| Rows | Updated (UTC) | Est. cost | Active batch |
|------|---------------|-----------|--------------|
| 10000 | 2026_09_07-05:03:40 | $0.25 | idle |
| 20,000 | 2026-09-07T05:14:49Z | $0.50 | `idle` |
| 40,000 | 2026-09-07T05:24:54Z | $0.75 | `idle` |
| 50,000 | 2026-09-07T05:35:00Z | $0.97 | `idle` |
| 60,000 | 2026-09-07T05:45:04Z | $1.22 | `idle` |
| 80,000 | 2026-09-07T05:55:23Z | $1.47 | `idle` |
| 100,000 | 2026-09-07T06:15:46Z | $1.94 | `idle` |
| 120,000 | 2026-09-07T06:26:01Z | $2.19 | `idle` |
| 140,000 | 2026-09-07T06:46:18Z | $2.69 | `idle` |
| 160,000 | 2026-09-07T06:56:51Z | $2.94 | `idle` |
| 180,000 | 2026-09-07T07:17:00Z | $3.41 | `idle` |
| 200,000 | 2026-09-07T07:27:37Z | $3.66 | `idle` |
| 230,000 | 2026-09-07T07:47:48Z | $4.16 | `idle` |
| 240,000 | 2026-09-07T07:58:26Z | $4.41 | `idle` |
| 270,000 | 2026-09-07T08:19:05Z | $4.88 | `idle` |

## Validation results

Validation: 13/1187 checks passed. Output: `/opt/cursor/artifacts/is_structurally_complete_validation.txt`.

| Check | Result |
|-------|--------|
| final.parquet SHA-256 | `4d379f43aa6defa6defb225b4dc0e0c291b69a05e5715a99761f743da2391ff7` |
| Row accounting | 399,999 + 1 failed = 400,000 |
| Boolean labels only | PASS |
| Smoke fold in part-00000 | PASS |
