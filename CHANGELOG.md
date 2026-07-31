# CHANGELOG

## 2026-07-31

1. Documented the study history and refreshed the README, and checked in canonical Phase 2 raw CSVs under `shared/data/raw/` so experiments share one consistent narrative and dataset source. [PR #34](https://github.com/METResearchGroup/mirrorView-task/pull/34)
2. Added a shared dataset registry and raw-only `load_dataset` API so callers load Phase 2 study CSVs by stable name instead of hardcoding paths under `shared/data/raw/`. [PR #35](https://github.com/METResearchGroup/mirrorView-task/pull/35)
3. Implemented the two-stage LLM feature-generation and theme-synthesis experiment pipeline (batching, `research_tools` runner stages, CLI, and live smoke harness) under `experiments/llm_based_feature_generation_2026_07_31/`, stopping before the 50% production run pending smoke approval. [PR #33](https://github.com/METResearchGroup/mirrorView-task/pull/33)

## 2026-07-28

1. Collocated the MirrorView deployable web stack under `webapp/` (static site, Lambdas, Terraform, S3 upload tooling, smoke stubs) and retargeted agent/operator docs to the new local paths while keeping S3 keys and API URLs unchanged. [PR #31](https://github.com/METResearchGroup/mirrorView-task/pull/31)
