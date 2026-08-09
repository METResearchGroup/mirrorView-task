# CHANGELOG

## 2026-08-09

1. Completed the Qwen3-4B LoRA keep/remove teachability run on SageMaker (`ml.g5.xlarge`): balanced unanimous-min3 chat data, TRL/PEFT train + baseline/adapter infer, and local `RESULTS.md` (test remove-F1 0.74 → 0.97). [PR #54](https://github.com/METResearchGroup/mirrorView-task/pull/54)
2. Moved length, readability, valence, intergroup, and PRIME text features into `shared/textual_features/` with a registry, so experiments call one shared library instead of duplicated mirrors-analysis code. [PR #55](https://github.com/METResearchGroup/mirrorView-task/pull/55)
3. Drafted an implementation plan to repeat the Qwen3-4B LoRA teachability pipeline on modal keep/remove labels (`STUDY_PHASE_2_PART_2_KEEP_REMOVE_LABELS`) under `experiments/larger_finetune_qwen_model_2026_08_08/`, using thin wrappers over `experiments/finetune_qwen_model_2026_08_08`.

## 2026-08-08

1. Added a shared Study Phase 2 Part 2 keep/remove dataset of posts with at least three linked-fate ratings and unanimous agreement (1644 posts), loadable by registry name for high-agreement modeling. [PR #53](https://github.com/METResearchGroup/mirrorView-task/pull/53)

## 2026-08-07

1. Added a pre-study political-expression attention check to the MirrorView webapp (select-all comprehension). Participants always continue; `attention_check_passed` / `attention_check_selected` are saved on every CSV row for post-hoc filtering. [PR #52](https://github.com/METResearchGroup/mirrorView-task/pull/52)

## 2026-08-06

1. Added the larger-scale prompt-engineering keep/remove classifier experiment on a balanced 1,000-post subset (500/500) with Qwen 3.6. Feature-tuned prompt raised remove F1 from 0.628 to 0.700 versus control. [PR #49](https://github.com/METResearchGroup/mirrorView-task/pull/49)
2. Complete methods writeup from the current study phase. [PR #51](https://github.com/METResearchGroup/mirrorView-task/pull/51/)

## 2026-08-05

1. Completed Part 2 free-response feature mining on full low/high Likert reflection corpora: shared Stage-2/3 helpers, Part-2 Stage-1/4 with garbage QA, 916 embedded features, and 5 labeled HDBSCAN themes in `RESULTS.md`. [PR #41](https://github.com/METResearchGroup/mirrorView-task/pull/41)
2. Tested new discovered features by adding it to a baseline prompt and comparing its performance against the regular baseline prompt [PR #47](https://github.com/METResearchGroup/mirrorView-task/pull/47)
3. Shipped a four-stage BERTopic pipeline on Study Phase 2 Part 2 original-post Titan embeddings. [PR #45](https://github.com/METResearchGroup/mirrorView-task/pull/45)
4. Completed the keep/remove LLM feature pipeline under `experiments/create_llm_features_2026_08_05/`. [PR #46](https://github.com/METResearchGroup/mirrorView-task/pull/46)
5. Added a keep/remove × platform crosstab experiment for Study Phase 2 Part 2 modal labels (Bluesky / Reddit / Twitter), with a runnable script and terse RESULTS table. [PR #42](https://github.com/METResearchGroup/mirrorView-task/pull/42)

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
