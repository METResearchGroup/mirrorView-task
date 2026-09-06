# is_news_or_opinion Phase B run report

## Approval

Phase B was approved in chat on 2026-09-06 ("Approved, run Phase B"). A comment could not be posted on the parent GitHub issue because the automation token has no write scope.

## Pinned identity

| Field | Value |
|-------|-------|
| Dataset id | `bluesky_7e2c4a91-3b5f-4d8e-a6c1-0f9b8d2e5a73` |
| Preprocessed run | `2026_09_03-23:51:30` |
| Preprocessed row count | 200,000 |
| Campaign id | `bluesky_2026_09_03_235130_llm_features_v1` |
| Feature name | `is_news_or_opinion` |
| Run id | `bluesky_2026_09_03_235130_llm_features_v1:is_news_or_opinion` |
| Model id | `gpt-5.4-nano` |
| Batch size | 2,000 |
| Prompt source | `data_platform/generate_features/is_news_or_opinion/generate_feature.py` |
| Prompt hash | `dcf52b33629bac70030fd8db9707824c38ff917f4acc65617a035c1e142acbf6` |
| Accepted label values | `news`, `opinion`, `neither` |

## S3 artifacts

| Artifact | URI |
|----------|-----|
| `final.parquet` | `s3://mirrorview-experimental-artifacts/data_platform/data/bluesky/bluesky_7e2c4a91-3b5f-4d8e-a6c1-0f9b8d2e5a73/features/bluesky_2026_09_03_235130_llm_features_v1/is_news_or_opinion/final.parquet` |
| `manifest.json` | `s3://mirrorview-experimental-artifacts/data_platform/data/bluesky/bluesky_7e2c4a91-3b5f-4d8e-a6c1-0f9b8d2e5a73/features/bluesky_2026_09_03_235130_llm_features_v1/is_news_or_opinion/manifest.json` |
| `progress.jsonl` | `s3://mirrorview-experimental-artifacts/data_platform/data/bluesky/bluesky_7e2c4a91-3b5f-4d8e-a6c1-0f9b8d2e5a73/features/bluesky_2026_09_03_235130_llm_features_v1/is_news_or_opinion/progress.jsonl` |

`final.parquet` SHA-256: `3f6df9aa274200699b9f9fc629b4f4ef30842904f1513a845744fa6815810578`

## Run timing

| Metric | Value |
|--------|-------|
| Wall-clock start (UTC) | `2026-09-06T10:34:00Z` |
| Wall-clock end (UTC) | `2026-09-06T21:07:50Z` |
| Wall-clock hours | 10.56 |
| Throughput | 18,932 rows/hour |
| Campaign PID | 75472 (exited 0) |
| Resume or reattach events during Phase B | 0 |

## Cost

| Metric | Value |
|--------|-------|
| Smoke estimated full run (avg) | $9.022 |
| Smoke estimated full run (max) | $9.890 |
| Actual cost (101 OpenAI batches) | $9.021 |
| Input tokens | 67,852,337 |
| Output tokens | 3,577,867 |
| Pricing | Batch API `gpt-5.4-nano`: $0.10/M input, $0.625/M output |

Actual cost matches the smoke average estimate within rounding (0.001% below).

## Label counts

| Label | Count |
|-------|-------|
| `neither` | 100,139 |
| `opinion` | 77,728 |
| `news` | 22,133 |
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

Milestone bodies were not posted to GitHub because the run had no write token. Bodies are recorded here and in `/tmp/phaseb/is_news_or_opinion/watcher/`.

| Rows | Updated (UTC) | Est. cost | Active batch |
|------|---------------|-----------|--------------|
| 12,000 | 2026_09_06-11:39:10 | $0.54 | `batch_6a9d502d192c8190bd053f2a715094e8` |
| 20,000 | 2026_09_06-11:59:46 | $0.90 | `batch_6a9d559856f4819083b35d8dee74c068` |
| 30,000 | 2026_09_06-12:30:33 | $1.35 | `batch_6a9d5b67ad84819081766c48fa61f8d8` |
| 40,000 | 2026_09_06-13:48:01 | $2.17 | `batch_6a9d6e796e408190a907d282cc0d05f0` |
| 50,000 | 2026_09_06-14:03:02 | $2.35 | `batch_6a9d71d4f0f48190b7705482ddfc4601` |
| 60,000 | 2026_09_06-14:33:25 | $2.71 | `batch_6a9d79343a848190a8590b941c9b9dc6` |
| 70,000 | 2026_09_06-15:03:47 | $3.25 | `batch_6a9d802142d08190964238d42005a397` |
| 80,000 | 2026_09_06-15:44:13 | $3.70 | `batch_6a9d891ddda081909d91d33603e3ba77` |
| 90,000 | 2026_09_06-16:14:33 | $4.15 | `batch_6a9d915dac048190afc6f7b8f81531a4` |
| 100,000 | 2026_09_06-16:54:59 | $4.51 | `batch_6a9d9a6bdc808190a03aa62320b18d5d` |
| 110,000 | 2026_09_06-17:45:33 | $5.05 | `batch_6a9da68e7bb08190857c9145c5f49bcf` |
| 120,000 | 2026_09_06-18:15:52 | $5.41 | `batch_6a9dac3f8fe48190b26be14f5d869290` |
| 130,000 | 2026_09_06-18:46:13 | $5.86 | `batch_6a9db4ee6e288190ae560596a351354c` |
| 140,000 | 2026_09_06-19:16:34 | $6.50 | `batch_6a9dbba3256881908999a620dd350ea5` |
| 150,000 | 2026_09_06-19:26:40 | $6.77 | `batch_6a9dbdd3a8c88190bf6232e83f2c391e` |
| 160,000 | 2026_09_06-19:46:53 | $7.22 | `batch_6a9dc317b18481908773a734e13b792c` |
| 170,000 | 2026_09_06-20:07:06 | $7.76 | `batch_6a9dc7c7e640819097861c537644b015` |
| 180,000 | 2026_09_06-20:27:20 | $8.21 | `batch_6a9dcbe8cbe88190bb368042217c8056` |
| 190,000 | 2026_09_06-20:47:34 | $8.66 | `batch_6a9dd09883cc81908ec265e728d7dd00` |
| 200,000 | 2026_09_06-21:07:50 | $9.02 | idle |

## Validation results

All checks passed (424/424). Validation script: `/tmp/phaseb/is_news_or_opinion/validate.py`. Output: `/tmp/phaseb/is_news_or_opinion/validation_output.json`.

| Check | Result |
|-------|--------|
| Q44 columns present | pass |
| `len(df) == manifest.final_parquet.row_count` | pass (200,000) |
| `len(df) == 200000 - failed_row_count` | pass |
| Unique `source_record_id` | pass |
| Single correct `run_id` | pass |
| Accepted `category` values only, no nulls | pass |
| `final.parquet` SHA-256 matches manifest | pass |
| 100 batch parts `part-00000` through `part-00099`, 2,000 rows each | pass |
| All batch SHA-256 values match manifest | pass |
| Batches tagged `intermediate-artifact=true`; final/manifest/progress untagged | pass |
| `part-00000` smoke rows unchanged from `smoke/output.parquet` | pass |
| `progress.jsonl`: 100 batch lines, 1 final line | pass |
| No forbidden S3 prefixes; `active_openai_batch.json` absent | pass |
| No errors; `failed_row_count=0` | pass |

## OpenAI Batch job ids

101 distinct provider batch ids. The smoke batch id is `batch_6a9ce87d52c88190ac7fa4a6e8950e6d`. The first full-run batch id is `batch_6a9d41a2a60881909f5782649ecfd3aa` (part 0 expansion). The last batch id is `batch_6a9dd33290fc8190b0c83da750be371e` (part 99). Full list is in `manifest.json` `batches[].provider_batch_ids`.
