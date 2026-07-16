# Progress — Follow-up Model Error Analysis (2026-07-15)

Scope default: **v1** (20 extraction calls). V2 not approved.
## [2026-07-16T03:38:18.716574+00:00] Phase 2 — LLM feature extraction

- Status: dry-run
- Scope: v1
- Details: V1 plan: 20 batches | already done: 0 | remaining API calls: 20 (cap max_calls=20) | est. incremental cost ~$5.10 on gpt-5.5
- Artifacts: `outputs/llm_features/v1_batch_plan.json`
- Cost: estimate_incremental_usd=5.10 planned=20 already_done=0

## [2026-07-16T03:38:42.543949+00:00] Phase 2 — LLM feature extraction

- Status: started
- Scope: v1
- Details: V1 plan: 20 batches | already done: 0 | remaining API calls: 20 (cap max_calls=20) | est. incremental cost ~$5.10 on gpt-5.5
- Artifacts: `outputs/llm_features/v1_batch_plan.json`
- Cost: estimate_incremental_usd=5.10 planned=20 already_done=0

## [2026-07-16T04:37:31.608776+00:00] Phase 2 — extraction finished

- Status: completed
- Scope: v1
- Details: new_calls=20 skipped=0 planned=20 total_cost_usd=8.107375
- Artifacts: `outputs/llm_features/cost_summary.json`, `outputs/run_manifest.json`
- Cost (if LLM phase): cumulative_usd=8.107375 new_calls=20 skipped=0 planned=20

## [2026-07-16T04:37:50.502508+00:00] Phase 2 — LLM feature extraction

- Status: dry-run
- Scope: v1
- Details: V1 plan: 20 batches | already done: 20 | remaining API calls: 0 (cap max_calls=20) | est. incremental cost ~$0.00 on gpt-5.5
- Artifacts: `outputs/llm_features/v1_batch_plan.json`
- Cost: estimate_incremental_usd=0.00 planned=20 already_done=20

## [2026-07-16T04:37:50.567763+00:00] Phase 3b — Clustering

- Status: started
- Scope: v1
- Details: posts=320 feature_rows=3341 shards=1 (V1 subset only; max_shards=2)

## [2026-07-16T04:37:51.353827+00:00] Phase 3a — Text mining

- Status: started
- Scope: v1
- Details: feature_rows=3341 buckets=['fn', 'fp', 'tn', 'tp']

## [2026-07-16T04:37:52.136969+00:00] Phase 3a — Text mining

- Status: completed
- Scope: v1
- Details: {"scope": "v1", "n_feature_rows": 3341, "buckets": ["fn", "fp", "tn", "tp"], "n_posts": 320, "snippet": "outputs/text_mining/progress_snippet.md"}
- Artifacts: `outputs/text_mining/` (see progress_snippet.md)

## [2026-07-16T04:38:12.782268+00:00] Phase 3b — Clustering

- Status: started
- Scope: v1
- Details: posts=320 feature_rows=3341 shards=1 (V1 subset only; max_shards=2)

## [2026-07-16T04:40:22.509704+00:00] Phase 3b — Clustering

- Status: completed
- Scope: v1
- Details: shards=1 new_calls=1 total_cost_usd=0.7015
- Artifacts: `outputs/clustering/cluster_summary.md`, `outputs/clustering/clusters_merged.json`
- Cost (if LLM phase): cumulative_usd=0.7015 new_calls=1 skipped=0 planned=1

## [2026-07-16T04:40:28.039326+00:00] Phase 4 — Synthesis

- Status: completed
- Scope: v1
- Details: Wrote RESULTS.md (extract_cost=$8.1074, clustering_cost=$0.7015, total=$8.8089)
- Artifacts: `RESULTS.md`

