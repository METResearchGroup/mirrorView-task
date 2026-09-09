# Step 1: Add the experiment modules and write the shared presentation

## Scope

- **Caller:** `experiments/test_separability_original_mirror_posts_2026_09_09/run.py` `main` with `--write-presentation`
- **Task:** Add the experiment folder, pin the catalog, shuffle each original and mirror pair once with seed 42, upload `presentations.parquet`, and implement the OpenAI runner, the Bedrock runner, the shared labeling loop, and the scorer so Steps 2 and 3 only run commands. Do not call OpenAI or Bedrock in this step.
- **Out of scope:** live OpenAI, live Bedrock, pytest, editing `data_platform/`, editing flip generation, editing the catalog, writing `RESULTS.md`, writing `CHANGELOG.md`

## Files to inspect (read-only)

| Path | Why |
|------|-----|
| `/workspace/docs/plans/2026-09-09_separability_original_mirror_dee07c/plan.md` | Confirmed decisions, S3 keys, models, scoring rule |
| `/workspace/experiments/calculate_required_label_count_per_stimulus_post_2026_09_09/constants.py` | Pinned catalog URI, SHA-256, row count |
| `/workspace/experiments/calculate_required_label_count_per_stimulus_post_2026_09_09/load.py` | Download, cache, SHA-256, row count, unique id checks |
| `/workspace/experiments/calculate_required_label_count_per_stimulus_post_2026_09_09/write.py` | `require_output_key_absent` before work, `put_new` |
| `/workspace/experiments/calculate_required_label_count_per_stimulus_post_2026_09_09/run.py` | given/when/then module docstring |
| `/workspace/experiments/generate_flips_2026_09_08/run.py` | Typer flags for a multi-mode experiment command |
| `/workspace/experiments/filter_posts_used_for_stimulus_dataset_2026_09_08/README.md` | Agent read-only banner |
| `/workspace/data_platform/generate_features/models.py` | `FeatureSpec`, `LabelTask`, `FeatureRunConfig`, `CampaignRunConfig`, `LabelRowMetadataModel` |
| `/workspace/data_platform/generate_features/engines/openai_engine.py` | `build_openai_engine`, `OpenAIBatchEngine.batch_label_records` |
| `/workspace/data_platform/generate_features/engines/bedrock_engine.py` | `label_tasks_collecting_failures`, `BEDROCK_MAX_TOKENS` is 32, `create_bedrock_runtime_client` |
| `/workspace/data_platform/generate_features/engines/bedrock_campaign.py` | `BEDROCK_CAMPAIGN_MAX_CONCURRENCY` is 8, OpenAI retry that this experiment must not call |
| `/workspace/data_platform/generate_features/s3_feature_campaign.py` | `FeaturePaths.from_root_uri`, `CampaignObjectStore.put_new`, `new_manifest`, `load_manifest`, `save_manifest`, `append_errors`, `read_failed_ids`, `run_id_for_feature` |
| `/workspace/data_platform/generate_features/s3_feature_batches.py` | `write_batch`, `adopt_unrecorded_batch`, `consolidate_final`, `attach_row_metadata`, `campaign_row_columns` |
| `/workspace/data_platform/generate_features/generate_features.py` | `generate_campaign_feature` routes non-Reddit campaigns to OpenAI, so do not use it for Bedrock. `tasks_from_dataframe` is public. |
| `/workspace/data_platform/generate_features/platform_cli.py` | `CAMPAIGN_BATCH_SIZE` is 2000 |
| `/workspace/data_platform/generate_features/political_stance/generate_feature.py` | Split LLM schema vs persisted row model |
| `/workspace/experiments/finetune_qwen_model_2026_08_08/evaluate.py` | `accuracy_score`, `precision_score`, `recall_score`, `f1_score`, `zero_division=0` |
| `/workspace/lib/constants.py` | `DEFAULT_LLM_MODEL`, `DEFAULT_BEDROCK_NOVA_MICRO`, `BEDROCK_REGION` |
| `/workspace/.cursor/skills/implement-plan-and-open-pr/UNIT_TESTING_STANDARDS.md` | Experiment code does not get unit tests |

## Files allowed to change

- `/workspace/experiments/test_separability_original_mirror_posts_2026_09_09/README.md` (new)
- `/workspace/experiments/test_separability_original_mirror_posts_2026_09_09/constants.py` (new)
- `/workspace/experiments/test_separability_original_mirror_posts_2026_09_09/schema.py` (new)
- `/workspace/experiments/test_separability_original_mirror_posts_2026_09_09/prompts.py` (new)
- `/workspace/experiments/test_separability_original_mirror_posts_2026_09_09/loader.py` (new)
- `/workspace/experiments/test_separability_original_mirror_posts_2026_09_09/write.py` (new)
- `/workspace/experiments/test_separability_original_mirror_posts_2026_09_09/openai_runner.py` (new)
- `/workspace/experiments/test_separability_original_mirror_posts_2026_09_09/bedrock_runner.py` (new)
- `/workspace/experiments/test_separability_original_mirror_posts_2026_09_09/score.py` (new)
- `/workspace/experiments/test_separability_original_mirror_posts_2026_09_09/run.py` (new)
- `/workspace/experiments/test_separability_original_mirror_posts_2026_09_09/.gitignore` (new)
- `/workspace/.gitignore` (ignore `cache/` and `outputs/` under this experiment folder only)

## Files forbidden to change

- `/workspace/data_platform/**`
- `/workspace/shared/flip_generation/**`
- `/workspace/experiments/curate_study_2_phase_3_stimuli/**`
- `/workspace/shared/data/raw/study_phase_2_part_2/**`
- `/workspace/tests/**`
- `/workspace/CHANGELOG.md`
- `/workspace/docs/plans/2026-09-09_separability_original_mirror_dee07c/plan.md`
- The catalog S3 object `experiments/curate_study_2_phase_3_stimuli/flips.csv`

## README contract

Write `/workspace/experiments/test_separability_original_mirror_posts_2026_09_09/README.md` first, then implement the modules to match it.

The README must:

1. Start with the same agent read-only banner used in `/workspace/experiments/filter_posts_used_for_stimulus_dataset_2026_09_08/README.md`.
2. Say this experiment asks the default OpenAI model and the default Bedrock model which of two texts is human, original vs mirror.
3. Name the catalog object, SHA-256, and 10,000 row count from the Pinned catalog table below.
4. Say human text is `original_text` and AI text is `mirrored_text`.
5. Say presentation order is shuffled once with seed 42, stored in `presentations.parquet`, and reused by both engines.
6. Name the label fields: `human_slot` is `first` or `second`, and `reason` is one sentence.
7. Name the S3 bucket `mirrorview-experimental-artifacts` and the prefix `experiments/test_separability_original_mirror_posts_2026_09_09/`.
8. List these required files: `constants.py`, `schema.py`, `prompts.py`, `loader.py`, `write.py`, `openai_runner.py`, `bedrock_runner.py`, `score.py`, `run.py`.
9. Include the four command blocks from `plan.md` Commands.

After this README is committed, later steps must not edit it.

## Pinned catalog

| Field | Value |
|-------|-------|
| Object | `s3://mirrorview-experimental-artifacts/experiments/curate_study_2_phase_3_stimuli/flips.csv` |
| SHA-256 | `c90fdcf86e89e393f0de4cc34e1dc4e4bb2bd876405926ad654ff679f3ab4139` |
| Rows | 10000 |
| Id column | `post_primary_key` |

Required catalog columns: `post_primary_key`, `original_text`, `mirrored_text`, `sampled_stance`, `sample_toxicity_type`.

`sampled_stance` must be `left` or `right`. `sample_toxicity_type` must be `sample_low_toxicity`, `sample_middle_toxicity`, or `sample_high_toxicity`. Empty original or mirror text raises `ValueError`.

A hash mismatch, a wrong row count, or duplicate ids raises `ValueError`. A missing source object raises `FileNotFoundError`. Do not load `shared/data/raw/study_phase_2_part_2/stimuli/flips.csv`.

Copy the download, cache, and hash pattern from `experiments/calculate_required_label_count_per_stimulus_post_2026_09_09/load.py`. Do not import that loader.

## Presentation contract

Call `require_presentation_key_absent` before downloading the catalog.

Shuffle with `random.Random(42)` while iterating rows sorted by `post_primary_key` with `kind="mergesort"`. For each row, draw one bit. If the bit is 0, first text is original and `gold_human_slot` is `first`. If the bit is 1, first text is the mirror and `gold_human_slot` is `second`.

Presentation columns, in this order:

| Column | Value |
|--------|-------|
| `post_primary_key` | catalog id |
| `first_text` | text shown as post first |
| `second_text` | text shown as post second |
| `gold_human_slot` | `first` or `second` |
| `sampled_stance` | copied from the catalog |
| `sample_toxicity_type` | copied from the catalog |
| `prompt_text` | user message that interpolates `first_text` and `second_text` |

User message template, stored in `prompts.py`:

```text
Post first:
{first_text}

Post second:
{second_text}
```

System prompt, stored in `prompts.py`: say that the user will send two social media posts, that exactly one was written by a human and the other was written by an AI as a political mirror of the human post, and that the model must return which presented post is human (`first` or `second`) plus a one-sentence reason.

Upload with `put_new` to `experiments/test_separability_original_mirror_posts_2026_09_09/outputs/presentations.parquet` in bucket `mirrorview-experimental-artifacts`. A second upload of that key must raise `FileExistsError`. Print `wrote 10000 presentations` and the SHA-256.

## Schema and FeatureSpec

`extra="forbid"` on both Pydantic models. No optional fields.

`LlmSeparabilityModel` is `FeatureSpec.llm_output_schema`: `human_slot` is `Literal["first", "second"]`, `reason` is `str` with `min_length=1`.

`SeparabilityRow` is `FeatureSpec.model`: `source_record_id` is `str`, `label_timestamp` is `str`, `human_slot` is `Literal["first", "second"]`, `reason` is `str`.

`separability_spec(engine_type)` returns `FeatureSpec(name="separability", model=SeparabilityRow, engine_type=engine_type, system_prompt=..., llm_output_schema=LlmSeparabilityModel)` where `engine_type` is `"openai"` or `"bedrock"`.

## Shared labeling loop

`run.py` owns one loop used by both engines. Do not call `generate_campaign_feature`. Do not call `run_bedrock_campaign_feature`. The Reddit campaign runner retries Bedrock content-filter failures through OpenAI, and that would mix engines.

`CampaignRunConfig` values, stored in `constants.py`:

| Field | Value |
|-------|-------|
| `campaign_id` | `test_separability_original_mirror_posts_2026_09_09` |
| `dataset_id` | `study_2_phase_3_catalog` |
| `preprocessed_run` | `presentations` |
| `platform` | `experiment` |
| `batch_size` | import `CAMPAIGN_BATCH_SIZE` from `data_platform.generate_features.platform_cli` (2000) |

Label records have `source_record_id` equal to `post_primary_key` and `text` equal to `prompt_text`. Sort by `source_record_id` with `kind="mergesort"`. Duplicate ids raise `ValueError`.

Feature prefixes, using `FeaturePaths.from_root_uri`:

| Run | Root URI | Feature argument | Resulting prefix |
|-----|----------|------------------|------------------|
| OpenAI full | `s3://mirrorview-experimental-artifacts/experiments/test_separability_original_mirror_posts_2026_09_09/outputs/labels` | `openai` | `.../outputs/labels/openai/` |
| Bedrock full | same root | `bedrock` | `.../outputs/labels/bedrock/` |
| OpenAI smoke | `s3://mirrorview-experimental-artifacts/experiments/test_separability_original_mirror_posts_2026_09_09/outputs/labels/openai` | `smoke` | `.../outputs/labels/openai/smoke/` |
| Bedrock smoke | `s3://mirrorview-experimental-artifacts/experiments/test_separability_original_mirror_posts_2026_09_09/outputs/labels/bedrock` | `smoke` | `.../outputs/labels/bedrock/smoke/` |

Smoke rows are the first 10 presentations after sorting by `post_primary_key`. Do not copy smoke rows into the full-run `final.parquet`.

Loop for one engine prefix:

1. Build a fresh manifest with `new_manifest`, passing `engine_type` `"openai"` or `"bedrock"`. If `load_manifest` returns an existing manifest, require identity fields to match, the same check as `generate_features._load_or_create_manifest`. Copy that check into the experiment. Do not import the private function.
2. If the manifest already has `final_parquet`, print that the final file exists and return without labeling.
3. For each chunk of `CAMPAIGN_BATCH_SIZE` ids, skip the part if it is already in the manifest. If the part object exists and is missing from the manifest, call `adopt_unrecorded_batch` and continue.
4. Call `openai_runner.label_tasks` or `bedrock_runner.label_tasks` on the pending tasks.
5. `attach_row_metadata` with `run_id` from `run_id_for_feature(campaign_id, "separability")`, `batch_id` equal to `part-{part_index:05d}`, `request_id` equal to `{engine}-{source_record_id}`, and `attempt_count` 1. Then `write_batch`. If a chunk has zero successful rows, do not call `write_batch`. Append every failed id to `errors.jsonl` with `append_errors`.
6. `consolidate_final` with `expected_ids` equal to every id in this run (10 for smoke, 10,000 for full) and `failed_ids` from `read_failed_ids`.

Print `labeled {n_labeled} of {n_expected}` and `failed={n_failed}`.

Ten thousand full-run pairs become five parts, `part-00000` through `part-00004`. Smoke is one part of 10 rows.

## Engine runners

`openai_runner.label_tasks(spec, tasks)` builds `OpenAIBatchEngine` through `build_openai_engine(spec, FeatureRunConfig())` and calls `batch_label_records`. The default model is `gpt-5.4-nano`. Return `(rows, failures)`. If `batch_label_records` raises for the whole job, do not write a part.

`bedrock_runner.label_tasks(spec, tasks)` calls `label_tasks_collecting_failures` with `create_bedrock_runtime_client()`, `DEFAULT_BEDROCK_NOVA_MICRO`, `BEDROCK_CAMPAIGN_MAX_CONCURRENCY` from `data_platform.generate_features.engines.bedrock_campaign`, `max_tokens=256` from experiment `constants.py`, and a fresh `label_timestamp`. Content-filter failures and other failures stay in the failures list. Do not send them to OpenAI.

Do not change `BEDROCK_MAX_TOKENS` in `data_platform/`.

## Scorer

Implement `score.py` in this step. Do not run `--score` until Step 3.

Join each engine `final.parquet` to `presentations.parquet` on `source_record_id` = `post_primary_key`. Positive class is `gold_human_slot == "first"` and `human_slot == "first"`, encoded as 1. Compute accuracy, precision, recall, and F1 with scikit-learn and `zero_division=0`, the same calls as `experiments/finetune_qwen_model_2026_08_08/evaluate.py` `compute_metrics`. Copy those four lines. Do not import that experiment module.

Score only rows with a valid `human_slot`. If a group has zero scored rows, write `0.0` for all four metrics and do not call scikit-learn on empty lists.

Cell key is `{sampled_stance}+{mapped toxicity}` where `sample_low_toxicity` maps to `low`, `sample_middle_toxicity` maps to `medium`, and `sample_high_toxicity` maps to `high`. Column order is left+low, left+medium, left+high, right+low, right+medium, right+high. Row order in each cell table is accuracy, recall, precision, F1.

Overall table rows are `openai` then `bedrock`. Columns are accuracy, precision, recall, F1. Under each table, write `n_scored` and `n_failed`.

## CLI

Use Typer. Flags are mutually exclusive except `--smoke` with `--engine`.

```text
--write-presentation
--engine openai|bedrock [--smoke]
--score
```

`--help` exits 0. `--smoke` without `--engine` raises `ValueError`. `--write-presentation` must not call a model.

## Main caller

```bash
export AWS_ACCESS_KEY_ID="$LAB_AWS_ACCESS_KEY_ID"
export AWS_SECRET_ACCESS_KEY="$LAB_AWS_ACCESS_KEY_SECRET"

PYTHONPATH=. uv run python experiments/test_separability_original_mirror_posts_2026_09_09/run.py --write-presentation
```

Expected stdout includes `wrote 10000 presentations` and `sha256=`. A second run raises `FileExistsError` before the catalog download.

## Live given / when / then (Phase 4)

Write this block in the `run.py` module docstring.

```text
given AWS credentials from LAB_AWS_ACCESS_KEY_ID and LAB_AWS_ACCESS_KEY_SECRET
and pull request 273 wrote the 10000 row catalog
when PYTHONPATH=. uv run python experiments/test_separability_original_mirror_posts_2026_09_09/run.py --write-presentation
then wrote 10000 presentations
and S3 object experiments/test_separability_original_mirror_posts_2026_09_09/outputs/presentations.parquet exists
and gold_human_slot is first or second on every row
and first_text plus second_text are the original and the mirror in some order
and no OpenAI or Bedrock call is made

given the presentation key already exists
when the command is run again
then the process raises FileExistsError
and the catalog S3 object is unchanged
```

## Must pass

- `--help` exits 0.
- First `--write-presentation` writes 10,000 rows and prints `wrote 10000 presentations`.
- Presentation columns match the table above.
- `openai_runner.py` and `bedrock_runner.py` exist and are imported by `run.py`.
- Catalog S3 object SHA-256 is still `c90fdcf86e89e393f0de4cc34e1dc4e4bb2bd876405926ad654ff679f3ab4139`.
- `data_platform/` is unchanged.

## Must fail

- Second `--write-presentation` after the S3 key exists, with `FileExistsError` before catalog download.
- Hash mismatch or row-count mismatch on the pinned catalog.
- Loading `shared/data/raw/study_phase_2_part_2/stimuli/flips.csv`.
- Calling `generate_campaign_feature` or `run_bedrock_campaign_feature`.
- Calling OpenAI or Bedrock during `--write-presentation`.

## Implement-from-spec notes

Follow `/implement-from-spec`. Full auto. Do not add pytest. Phase 4 is the given/when/then block in the `run.py` module docstring.

Phase 1 names `run.py` `main` with `--write-presentation` as the caller for this step.

Phase 2 scaffolds the allowed files with stub bodies: load, shuffle, write, label loop, score.

Phase 3 locks the Pydantic models, `CampaignRunConfig` values, presentation columns, and runner signatures. Continue without a pause.

Phase 5 implements in this order, one commit per unit of work:

1. `constants.py` pinned catalog and S3 keys
2. `schema.py` and `prompts.py`
3. `loader.py` download and hash checks
4. Shuffle and presentation table
5. `write.py` `require_presentation_key_absent` and `put_new`
6. `run.py` `--write-presentation`
7. Shared labeling loop plus `openai_runner.py` and `bedrock_runner.py`
8. `score.py`
9. README and `.gitignore`

Phase 6 is complete when `--write-presentation` succeeds once, the second run raises `FileExistsError`, and no model was called. Do not start Step 2 until the presentation object exists.
