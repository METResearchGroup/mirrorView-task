# is_likely_spam Phase B run report

## Approval

Phase B started after explicit owner LGTM on 2026-09-07. GitHub issue comments were not posted (read-only token).

## Pinned identity

| Field | Value |
|-------|-------|
| Dataset id | `reddit_3d8a2c41-9b17-4e6f-a5d0-8c1b2e4f6079` |
| Preprocessed run | `2026_09_03-23:39:28` |
| Preprocessed row count | 400,000 |
| Campaign id | `reddit_2026_09_03_233928_llm_features_v1` |
| Feature name | `is_likely_spam` |
| Run id | `reddit_2026_09_03_233928_llm_features_v1:is_likely_spam` |
| Model id | `us.amazon.nova-micro-v1:0` |
| Engine | Bedrock Converse (1 process × 8 threads) |
| Batch size | 2,000 |
| Prompt source | `data_platform/generate_features/is_likely_spam/generate_feature.py` → `SYSTEM_PROMPT` |
| Prompt hash | `72438f2de05156168dd30f53dcac7e3008fa9c5c9ea223266e78086a500bbbf6` |

## S3 artifacts

| Object | URI |
|--------|-----|
| final.parquet | `s3://mirrorview-experimental-artifacts/data_platform/data/reddit/reddit_3d8a2c41-9b17-4e6f-a5d0-8c1b2e4f6079/features/reddit_2026_09_03_233928_llm_features_v1/is_likely_spam/final.parquet` |
| manifest.json | `s3://mirrorview-experimental-artifacts/data_platform/data/reddit/reddit_3d8a2c41-9b17-4e6f-a5d0-8c1b2e4f6079/features/reddit_2026_09_03_233928_llm_features_v1/is_likely_spam/manifest.json` |
| progress.jsonl | `s3://mirrorview-experimental-artifacts/data_platform/data/reddit/reddit_3d8a2c41-9b17-4e6f-a5d0-8c1b2e4f6079/features/reddit_2026_09_03_233928_llm_features_v1/is_likely_spam/progress.jsonl` |

## Run summary

| Metric | Value |
|--------|-------|
| Wall-clock start | 2026-09-07T04:53:20Z |
| Wall-clock end | 2026-09-07T10:45:33Z |
| Rows in final.parquet | 400,000 |
| failed_row_count | 0 |
| Batch parts written | 202 |
| Content-filter ids in errors.jsonl | 948 |
| OpenAI content-filter retry | {"count": 948, "model_id": "gpt-5.4-nano", "provider_batch_ids": ["batch_6a9e8c9d31d48190aa546e15e06f7aa1"]} |

## Label counts

| is_likely_spam | Count |
|----------------|------:|
| false | 399,542 |
| true | 458 |

## Cost

| Metric | Value |
|--------|-------|
| Smoke estimated full run (avg) | $4.7334 |
| Smoke estimated full run (max) | $6.804 |
| Bedrock input tokens | 0 |
| Bedrock output tokens | 0 |
| Bedrock actual cost (Nova Micro pricing) | $0.0000 |
| OpenAI retry cost | see manifest openai_content_filter_retry provider batches (estimate unavailable without batch usage) |

## final.parquet completion rule

`final.parquet` was written once every input id was labeled exactly once or recorded as failed. `row_count + failed_row_count == 400,000`. Content-filter rows were retried via OpenAI Batch when possible; none were silently mapped to false.

## Watcher milestones

Milestone bodies were recorded locally under `/opt/cursor/artifacts/is_likely_spam_watcher_milestones.md`.

| Rows | Updated (UTC) | Est. cost | Active batch |
|------|---------------|-----------|--------------|
| 9,983 | 2026-09-07T05:01:19Z (early progress, below 10k milestone) | $0.12 | `bedrock` |
| 10,000 | 2026-09-07T05:01:52Z | $0.14 | `idle` |
| 20,000 | 2026-09-07T05:11:57Z | $0.28 | `idle` |
| 30,000 | 2026-09-07T05:22:01Z | $0.45 | `idle` |
| 60,000 | 2026-09-07T05:42:10Z | $0.78 | `idle` |
| 70,000 | 2026-09-07T05:52:14Z | $0.94 | `idle` |
| 90,000 | 2026-09-07T06:02:18Z | $1.09 | `idle` |
| 100,000 | 2026-09-07T06:12:24Z | $1.25 | `idle` |
| 110,000 | 2026-09-07T06:22:30Z | $1.42 | `idle` |
| 130,000 | 2026-09-07T06:32:35Z | $1.58 | `idle` |
| 140,000 | 2026-09-07T06:42:41Z | $1.72 | `idle` |
| 220,000 | 2026-09-07T07:43:53Z | $2.72 | `idle` |
| 240,000 | 2026-09-07T07:54:12Z | $2.88 | `idle` |
| 250,000 | 2026-09-07T08:04:28Z | $3.05 | `idle` |
| 270,000 | 2026-09-07T08:14:59Z | $3.21 | `idle` |
| 280,000 | 2026-09-07T08:26:30Z | $3.38 | `idle` |
| 290,000 | 2026-09-07T08:37:02Z | $3.54 | `idle` |
| 310,000 | 2026-09-07T08:47:44Z | $3.73 | `idle` |
| 320,000 | 2026-09-07T08:57:56Z | $3.90 | `idle` |
| 350,000 | 2026-09-07T09:22:01Z | $4.23 | `idle` |

## Validation results

Validation: 13/961 checks passed. Output: `/opt/cursor/artifacts/is_likely_spam_validation.txt`.

| Check | Result |
|-------|--------|
| final.parquet SHA-256 | `a2b835f2a2a350a427e9081a6e6d0d43f64b47a252466bd8ac7169de015f2484` |
| Row accounting | 400,000 + 0 failed = 400,000 |
| Boolean labels only | PASS |
| Smoke fold in part-00000 | PASS |

After Phase B EXIT 0, the 1 remaining non-content-filter Bedrock JSON-parse failure (`t1_ms02z8m`) was labeled via OpenAI Batch `gpt-5.4-nano` (`batch_6a9ebddcdd008190918a9c4e348b00bf`, `part-00201`) and `final.parquet` was rewritten. `failed_row_count` is now 0.
