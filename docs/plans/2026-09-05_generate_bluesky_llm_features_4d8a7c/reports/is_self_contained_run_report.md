# is_self_contained Phase B run report

## Approval

Phase B was approved in chat on 2026-09-06 ("Approved, run Phase B"). A comment could not be posted on the parent GitHub issue because the automation token has no write scope.

## Pinned identity

| Field | Value |
|-------|-------|
| Dataset id | `bluesky_7e2c4a91-3b5f-4d8e-a6c1-0f9b8d2e5a73` |
| Preprocessed run | `2026_09_03-23:51:30` |
| Preprocessed row count | 200,000 |
| Campaign id | `bluesky_2026_09_03_235130_llm_features_v1` |
| Feature name | `is_self_contained` |
| Run id | `bluesky_2026_09_03_235130_llm_features_v1:is_self_contained` |
| Model id | `gpt-5.4-nano` |
| Batch size | 2,000 |
| Prompt source | `data_platform/generate_features/is_self_contained/generate_feature.py` |
| Prompt hash | `73a5f17c6a3b6264b07168af7f6d24561a884df1ecfbc65764a111fae3045d7c` |
| Accepted label values | boolean `true` or `false` |

## S3 artifacts

| Artifact | URI |
|----------|-----|
| `final.parquet` | `s3://mirrorview-experimental-artifacts/data_platform/data/bluesky/bluesky_7e2c4a91-3b5f-4d8e-a6c1-0f9b8d2e5a73/features/bluesky_2026_09_03_235130_llm_features_v1/is_self_contained/final.parquet` |
| `manifest.json` | `s3://mirrorview-experimental-artifacts/data_platform/data/bluesky/bluesky_7e2c4a91-3b5f-4d8e-a6c1-0f9b8d2e5a73/features/bluesky_2026_09_03_235130_llm_features_v1/is_self_contained/manifest.json` |
| `progress.jsonl` | `s3://mirrorview-experimental-artifacts/data_platform/data/bluesky/bluesky_7e2c4a91-3b5f-4d8e-a6c1-0f9b8d2e5a73/features/bluesky_2026_09_03_235130_llm_features_v1/is_self_contained/progress.jsonl` |

`final.parquet` SHA-256: `197730b899d72bd4d19779491f7559a2a44e3156cfcec0befeb752c332df7e80`

## Run timing

| Metric | Value |
|--------|-------|
| Wall-clock start (UTC) | `2026-09-06T10:34:40Z` |
| Wall-clock end (UTC) | `2026-09-06T21:00:25Z` |
| Wall-clock hours | 10.43 |
| Throughput | 19,177 rows/hour |
| Campaign PID | 76708 (exited 0) |
| Resume or reattach events during Phase B | 0 |

## Cost

| Metric | Value |
|--------|-------|
| Smoke estimated full run (avg) | $11.409 |
| Smoke estimated full run (max) | $12.215 |
| Actual cost (101 OpenAI batches) | $11.360 |
| Input tokens | 89,852,337 |
| Output tokens | 3,800,000 |
| Pricing | Batch API `gpt-5.4-nano`: $0.10/M input, $0.625/M output |

Actual cost is 0.4% below the smoke average estimate and 6.9% below the smoke max estimate.

## Label counts

| Label | Count |
|-------|-------|
| `is_self_contained=true` | 114,921 |
| `is_self_contained=false` | 85,079 |
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

Part 0 lists two provider batch ids (`batch_6a9cef0347188190b69a49dffd2e2060` from Phase A smoke and `batch_6a9d41c97bb48190b64d4f8edd184e06` for the remaining 1,990 rows). This is expected, not a retry.

## final.parquet completion rule

`final.parquet` was written once every input id was labeled exactly once. `manifest.json` `final_parquet` reports `row_count=200000` and `failed_row_count=0`. The step file row-count assertion is `len(df) == 200000 - failed_row_count`, which equals `manifest.final_parquet.row_count`.

## Watcher milestones

Milestone bodies were not posted to GitHub because the run had no write token. Bodies are recorded here and in `/tmp/phaseb/is_self_contained/watcher/`.

| Rows | Updated (UTC) | Est. cost | Active batch |
|------|---------------|-----------|--------------|
| 10,000 | 2026_09_06-11:21:26 | $0.57 | `batch_6a9d4b8229e88190963a1c9ba0a30859` |
| 20,000 | 2026_09_06-11:52:03 | $1.14 | `batch_6a9d53cfe0348190ac2b811762729635` |
| 30,000 | 2026_09_06-12:22:45 | $1.94 | `batch_6a9d5b12c2248190b14bb95ba39a26e3` |
| 40,000 | 2026_09_06-12:43:25 | $2.28 | `batch_6a9d5eb312f48190957b0d29eed3bf29` |
| 50,000 | 2026_09_06-13:48:12 | $2.97 | `batch_6a9d6e7c0dd08190b72ead259df3beac` |
| 60,000 | 2026_09_06-14:13:08 | $3.42 | `batch_6a9d74606ff481908ea19d47e421d0c7` |
| 70,000 | 2026_09_06-14:43:35 | $4.11 | `batch_6a9d7b17870481909dda795e12ca6195` |
| 80,000 | 2026_09_06-15:03:49 | $4.56 | `batch_6a9d7ff3c5288190b0dbead655c4ffbd` |
| 90,000 | 2026_09_06-15:34:09 | $5.25 | `batch_6a9d8793251c81909caf61502d5d6592` |
| 100,000 | 2026_09_06-16:04:33 | $5.70 | `batch_6a9d8e70a3fc8190ba033f96a859d99f` |
| 110,000 | 2026_09_06-16:45:01 | $6.27 | `batch_6a9d9778cd74819099583d49f9c0a989` |
| 120,000 | 2026_09_06-17:25:30 | $6.85 | `batch_6a9da0b357cc819088ec025d8c638247` |
| 130,000 | 2026_09_06-18:26:13 | $7.42 | `batch_6a9db00692448190acaa5070688cca1e` |
| 140,000 | 2026_09_06-19:06:38 | $7.99 | `batch_6a9db98345408190a8c645b79c268abb` |
| 150,000 | 2026_09_06-19:26:53 | $8.56 | `batch_6a9dbe3f40608190a9d7d13a3581e5a4` |
| 160,000 | 2026_09_06-19:57:14 | $9.47 | `batch_6a9dc58ba0108190825f125df8a0ac08` |
| 170,000 | 2026_09_06-20:07:20 | $9.81 | `batch_6a9dc7d6af4481909f93775836b7ffbe` |
| 180,000 | 2026_09_06-20:27:36 | $10.38 | `batch_6a9dcc628a488190b4693a970cb3e2af` |
| 190,000 | 2026_09_06-20:47:49 | $10.95 | `batch_6a9dd0dbedb88190ac5a76f09775fece` |
| 200,000 | 2026_09_06-21:08:08 | $11.41 | idle |

## Validation results

All checks passed (19/19). Validation script: `/tmp/phaseb/is_self_contained/validate_phaseb.py`. Output: `/tmp/phaseb/is_self_contained/validation_output.txt`.

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

101 distinct provider batch ids. The smoke batch id is `batch_6a9cef0347188190b69a49dffd2e2060`. The first full-run batch id for part 0 expansion is `batch_6a9d41c97bb48190b64d4f8edd184e06`. The last batch id is in `manifest.json` `batches[99].provider_batch_ids`. Full list is in `manifest.json` `batches[].provider_batch_ids`.
