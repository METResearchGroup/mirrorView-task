# is_political Phase B run report

## Approval

Phase B was approved in chat on 2026-09-06 ("Approved, run Phase B"). A comment could not be posted on the parent GitHub issue because the automation token has no write scope.

## Pinned identity

| Field | Value |
|-------|-------|
| Dataset id | `bluesky_7e2c4a91-3b5f-4d8e-a6c1-0f9b8d2e5a73` |
| Preprocessed run | `2026_09_03-23:51:30` |
| Preprocessed row count | 200,000 |
| Campaign id | `bluesky_2026_09_03_235130_llm_features_v1` |
| Feature name | `is_political` |
| Run id | `bluesky_2026_09_03_235130_llm_features_v1:is_political` |
| Model id | `gpt-5.4-nano` |
| Batch size | 2,000 |
| Prompt source | `data_platform/generate_features/is_political/generate_feature.py` |
| Prompt hash | `d1d8c0ab2c180b7fb511c67bde49de7b9c465e9d21d45210c196559ae6c958a1` |
| Accepted label values | boolean `true` or `false` |

## S3 artifacts

| Artifact | URI |
|----------|-----|
| `final.parquet` | `s3://mirrorview-experimental-artifacts/data_platform/data/bluesky/bluesky_7e2c4a91-3b5f-4d8e-a6c1-0f9b8d2e5a73/features/bluesky_2026_09_03_235130_llm_features_v1/is_political/final.parquet` |
| `manifest.json` | `s3://mirrorview-experimental-artifacts/data_platform/data/bluesky/bluesky_7e2c4a91-3b5f-4d8e-a6c1-0f9b8d2e5a73/features/bluesky_2026_09_03_235130_llm_features_v1/is_political/manifest.json` |
| `progress.jsonl` | `s3://mirrorview-experimental-artifacts/data_platform/data/bluesky/bluesky_7e2c4a91-3b5f-4d8e-a6c1-0f9b8d2e5a73/features/bluesky_2026_09_03_235130_llm_features_v1/is_political/progress.jsonl` |

`final.parquet` SHA-256: `16b075af1d0cfb8462af7725a6070d16d53463fa3027b907449e0e4a11f0efd2`

## Run timing

| Metric | Value |
|--------|-------|
| Wall-clock start (UTC) | `2026-09-06T10:34:34Z` |
| Wall-clock end (UTC) | `2026-09-06T20:46:01Z` |
| Wall-clock hours | 10.19 |
| Throughput | 19,627 rows/hour |
| Campaign PID | 76115 (exited 0) |
| Resume or reattach events during Phase B | 0 |

## Cost

| Metric | Value |
|--------|-------|
| Smoke estimated full run (avg) | $8.739 |
| Smoke estimated full run (max) | $9.545 |
| Actual cost (101 OpenAI batches) | $8.690 |
| Input tokens | 65,652,337 |
| Output tokens | 3,400,000 |
| Pricing | Batch API `gpt-5.4-nano`: $0.10/M input, $0.625/M output |

Actual cost is 0.6% below the smoke average estimate.

## Label counts

| Label | Count |
|-------|-------|
| `is_political=true` | 49,483 |
| `is_political=false` | 150,517 |
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

Part 0 lists two provider batch ids because the ten smoke rows were labeled in Phase A and the remaining 1,990 rows in part 0 were labeled in the first Phase B batch. This is expected, not a retry.

## final.parquet completion rule

`final.parquet` was written once every input id was labeled exactly once. `manifest.json` `final_parquet` reports `row_count=200000` and `failed_row_count=0`. The step file row-count assertion is `len(df) == 200000 - failed_row_count`, which equals `manifest.final_parquet.row_count`.

## Watcher milestones

Milestone bodies were not posted to GitHub because the run had no write token. Bodies are recorded here and in `/tmp/phaseb/is_political/watcher/`.

| Rows | Updated (UTC) | Est. cost | Active batch |
|------|---------------|-----------|--------------|
| 10,000 | 2026_09_06 (Phase A handoff) | — | — |
| 22,000 | 2026_09_06 (Phase A handoff) | — | — |
| 30,000 | 2026_09_06 (Phase A handoff) | — | — |
| 42,000 | 2026_09_06 (Phase A handoff) | — | — |
| 56,000 | 2026_09_06 (Phase A handoff) | — | — |
| 60,000 | 2026_09_06-14:03:03 | $2.62 | `batch_6a9d71ad277c8190973d3a3a4583b13f` |
| 70,000 | 2026_09_06-14:23:22 | $3.06 | `batch_6a9d7752f5788190bf6c679247216bbc` |
| 80,000 | 2026_09_06-14:53:45 | $3.50 | `batch_6a9d7e24ea5881908fb1be5115c78621` |
| 90,000 | 2026_09_06-15:34:12 | $3.93 | `batch_6a9d8700b54c8190b2889f0380024ed7` |
| 100,000 | 2026_09_06-16:14:36 | $4.37 | `batch_6a9d9034da1881908082b7c4bc648d4b` |
| 110,000 | 2026_09_06-17:15:20 | $4.81 | `batch_6a9d9d87f93c8190a37a437434f5e26a` |
| 120,000 | 2026_09_06-17:45:38 | $5.24 | `batch_6a9da66f1b3c8190be6f70d8f92e625f` |
| 130,000 | 2026_09_06-18:36:15 | $5.68 | `batch_6a9db1db21b881908ec27557dfb6ab3e` |
| 140,000 | 2026_09_06-19:06:35 | $6.20 | `batch_6a9db8eb95848190961019df57c9862b` |
| 150,000 | 2026_09_06-19:26:51 | $6.73 | `batch_6a9dbe3c53b48190874d5e524ec459b3` |
| 160,000 | 2026_09_06-19:36:59 | $6.99 | `batch_6a9dc0d2a9f88190ace1a2bcbd151576` |
| 170,000 | 2026_09_06-19:57:12 | $7.52 | `batch_6a9dc56865048190981eefbd5bc6ef1c` |
| 180,000 | 2026_09_06-20:17:27 | $8.04 | `batch_6a9dca2624e481909b7aea83969c4295` |
| 190,000 | 2026_09_06-20:27:35 | $8.30 | `batch_6a9dcc7ad63c8190a71505f028daf8bd` |
| 200,000 | 2026_09_06-20:47:50 | $8.74 | idle |

## Validation results

All checks passed (27/27). Validation script: `/tmp/phaseb/is_political/validate.py`. Output: `/tmp/phaseb/is_political/validation_output.txt`.

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

101 distinct provider batch ids. The smoke batch id is `batch_6a9ceb46c5ec81909998eff109642a14`. The first full-run batch id is `batch_6a9d41c379d08190835f2da3b756137b` (part 0 expansion). The last batch id is `batch_6a9dd0752e688190b899a14d4ee4abb2` (part 99). Full list is in `manifest.json` `batches[].provider_batch_ids`.
