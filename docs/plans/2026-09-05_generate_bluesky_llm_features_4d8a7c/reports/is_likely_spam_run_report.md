# is_likely_spam Phase B run report

## Approval

Phase B started after explicit chat approval on 2026-09-06 ("Approved, run Phase B"). The parent campaign issue comment could not be posted because the GitHub token in this environment has no write scope.

## Pinned identity

| Field | Value |
|-------|-------|
| Dataset id | `bluesky_7e2c4a91-3b5f-4d8e-a6c1-0f9b8d2e5a73` |
| Preprocessed run | `2026_09_03-23:51:30` |
| Preprocessed row count | 200,000 |
| Campaign id | `bluesky_2026_09_03_235130_llm_features_v1` |
| Feature name | `is_likely_spam` |
| Run id | `bluesky_2026_09_03_235130_llm_features_v1:is_likely_spam` |
| Model id | `gpt-5.4-nano` |
| Batch size | 2,000 |
| Prompt source | `data_platform/generate_features/is_likely_spam/generate_feature.py` → `SYSTEM_PROMPT` |
| Prompt hash | `72438f2de05156168dd30f53dcac7e3008fa9c5c9ea223266e78086a500bbbf6` |

## S3 artifacts

| Object | URI |
|--------|-----|
| final.parquet | `s3://mirrorview-experimental-artifacts/data_platform/data/bluesky/bluesky_7e2c4a91-3b5f-4d8e-a6c1-0f9b8d2e5a73/features/bluesky_2026_09_03_235130_llm_features_v1/is_likely_spam/final.parquet` |
| manifest.json | `s3://mirrorview-experimental-artifacts/data_platform/data/bluesky/bluesky_7e2c4a91-3b5f-4d8e-a6c1-0f9b8d2e5a73/features/bluesky_2026_09_03_235130_llm_features_v1/is_likely_spam/manifest.json` |
| progress.jsonl | `s3://mirrorview-experimental-artifacts/data_platform/data/bluesky/bluesky_7e2c4a91-3b5f-4d8e-a6c1-0f9b8d2e5a73/features/bluesky_2026_09_03_235130_llm_features_v1/is_likely_spam/progress.jsonl` |

## Run summary

| Metric | Value |
|--------|-------|
| Wall-clock start | 2026-09-06T10:34:44Z |
| Wall-clock end | 2026-09-06T21:08:12Z |
| Wall-clock hours | 10.56 |
| Rows in final.parquet | 200,000 |
| failed_row_count | 0 |
| Throughput | 18,943 rows/hour |
| Provider batch ids (distinct) | 101 |
| Phase B resume/reattach events | 0 |

The campaign process (PID 76987) ran once from start to finish with exit code 0. No Phase B crashes, stalls, or manual resumes occurred. Part 0 lists two provider batch ids (smoke batch plus the first production batch), which is expected per the step contract.

## Label counts

| is_likely_spam | Count |
|----------------|------:|
| false | 198,856 |
| true | 1,144 |

## Cost

| Metric | Value |
|--------|-------|
| Smoke estimated full run (avg) | $9.244 |
| Smoke estimated full run (max) | $10.05 |
| Actual input tokens | 64,452,337 |
| Actual output tokens | 4,400,000 |
| Actual cost (gpt-5.4-nano Batch pricing) | $9.195 |
| Pricing source | https://developers.openai.com/api/docs/pricing |
| Batch input USD per million tokens | $0.10 |
| Batch output USD per million tokens | $0.625 |

Actual cost came in slightly below the smoke average estimate.

## Retries and errors

| Metric | Value |
|--------|-------|
| errors_total | 0 |
| errors_transient_like | 0 |
| Parts with more than one provider batch id | part 0 only (smoke + production) |
| Rows with attempt_count > 1 | 0 |

No permanently failed ids were recorded. `errors.jsonl` is absent.

## final.parquet completion rule

`final.parquet` was written once every input id was labeled exactly once. `manifest.json` `final_parquet` reports `row_count` 200,000 and `failed_row_count` 0, so `row_count + failed_row_count == 200,000`. Failed ids are excluded from the parquet file.

## Watcher milestones

Milestone bodies were not posted to GitHub because this run had no write token. The watcher ran locally at each 10,000-row boundary and saved rolling comment text under `/tmp/phaseb/is_likely_spam/watcher/`.

| Rows | Updated (UTC) | Est. cost | Active batch |
|-----:|---------------|----------:|--------------|
| 10,000 | 2026_09_06-11:26:40 | $0.46 | batch_6a9d4bd1e1948190a844475042cbf2c3 |
| 20,000 | 2026_09_06-11:57:35 | $0.92 | batch_6a9d54d209d08190ba8dbbe90f7f9e20 |
| 30,000 | 2026_09_06-12:28:26 | $1.39 | batch_6a9d5b4415948190816c9a587219db8f |
| 40,000 | 2026_09_06-12:59:14 | $1.94 | batch_6a9d620ece7c8190902041bb86c27446 |
| 50,000 | 2026_09_06-13:48:08 | $2.31 | batch_6a9d6e7abc288190a979bfd7e88b558e |
| 60,000 | 2026_09_06-14:23:13 | $2.87 | batch_6a9d7683edd481908db7936aab47172c |
| 70,000 | 2026_09_06-14:53:36 | $3.24 | batch_6a9d7d83ccf08190a9aa59535ea1bb29 |
| 80,000 | 2026_09_06-15:34:05 | $3.79 | batch_6a9d875f834481909fb0ab7a3b5e0ca0 |
| 90,000 | 2026_09_06-16:04:26 | $4.16 | batch_6a9d8eabffc88190a87200d421025918 |
| 100,000 | 2026_09_06-16:44:59 | $4.62 | batch_6a9d96d2e06481909c9ad8bd0f2d9d34 |
| 110,000 | 2026_09_06-17:25:27 | $5.08 | batch_6a9da1ee3e308190b78887169a3f06aa |
| 120,000 | 2026_09_06-17:55:49 | $5.55 | batch_6a9da8ea566c819095a0a74e4f4017ab |
| 130,000 | 2026_09_06-18:36:14 | $6.01 | batch_6a9db2020308819084fc6b18e44a1939 |
| 140,000 | 2026_09_06-19:06:41 | $6.56 | batch_6a9db98a9cc0819092bbc1ea6f8e2d01 |
| 150,000 | 2026_09_06-19:26:55 | $6.93 | batch_6a9dbe37cfc081909f3b97561ddd1953 |
| 160,000 | 2026_09_06-19:47:07 | $7.40 | batch_6a9dc306b40c8190bc8f702eaddb9c20 |
| 170,000 | 2026_09_06-20:07:24 | $7.95 | batch_6a9dc762beec81908bcc54bc938e31cb |
| 180,000 | 2026_09_06-20:27:41 | $8.50 | batch_6a9dcc9fb730819082eef11649e82692 |
| 190,000 | 2026_09_06-20:47:54 | $8.97 | batch_6a9dd146a2508190be566c1ea4e58a32 |
| 200,000 | 2026_09_06-21:08:12 | $9.24 | idle |

## Validation results

Validation ran with boto3 downloads to `/tmp/phaseb/is_likely_spam/` on 2026-09-06 after completion.

| Check | Result |
|-------|--------|
| final.parquet SHA-256 matches manifest | PASS |
| Q44 columns present and ordered | PASS |
| Row count == 200,000 - failed_row_count | PASS |
| Row count matches manifest.final_parquet.row_count | PASS |
| Unique source_record_id | PASS |
| Single correct run_id | PASS |
| No null labels; boolean values only | PASS |
| 100 batch objects part-00000..part-00099 | PASS |
| Each batch 2,000 rows; sum 200,000 | PASS |
| Batch SHA-256 matches manifest entries | PASS |
| Batch objects tagged intermediate-artifact=true | PASS |
| final.parquet, manifest.json, progress.jsonl untagged | PASS |
| progress.jsonl: 100 batch lines + 1 final line | PASS |
| part-00000: 10 unchanged smoke rows + 1,990 new rows | PASS |
| No forbidden prefix objects | PASS |
| active_openai_batch.json absent after completion | PASS |

Label value counts from validation: `false` 198,856, `true` 1,144.
