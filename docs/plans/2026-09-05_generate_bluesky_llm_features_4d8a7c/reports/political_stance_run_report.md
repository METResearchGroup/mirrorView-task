# political_stance run report

Phase B full run for issue #193. Chat approval on 2026-09-06 ("Approved, run Phase B"). No issue comment was posted because the GitHub token had no write scope.

## Identity

| Field | Value |
| --- | --- |
| Dataset id | `bluesky_7e2c4a91-3b5f-4d8e-a6c1-0f9b8d2e5a73` |
| Preprocessed run | `2026_09_03-23:51:30` |
| Campaign id | `bluesky_2026_09_03_235130_llm_features_v1` |
| Feature | `political_stance` |
| Run id | `bluesky_2026_09_03_235130_llm_features_v1:political_stance` |
| Model | `gpt-5.4-nano` |
| Prompt path | `data_platform/generate_features/political_stance/generate_feature.py` |
| Prompt hash | `706ada488b0308fc4ad34cf7556b6a7d581624cb8cf24b26e018723629037687` |
| Batch size | 2000 |
| Wall clock start | 2026-09-06T10:34:53Z |
| Wall clock end | 2026-09-06T20:48:28Z |
| Wall clock hours | 10.23 |

## S3 artifacts

| Artifact | URI |
| --- | --- |
| final.parquet | `s3://mirrorview-experimental-artifacts/data_platform/data/bluesky/bluesky_7e2c4a91-3b5f-4d8e-a6c1-0f9b8d2e5a73/features/bluesky_2026_09_03_235130_llm_features_v1/political_stance/final.parquet` |
| manifest.json | `s3://mirrorview-experimental-artifacts/data_platform/data/bluesky/bluesky_7e2c4a91-3b5f-4d8e-a6c1-0f9b8d2e5a73/features/bluesky_2026_09_03_235130_llm_features_v1/political_stance/manifest.json` |
| progress.jsonl | `s3://mirrorview-experimental-artifacts/data_platform/data/bluesky/bluesky_7e2c4a91-3b5f-4d8e-a6c1-0f9b8d2e5a73/features/bluesky_2026_09_03_235130_llm_features_v1/political_stance/progress.jsonl` |

final.parquet SHA-256: `302a8be18289b79213763f206a5c109d257a4f65f93ef4b364cbc73b3bddf017`

## final.parquet completion rule

`final.parquet` was written once every input id was labeled exactly once. No ids were permanently failed, so `failed_row_count` is 0 and `row_count` is 200,000. The sum `row_count + failed_row_count` equals 200,000.

## Run outcome

| Metric | Value |
| --- | --- |
| Rows in final.parquet | 200,000 |
| failed_row_count | 0 |
| Error rate | 0.00% |
| Retries (attempt_count > 1 in final) | 0 |
| Parts with more than one provider batch id | 1 (part-00000: smoke batch plus first production batch) |
| Resume or reattach events during Phase B | 0 |
| Campaign exit code | 0 |

## Label counts

| Label | Count |
| --- | --- |
| unclear | 151,884 |
| neutral | 32,636 |
| left | 12,738 |
| right | 2,742 |

## Cost

| Metric | Value |
| --- | --- |
| Smoke estimated full run (avg) | $11.844 |
| Smoke estimated full run (max) | $12.70 |
| Actual full run cost | $11.815161 |
| Total input tokens | 93,452,337 |
| Total output tokens | 3,951,884 |
| Pricing source | https://developers.openai.com/api/docs/pricing |
| Input price (Batch) | $0.10 per million tokens |
| Output price (Batch) | $0.625 per million tokens |
| Throughput | 19,557 rows per hour |

Actual cost came in slightly below the smoke average estimate.

## OpenAI Batch job ids

100 production parts used 100 provider batches. Part-00000 also references the Phase A smoke batch `batch_6a9cf33f930c81909fb1a0814dcb4979`, for a total of 101 distinct provider batch ids in the manifest. Production batches run from `batch_6a9d41d65fb08190923cde6c3b1d47be` through `batch_6a9dd031a0bc8190b178f095c5b9638c`.

## Watcher milestones

Milestone comment bodies were saved locally because the run had no GitHub write token. They were not posted to issue #193.

| Durable rows | Updated (UTC) | Est. cost to date | Active batch |
| --- | --- | --- | --- |
| 10,000 | 2026_09_06-11:19:06 | $0.59 | batch_6a9d4b3e72308190bcd7fae536f1f064 |
| 20,000 | 2026_09_06-11:49:53 | $1.18 | batch_6a9d52d699448190a03208c6533978a2 |
| 32,000 | 2026_09_06-12:20:42 | $1.90 | batch_6a9d5a0ab8808190bffc6de82352a9b9 |
| 40,000 | 2026_09_06-12:41:18 | $2.37 | batch_6a9d5e899ae8819086f02ee148ff1dd5 |
| 52,000 | 2026_09_06-13:48:09 | $3.08 | batch_6a9d6e7c8af48190aafcf33e9c9c29a6 |
| 60,000 | 2026_09_06-14:13:16 | $3.55 | batch_6a9d74a8f44c81908172e699e2c0bf88 |
| 70,000 | 2026_09_06-14:53:47 | $4.26 | batch_6a9d7da329a881909cb345ba357bea6b |
| 80,000 | 2026_09_06-15:14:02 | $4.74 | batch_6a9d8228e4388190a74be1b02ddb2b4e |
| 90,000 | 2026_09_06-15:44:31 | $5.33 | batch_6a9d8977904481908c3c9ef9117580dd |
| 100,000 | 2026_09_06-16:14:54 | $5.92 | batch_6a9d909d653481909b6efbd8008f0aa3 |
| 110,000 | 2026_09_06-16:45:18 | $6.51 | batch_6a9d98944c648190a2cca9575805c2dc |
| 120,000 | 2026_09_06-17:46:07 | $7.11 | batch_6a9da5ccdc888190a0bba087699ffb8e |
| 130,000 | 2026_09_06-18:26:39 | $7.82 | batch_6a9db03ba990819081d85c4653a2971b |
| 140,000 | 2026_09_06-19:07:06 | $8.41 | batch_6a9db94730288190885dfd0f60883b63 |
| 150,000 | 2026_09_06-19:27:22 | $9.12 | batch_6a9dbe2965dc8190813d12923804e7e9 |
| 160,000 | 2026_09_06-19:37:29 | $9.48 | batch_6a9dc0b727748190ab613fd509513704 |
| 170,000 | 2026_09_06-19:57:42 | $10.19 | batch_6a9dc524e6c08190b2909ee2a8c2c811 |
| 180,000 | 2026_09_06-20:18:05 | $10.90 | batch_6a9dca00a36c8190b212ff49dd90ae6b |
| 190,000 | 2026_09_06-20:28:13 | $11.25 | batch_6a9dccc206fc81908136b0f55a5d7bb0 |
| 200,000 | 2026_09_06-20:48:28 | $11.84 | idle |

Two early boundaries (32,000 and 52,000) crossed between the standard 10,000 row intervals because the prior orchestrator saved them before handoff. All 20 saved milestones are listed above.

## Validation results

All checks passed.

| Check | Result |
| --- | --- |
| Q44 columns | PASS |
| row_count == 200,000 - failed_row_count | PASS (200,000) |
| row_count == manifest.final_parquet.row_count | PASS |
| unique source_record_id | PASS |
| single correct run_id | PASS |
| accepted label values only | PASS |
| no null labels | PASS |
| final.parquet SHA-256 matches manifest | PASS |
| 100 batch objects part-00000 through part-00099 | PASS |
| each batch 2,000 rows | PASS |
| each batch SHA-256 matches manifest | PASS |
| batch objects tagged intermediate-artifact=true | PASS |
| final.parquet, manifest.json, progress.jsonl untagged | PASS |
| part-00000 holds 10 unchanged smoke rows plus 1,990 new rows | PASS |
| no objects under campaigns/, shards/, final/ | PASS |
| active_openai_batch.json absent after completion | PASS |
| progress.jsonl: 100 batch lines and 1 final line | PASS |

Validation script output is at `/tmp/phaseb/political_stance/validation_output.txt` on the orchestrator host.

## Phase A smoke reference

Smoke cost report: `docs/plans/2026-09-05_generate_bluesky_llm_features_4d8a7c/reports/smoke/political_stance/political_stance_cost_report.json` (deleted from Git in Phase B; S3 smoke evidence remains).

Smoke estimated full run: $11.844 avg, $12.70 max, based on 469.7 avg input tokens and 19.6 avg output tokens per request on 10 smoke posts.
