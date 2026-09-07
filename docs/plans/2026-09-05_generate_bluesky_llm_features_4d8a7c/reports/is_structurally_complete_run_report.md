# is_structurally_complete Phase B run report

## Approval

Phase B was approved in chat on 2026-09-06 ("Approved, run Phase B"). A comment could not be posted on the parent GitHub issue because the automation token has no write scope.

## Pinned identity

| Field | Value |
|-------|-------|
| Dataset id | `bluesky_7e2c4a91-3b5f-4d8e-a6c1-0f9b8d2e5a73` |
| Preprocessed run | `2026_09_03-23:51:30` |
| Preprocessed row count | 200,000 |
| Campaign id | `bluesky_2026_09_03_235130_llm_features_v1` |
| Feature name | `is_structurally_complete` |
| Run id | `bluesky_2026_09_03_235130_llm_features_v1:is_structurally_complete` |
| Model id | `gpt-5.4-nano` |
| Batch size | 2,000 |
| Prompt source | `data_platform/generate_features/is_structurally_complete/generate_feature.py` |
| Prompt hash | `1ba4625039f7a7f056943be4d35890fa9483bfe4d51378bccd1bdea0041925bd` |
| Accepted label values | boolean `true` or `false` |

## S3 artifacts

| Artifact | URI |
|----------|-----|
| `final.parquet` | `s3://mirrorview-experimental-artifacts/data_platform/data/bluesky/bluesky_7e2c4a91-3b5f-4d8e-a6c1-0f9b8d2e5a73/features/bluesky_2026_09_03_235130_llm_features_v1/is_structurally_complete/final.parquet` |
| `manifest.json` | `s3://mirrorview-experimental-artifacts/data_platform/data/bluesky/bluesky_7e2c4a91-3b5f-4d8e-a6c1-0f9b8d2e5a73/features/bluesky_2026_09_03_235130_llm_features_v1/is_structurally_complete/manifest.json` |
| `progress.jsonl` | `s3://mirrorview-experimental-artifacts/data_platform/data/bluesky/bluesky_7e2c4a91-3b5f-4d8e-a6c1-0f9b8d2e5a73/features/bluesky_2026_09_03_235130_llm_features_v1/is_structurally_complete/progress.jsonl` |

`final.parquet` SHA-256: `d8dfd9f51e577c7d2e505fe77e75e3be98b4cc4c7e2dfc333c7f818cd199049c`

## Run timing

| Metric | Value |
|--------|-------|
| Wall-clock start (UTC) | `2026-09-06T10:34:35Z` |
| Wall-clock end (UTC) | `2026-09-06T21:29:02Z` |
| Wall-clock hours | 10.91 |
| Throughput | 18,336 rows/hour |
| Campaign PID | 76385 (exited 0) |
| Resume or reattach events during Phase B | 0 |

## Cost

| Metric | Value |
|--------|-------|
| Smoke estimated full run (avg) | $13.304 |
| Smoke estimated full run (max) | $14.11 |
| Actual cost (101 OpenAI batches) | $13.255 |
| Input tokens | 105,052,337 |
| Output tokens | 4,400,000 |
| Pricing | Batch API `gpt-5.4-nano`: $0.10/M input, $0.625/M output |

Actual cost is 0.4% below the smoke average estimate and 6.1% below the smoke max estimate.

## Label counts

| Label | Count |
|-------|-------|
| `is_structurally_complete=true` | 192,805 |
| `is_structurally_complete=false` | 7,195 |
| **Total in final** | **200,000** |
| `failed_row_count` | 0 |

No `errors.jsonl` was written. No permanently failed ids were excluded from `final.parquet`.

## Retries and provider batches

| Metric | Value |
|--------|-------|
| Distinct OpenAI batch ids | 101 |
| Parts with more than one provider batch id | 1 (part 0: smoke batch plus full-run batch) |
| Rows with `attempt_count > 1` | 0 |
| Transient errors during Phase B | 0 |

Part 0 lists two provider batch ids (`batch_6a9cf128dba0819083d792b58ffab0a8` from Phase A smoke and `batch_6a9d41c577e4819094e3408316249a55` for the remaining 1,990 rows). This is expected, not a retry.

## final.parquet completion rule

`final.parquet` was written once every input id was labeled exactly once. `manifest.json` `final_parquet` reports `row_count=200000` and `failed_row_count=0`. The step file row-count assertion is `len(df) == 200000 - failed_row_count`, which equals `manifest.final_parquet.row_count`.

## Watcher milestones

Milestone bodies were not posted to GitHub because the run had no write token. Bodies are recorded here and in `/tmp/phaseb/is_structurally_complete/watcher/`.

| Rows | Updated (UTC) | Est. cost | Active batch |
|------|---------------|-----------|--------------|
| 12,000 | 2026_09_06-11:49:53 | $0.80 | `batch_6a9d52b43ba481908cf45dac6d20c242` |
| 20,000 | 2026_09_06-12:10:24 | $1.33 | `batch_6a9d572e87188190b42a87527b81f0b6` |
| 32,000 | 2026_09_06-12:41:08 | $2.13 | `batch_6a9d5e8ab4e481908f6d14383729ef4d` |
| 44,000 | 2026_09_06-13:48:10 | $2.93 | `batch_6a9d6e7915508190bf1739c197d9cb64` |
| 50,000 | 2026_09_06-14:13:08 | $3.46 | `batch_6a9d741d48508190a7b704058fa2130a` |
| 60,000 | 2026_09_06-14:33:22 | $3.99 | `batch_6a9d785632b8819088e0e0cfd3e16139` |
| 70,000 | 2026_09_06-15:03:43 | $4.66 | `batch_6a9d801eed6c81909146f24f2390a0ee` |
| 80,000 | 2026_09_06-15:44:09 | $5.32 | `batch_6a9d8a37ab58819083ec33e175459a0c` |
| 90,000 | 2026_09_06-16:34:43 | $5.99 | `batch_6a9d94bdfda8819089333176340c316a` |
| 100,000 | 2026_09_06-17:25:17 | $6.79 | `batch_6a9da05e867c8190b8e2333e57907be9` |
| 110,000 | 2026_09_06-18:15:53 | $7.32 | `batch_6a9dacd2bf608190a6676a24a2803c90` |
| 120,000 | 2026_09_06-19:06:29 | $8.12 | `batch_6a9db8e632c88190950a1d985b65b429` |
| 130,000 | 2026_09_06-19:26:44 | $8.78 | `batch_6a9dbd5e904c819090849a566860b42b` |
| 140,000 | 2026_09_06-19:46:56 | $9.45 | `batch_6a9dc25778048190b192407e95866aab` |
| 150,000 | 2026_09_06-19:57:02 | $9.98 | `batch_6a9dc55c82048190b774ec7c1394692b` |
| 160,000 | 2026_09_06-20:17:16 | $10.64 | `batch_6a9dc9d57808819086d22e7a743ced20` |
| 170,000 | 2026_09_06-20:37:33 | $11.44 | `batch_6a9dcf032d1481909465991828004486` |
| 180,000 | 2026_09_06-20:57:47 | $12.11 | `batch_6a9dd359b6608190ba26ca53d2c451c1` |
| 190,000 | 2026_09_06-21:17:59 | $12.90 | `batch_6a9dd812764c819091faee162608f835` |
| 200,000 | 2026_09_06-21:39:10 | $13.30 | idle |

## Validation results

All checks passed (20/20). Validation script: `/tmp/phaseb/is_structurally_complete/validate_phaseb.py`. Output: `/tmp/phaseb/is_structurally_complete/validation_output.txt`.

| Check | Result |
|-------|--------|
| Q44 columns present | pass |
| `len(df) == manifest.final_parquet.row_count` | pass (200,000) |
| `len(df) == 200000 - failed_row_count` | pass |
| Unique `source_record_id` | pass |
| Single correct `run_id` | pass |
| Boolean labels only, no nulls | pass |
| `final.parquet` SHA-256 matches manifest | pass |
| 100 batch parts `part-00000` through `part-00099`, 2,000 rows each | pass |
| All batch SHA-256 values match manifest | pass |
| Batches tagged `intermediate-artifact=true`; final/manifest/progress untagged | pass |
| `part-00000` smoke rows unchanged from `smoke/output.parquet` | pass |
| `progress.jsonl`: 100 batch lines, 1 final line | pass |
| No forbidden S3 prefixes; `active_openai_batch.json` absent | pass |
| No errors; `failed_row_count=0` | pass |

## OpenAI Batch job ids

101 distinct provider batch ids. The smoke batch id is `batch_6a9cf128dba0819083d792b58ffab0a8`. The first full-run batch id for part 0 expansion is `batch_6a9d41c577e4819094e3408316249a55`. The last batch id is `batch_6a9dda5c26b88190b6b6ec7a499c3fe4`. The full list is in `manifest.json` `batches[].provider_batch_ids`.
