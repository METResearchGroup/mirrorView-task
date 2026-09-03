# CHANGELOG

## 2026-09-03

1. Reddit monthly comment dumps from the Pushshift experiment can be filtered, sampled to 500,000 comments per month, and stored as git LFS parquet using the same comment fields as live Reddit ingest. [PR #153](https://github.com/METResearchGroup/mirrorView-task/pull/153)
2. `data_platform` now uses "standardized" instead of "canonical" for shared column helpers and constants (`add_standardized_text_column`, `STANDARDIZED_TEXT_COLUMN`, and related names). Column values are unchanged. [PR #150](https://github.com/METResearchGroup/mirrorView-task/pull/150)
3. New Reddit comment rows keep `comment_fullname`, `author`, `body`, `created_at`, and `sync_timestamp`. The writer still adds `record_id` from `comment_fullname`. Older comment files that still have extra columns will not load until you ingest the comments again. [PR #148](https://github.com/METResearchGroup/mirrorView-task/pull/148)
4. Bluesky ingest now requires an explicit `new-run` or `resume` command. `new-run` refuses to start when an unfinished raw run exists; `resume` accepts a named timestamp or `--latest` and fails fast when the run is missing or already completed. Twitter and Reddit keep the combined start-or-resume behavior. [PR #145](https://github.com/METResearchGroup/mirrorView-task/pull/145)
5. Raw ingest now writes a stable `record_id` on every row using the same `{integration}_{id}` keys as study stimuli (`bluesky_{sha256(uri)}`, `twitter_{tweet_id}`, `reddit_{post_reddit_id}_{comment_id}`). [PR #138](https://github.com/METResearchGroup/mirrorView-task/pull/138)
6. Ingest, preprocess, and feature unlabeled skip now share one skip set session. The warmup names are gone. Callers load known ids for this run or for all runs before they drop, persist, or collapse. [PR #144](https://github.com/METResearchGroup/mirrorView-task/pull/144)
7. Bluesky ingestion now delegates all API client work to `BlueskyClient` in `data_platform/ingestion/integrations/bluesky.py`. `sync_bluesky.py` now handles sync logic only, and the client can be tested on its own. [PR #143](https://github.com/METResearchGroup/mirrorView-task/pull/143)

## 2026-09-02

1. Preprocess now owns length and English gates for stimuli-ready text. Reddit comments also need at least 30 characters. Ingest fetch filters are unchanged. [PR #132](https://github.com/METResearchGroup/mirrorView-task/pull/132)
2. Preprocess now copies each platform's original record id onto `source_record_id`. Feature files use that name, and curation joins original ids to it. Raw id columns stay. [PR #131](https://github.com/METResearchGroup/mirrorView-task/pull/131)
3. Preprocess now writes a shared `author_handle` column on Bluesky, Reddit, and Twitter rows. Raw ingest author fields stay as they are. [PR #130](https://github.com/METResearchGroup/mirrorView-task/pull/130)
4. Twitter and Reddit ingest now write payload creation time as UTC ISO-8601 `created_at`. Reddit no longer also writes the same string as `created_utc`. [PR #128](https://github.com/METResearchGroup/mirrorView-task/pull/128)
5. Ingest run metadata now stores one skip total, `rows_skipped_as_duplicates`, plus an optional per-record-type map. Older platform skip-count names are still read on resume. [PR #127](https://github.com/METResearchGroup/mirrorView-task/pull/127)
6. Ingest YAML now uses one `dedupe_policy` skip list on Bluesky, Twitter, and Reddit, with optional Reddit per-type overrides. Committed configs no longer list the unused `current_run` token. [PR #126](https://github.com/METResearchGroup/mirrorView-task/pull/126)
7. Ingest YAML names a run-wide post cap as `max_posts` and a comment cap as `max_comments`. The older `max_rows` key still means posts on Bluesky and Twitter and comments on Reddit. [PR #125](https://github.com/METResearchGroup/mirrorView-task/pull/125)
8. Bluesky, Twitter, and Reddit ingest now share YAML `limit_per_task` for the per-task fetch cap. The older platform keys still work as fallbacks. [PR #124](https://github.com/METResearchGroup/mirrorView-task/pull/124)
9. Twitter ingest YAML now uses list-form `keywords` like Bluesky. The older `keyword` string or list still works as a fallback. [PR #123](https://github.com/METResearchGroup/mirrorView-task/pull/123)
10. Twitter and Reddit ingest now write raw files using the dataset format from YAML, so parquet configs get `.parquet` names instead of hardcoded CSV. Bluesky already did this. [PR #122](https://github.com/METResearchGroup/mirrorView-task/pull/122)
11. Ingest run metadata and the dataset manifest both store the YAML config as a path from the repo root with forward slashes, so two configs with the same file name on different platforms stay distinct. [PR #121](https://github.com/METResearchGroup/mirrorView-task/pull/121)
12. Bluesky ingest YAML uses `author_filter` for the searchPosts author filter, so it is no longer named like login identity. The older `handle` key still works as a fallback. Env `BLUESKY_HANDLE` is unchanged. [PR #120](https://github.com/METResearchGroup/mirrorView-task/pull/120)
13. Twitter ingest now stops at startup when YAML `record_types` is missing, empty, or does not include `twitter.tweet`, so a bad Twitter config fails before any API fetch. Bluesky and Reddit already had this check. [PR #119](https://github.com/METResearchGroup/mirrorView-task/pull/119)
14. Feature generation writes each run under `features/{timestamp}/`, which matches how the other pipeline stages store runs. Each run records prompt and model identity in metadata, and posts that already have labels are still skipped. [PR #93](https://github.com/METResearchGroup/mirrorView-task/pull/93)
15. Ingest YAML uses `prior_runs_same_dataset` to skip ids from earlier local runs of the same dataset. We removed `query_batch_size` and `dedupe_comments_from_prior_raw_runs`. [PR #87](https://github.com/METResearchGroup/mirrorView-task/pull/87)
16. Ingest now writes ISO `created_at` and the run `sync_timestamp` on Bluesky, Reddit, and Twitter rows, so later stages can read those two fields. Reddit still also writes `created_utc` as the same ISO string. Current timestamps in `data_platform` use UTC `get_current_timestamp`. [PR #88](https://github.com/METResearchGroup/mirrorView-task/pull/88)
17. The preprocess step adds a shared `text` column on Bluesky, Twitter, and Reddit comment rows that pass the filters. Reddit feature code now reads that column, and the original `body` field is still on the record so you can check it. [PR #91](https://github.com/METResearchGroup/mirrorView-task/pull/91)
18. Feature skip and run completeness in `data_platform` use one seen-id loader and one completeness raise. Bluesky and Twitter share `quote_query_term`, and `data_platform.models` exports every sync record model. [PR #90](https://github.com/METResearchGroup/mirrorView-task/pull/90)
19. Data-platform code can resolve and validate file paths relative to the `data_platform/` package, using shared full names for posts, comments, and metadata files. [PR #95](https://github.com/METResearchGroup/mirrorView-task/pull/95)
20. Skip-set sessions can load this-run or all-runs ids, drop already-seen ingest rows, and extend the skip set after append, while the old warmup path still works for existing callers. [PR #79](https://github.com/METResearchGroup/mirrorView-task/pull/79)
21. Bluesky feature generation and curation now call the same platform command-line scripts as Reddit and Twitter. Bluesky still uses settings flags for its extra completeness checks and for skipping curation when inputs have not changed. LangChain feature settings no longer set a generate_fn that the LangChain engine never calls. [PR #89](https://github.com/METResearchGroup/mirrorView-task/pull/89)
22. Feature generation no longer sends LLM traces to Opik. The `--opik` flag is gone, and existing metadata files that stored `opik_enabled` still load. [PR #101](https://github.com/METResearchGroup/mirrorView-task/pull/101)

## 2026-09-01

1. Shared preprocessing, feature, and curation runners now take `PlatformSpecificColumns` on `spec.columns` instead of the overloaded `PlatformIdBinding` name, so per-platform CSV column maps read as what they are. [PR #65](https://github.com/METResearchGroup/mirrorView-task/pull/65)

## 2026-08-16

1. Removed AWS Glue table setup, S3 writes, DynamoDB pipeline-run tracking, and Prefect orchestration from `data_platform/`. Curation is the last pipeline stage, and artifacts stay under `data_platform/data/`. Run each stage via its CLI (see `data_platform/README.md`). [PR #50](https://github.com/METResearchGroup/mirrorView-task/pull/50)
2. Incremental sync and preprocessing now combine record ids from every local run directory for a dataset when the YAML config enables deduplication across prior runs. The pipeline no longer uses Amazon Athena to look up ids it has already seen. [PR #50](https://github.com/METResearchGroup/mirrorView-task/pull/50)
3. Bluesky keyword search uses the public Bluesky API at `https://api.bsky.app` when `BLUESKY_HANDLE` and `BLUESKY_PASSWORD` are unset, so you can run a small local collection without a Bluesky account. [PR #50](https://github.com/METResearchGroup/mirrorView-task/pull/50)

## 2026-08-09

1. Completed the Qwen3-4B LoRA keep/remove teachability run on SageMaker (`ml.g5.xlarge`): balanced unanimous-min3 chat data, TRL/PEFT train + baseline/adapter infer, and local `RESULTS.md` (test remove-F1 0.74 → 0.97). [PR #54](https://github.com/METResearchGroup/mirrorView-task/pull/54)
2. Moved length, readability, valence, intergroup, and PRIME text features into `shared/textual_features/` with a registry, so experiments call one shared library instead of duplicated mirrors-analysis code. [PR #55](https://github.com/METResearchGroup/mirrorView-task/pull/55)
3. Completed the larger modal-label Qwen3-4B LoRA teachability run (1 epoch on SageMaker `ml.g5.xlarge`): balanced Study Phase 2 Part 2 modal keep/remove data, thin wrappers over the unanimous recipe, and local `RESULTS.md` (test accuracy 0.64 → 0.70; remove-F1 0.72 → 0.70). [PR #57](https://github.com/METResearchGroup/mirrorView-task/pull/57)
4. Shipped a descriptive analysis that splits linked-fate keep and remove labels into unanimous and majority cells (ties dropped), with surface metrics, Stage 1 word clouds, and stance tables by toxicity stratum. Unanimous cells sit at clearer extremes, and heavy remove aligns more with high toxicity than with left or right stance. [PR #56](https://github.com/METResearchGroup/mirrorView-task/pull/56)

## 2026-08-08

1. Added a shared Study Phase 2 Part 2 keep/remove dataset of posts with at least three linked-fate ratings and unanimous agreement (1644 posts), loadable by registry name for high-agreement modeling. [PR #53](https://github.com/METResearchGroup/mirrorView-task/pull/53)

## 2026-08-07

1. Added a pre-study political-expression attention check to the MirrorView webapp (select-all comprehension). Participants always continue; `attention_check_passed` / `attention_check_selected` are saved on every CSV row for post-hoc filtering. [PR #52](https://github.com/METResearchGroup/mirrorView-task/pull/52)

## 2026-08-06

1. Landed Bluesky, Twitter, and Reddit ingest through curation in this repository under `data_platform/`, with local-disk durability and sample discovery pointed at in-repo curated exports. [PR #50](https://github.com/METResearchGroup/mirrorView-task/pull/50)
2. Added the larger-scale prompt-engineering keep/remove classifier experiment on a balanced 1,000-post subset (500/500) with Qwen 3.6. Feature-tuned prompt raised remove F1 from 0.628 to 0.700 versus control. [PR #49](https://github.com/METResearchGroup/mirrorView-task/pull/49)
3. Complete methods writeup from the current study phase. [PR #51](https://github.com/METResearchGroup/mirrorView-task/pull/51/)

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
