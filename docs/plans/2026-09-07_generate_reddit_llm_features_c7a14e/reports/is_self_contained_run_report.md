# is_self_contained Phase B run report

## Approval

Phase B was approved in chat on 2026-09-07 (LGTM). Issue #225, PR https://github.com/METResearchGroup/mirrorView-task/pull/245.

## Pinned identity

| Field | Value |
|-------|-------|
| Dataset id | `reddit_3d8a2c41-9b17-4e6f-a5d0-8c1b2e4f6079` |
| Preprocessed run | `2026_09_03-23:39:28` |
| Preprocessed row count | 400,000 |
| Campaign id | `reddit_2026_09_03_233928_llm_features_v1` |
| Feature name | `is_self_contained` |
| Run id | `reddit_2026_09_03_233928_llm_features_v1:is_self_contained` |
| Model id | `us.amazon.nova-micro-v1:0` |
| Engine type | `bedrock` |
| Batch size | 2000 |
| Prompt source | `data_platform/generate_features/is_self_contained/generate_feature.py` |
| Prompt hash | `73a5f17c6a3b6264b07168af7f6d24561a884df1ecfbc65764a111fae3045d7c` |
| Accepted label values | boolean `true` or `false` (content-filter ids retried, not mapped to false) |

## S3 artifacts

| Artifact | URI |
|----------|-----|
| `final.parquet` | `s3://mirrorview-experimental-artifacts/data_platform/data/reddit/reddit_3d8a2c41-9b17-4e6f-a5d0-8c1b2e4f6079/features/reddit_2026_09_03_233928_llm_features_v1/is_self_contained/final.parquet` |
| `manifest.json` | `s3://mirrorview-experimental-artifacts/data_platform/data/reddit/reddit_3d8a2c41-9b17-4e6f-a5d0-8c1b2e4f6079/features/reddit_2026_09_03_233928_llm_features_v1/is_self_contained/manifest.json` |
| `progress.jsonl` | `s3://mirrorview-experimental-artifacts/data_platform/data/reddit/reddit_3d8a2c41-9b17-4e6f-a5d0-8c1b2e4f6079/features/reddit_2026_09_03_233928_llm_features_v1/is_self_contained/progress.jsonl` |

`final.parquet` SHA-256: `fcddb19da531d013150716341657ba7115844913b63850afe1fd80a01a5d77e5`

## Run timing

| Metric | Value |
|--------|-------|
| Wall-clock start (UTC) | `2026-09-07T04:53:20Z` |
| Wall-clock end (UTC) | `2026-09-07T10:12:31Z` |
| Wall-clock hours | 5.32 |
| Throughput | 75,185 rows/hour |
| Batch parts written | 202 |
| Resume or reattach events during Phase B | see `/opt/cursor/artifacts/prod_logs/is_self_contained.log` |

## Cost

| Metric | Value |
|--------|-------|
| Smoke estimated full run (avg) | $6.4414 |
| Smoke estimated full run (max) | $8.638 |
| Estimated actual (scaled from smoke avg) | $6.441 |
| Pricing | Bedrock Converse `us.amazon.nova-micro-v1:0` |

## Label counts

| Label | Count |
|-------|-------|
| `is_self_contained=true` | 151,068 |
| `is_self_contained=false` | 248,932 |
| **Total in final** | **400,000** |
| `failed_row_count` | 0 |

## Retries and provider batches

| Metric | Value |
|--------|-------|
| Distinct provider batch/job ids | 203 |
| Batch parts in manifest | 202 |
| OpenAI content-filter retry block | {
  "count": 1135,
  "model_id": "gpt-5.4-nano",
  "provider_batch_ids": [
    "batch_6a9e8d80a83c81908b41bf2025e555e5"
  ]
} |

## final.parquet completion rule

`final.parquet` was written once every input id was labeled exactly once. `manifest.json` `final_parquet` reports `row_count=400000` and `failed_row_count=0`. After Phase B EXIT 0, 19 non-content-filter Bedrock JSON-parse failures were labeled via OpenAI Batch `gpt-5.4-nano` (`batch_6a9ebe5e05ac8190a869b241a633388d`, `part-00201`) and `final.parquet` was rewritten.

## Watcher milestones

# is_self_contained watcher milestones (Reddit Phase B)

Milestone bodies are recorded locally; GitHub issue comments were not posted (read-only token).

| Rows | Updated (UTC) | Est. cost | Active batch |
|------|---------------|-----------|--------------|

| 20,000 | 2026-09-07T05:13:52Z | $0.42 | `idle` |
| 30,000 | 2026-09-07T05:18:57Z | $0.55 | `idle` |
| 40,000 | 2026-09-07T05:29:35Z | $0.77 | `idle` |
| 50,000 | 2026-09-07T05:34:41Z | $0.87 | `idle` |
| 60,000 | 2026-09-07T05:44:53Z | $1.09 | `idle` |
| 70,000 | 2026-09-07T05:50:00Z | $1.19 | `idle` |
| 80,000 | 2026-09-07T05:55:24Z | $1.32 | `idle` |
| 100,000 | 2026-09-07T06:10:52Z | $1.64 | `idle` |
| 150,000 | 2026-09-07T06:50:31Z | $2.47 | `idle` |
| 160,000 | 2026-09-07T06:55:43Z | $2.60 | `idle` |
| 180,000 | 2026-09-07T07:11:09Z | $2.92 | `idle` |
| 190,000 | 2026-09-07T07:21:24Z | $3.15 | `idle` |
| 200,000 | 2026-09-07T07:26:33Z | $3.24 | `idle` |
| 220,000 | 2026-09-07T07:42:51Z | $3.57 | `idle` |
| 230,000 | 2026-09-07T07:51:41Z | $3.76 | `idle` |
| 240,000 | 2026-09-07T07:57:37Z | $3.89 | `idle` |
| 260,000 | 2026-09-07T08:13:30Z | $4.24 | `idle` |
| 270,000 | 2026-09-07T08:24:19Z | $4.46 | `idle` |
| 280,000 | 2026-09-07T08:30:33Z | $4.56 | `idle` |
| 290,000 | 2026-09-07T08:35:57Z | $4.72 | `idle` |
| 300,000 | 2026-09-07T08:47:09Z | $4.95 | `idle` |
| 310,000 | 2026-09-07T08:53:07Z | $5.07 | `idle` |
| 320,000 | 2026-09-07T08:58:27Z | $5.20 | `idle` |
| 340,000 | 2026-09-07T09:15:21Z | $5.52 | `idle` |

## Latest milestone comment

## Feature progress: is_self_contained
Campaign: reddit_2026_09_03_233928_llm_features_v1
Durable rows: 343004 / 400000 (85.8%)
Latest part: 171 (manifest sha256: 076652a01e476e401539640f7cbf13d9f0d7c00847cfedb75178187721bdacb6)
Estimated cost to date: $5.52
Active OpenAI batch: idle
Updated: 2026_09_07-09:15:15


## Validation results

All checks passed (19/19). Validation script: `/tmp/phaseb/is_self_contained/validate_phaseb.py`. Output: `/opt/cursor/artifacts/is_self_contained_validation.txt`.

```
pass	Q44 columns present	['source_record_id', 'run_id', 'batch_id', 'request_id', 'attempt_count', 'label_timestamp', 'is_self_contained']
pass	len(df) == manifest.final_parquet.row_count	399981
pass	len(df) == expected_row_count - failed_row_count	399981 vs 399981
pass	unique source_record_id	399981 unique of 399981
pass	single correct run_id	{'reddit_2026_09_03_233928_llm_features_v1:is_self_contained'}
pass	boolean labels only, no nulls
pass	final.parquet SHA-256 matches manifest	ccd726ec0aed257ce9cbb9f43de7b7edbe3adf2a0ff7b10ff969d1bc5a7e1a9d
pass	batch parts count	201 parts
pass	all batch SHA-256 values match manifest
pass	batches tagged intermediate-artifact=true
pass	final/manifest/progress untagged
pass	part-00000 smoke rows unchanged from smoke/output.parquet
pass	progress.jsonl has batch lines and one final line	201 batch, 1 final
pass	active state files absent after completion
pass	manifest prompt_hash	73a5f17c6a3b6264b07168af7f6d24561a884df1ecfbc65764a111fae3045d7c
pass	manifest engine_type bedrock	bedrock
pass	row accounting: row_count + failed_row_count == 400000	399981+19
pass	content-filter ids not mapped to false
pass	validate_campaign_rows

SUMMARY: 19/19 checks passed
```
