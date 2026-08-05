# CHANGELOG

## 2026-08-05

1. Stood up a class-conditional keep/remove LLM feature pipeline (generate → Titan embed → HDBSCAN+KMeans cluster → LLM label) under `experiments/create_llm_features_2026_08_05/`, with live smoke on 10 posts/class and production 500/500 gated on smoke approval. [PR #46](https://github.com/METResearchGroup/mirrorView-task/pull/46)
2. Added a keep/remove × platform crosstab experiment for Study Phase 2 Part 2 modal labels (Bluesky / Reddit / Twitter), with a runnable script and terse RESULTS table. [PR #42](https://github.com/METResearchGroup/mirrorView-task/pull/42)

## 2026-08-03

1. Added a shared transformed keep/remove label dataset for Study Phase 2 Part 2 (modal linked-fate decisions, ties → remove) and extended the registry/`load_dataset` path so callers can load it by name instead of rebuilding labels per experiment. [PR #40](https://github.com/METResearchGroup/mirrorView-task/pull/40)

## 2026-08-01

1. Completed the 50% production run for the LLM feature-generation and theme-synthesis experiment: 140 stage-1 batches on the frozen subset (4,397 posts), 1,116 keep + 1,120 remove features, and 132 synthesized themes; added sharded stage-2 synthesis, `resume_production.py`, `RESULTS.md`, and checkpoint commit watcher. [PR #33](https://github.com/METResearchGroup/mirrorView-task/pull/33)

## 2026-07-31

1. Migrated thirteen Phase 1 experiment entry points to load Part 1 pilot results and Part 2 stimuli through the shared dataset registry instead of hardcoded `scripts/` or `combined_flips` paths. [PR #36](https://github.com/METResearchGroup/mirrorView-task/pull/36)
2. Documented the study history and refreshed the README, and checked in canonical Phase 2 raw CSVs under `shared/data/raw/` so experiments share one consistent narrative and dataset source. [PR #34](https://github.com/METResearchGroup/mirrorView-task/pull/34)
3. Added a shared dataset registry and raw-only `load_dataset` API so callers load Phase 2 study CSVs by stable name instead of hardcoding paths under `shared/data/raw/`. [PR #35](https://github.com/METResearchGroup/mirrorView-task/pull/35)
4. Implemented the two-stage LLM feature-generation and theme-synthesis experiment pipeline (batching, `research_tools` runner stages, CLI, and live smoke harness) under `experiments/llm_based_feature_generation_2026_07_31/`, stopping before the 50% production run pending smoke approval. [PR #33](https://github.com/METResearchGroup/mirrorView-task/pull/33)

## 2026-07-28

1. Collocated the MirrorView deployable web stack under `webapp/` (static site, Lambdas, Terraform, S3 upload tooling, smoke stubs) and retargeted agent/operator docs to the new local paths while keeping S3 keys and API URLs unchanged. [PR #31](https://github.com/METResearchGroup/mirrorView-task/pull/31)
