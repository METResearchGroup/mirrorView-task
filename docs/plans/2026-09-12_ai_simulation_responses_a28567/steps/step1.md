# Step 1: Add the shared cohort, prompts, schema, runner, and tests

## Scope

- **Caller:** `experiments/ai_simulation_responses_2026_09_11/shared/run.py` `main` with `--write-cohort`
- **Task:** Add the experiment folders, download September Prolific CSVs, and confirm up to 1,000 complete participants. Upload cohort parquet locally and to S3 at the matching path. Implement the mirrored-path helper, prompts, schema, four model runners, scoring helpers, and pytest. Do not call OpenAI or Bedrock.
- **Out of scope:** smoke, cost estimate, full labeling, `RESULTS.md`, `CHANGELOG.md`, editing product engines, editing the website, editing `scripts/export_study_results.py`

## Files to inspect (read-only)

| Path | Why |
|------|-----|
| `/workspace/docs/plans/2026-09-12_ai_simulation_responses_a28567/plan.md` | Confirmed decisions, models, gates |
| `/workspace/scripts/export_study_results.py` | `list_csv_keys`, `download_csvs`, `filter_manual_test_rows`, bucket `jspsych-mirror-view-2026-09-09`, prefix `data/prolific/` |
| `/workspace/webapp/public/main.js` | Training_assisted instruction copy, reflection question, `columnsToKeep`, `trial_index` |
| `/workspace/webapp/public/post_surveys.js` | Demographic labels and Likert anchors that are actually exported |
| `/workspace/webapp/public/plugins/plugin-moderation-trial.js` | `pair_order`, `decision`, linked-fate shuffle |
| `/workspace/jobs/config/mirrorview_2026_09_09.yaml` | Study id `mirrorview_2026_09_09`, 20 trials, `training_assisted` |
| `/workspace/experiments/test_separability_original_mirror_posts_2026_09_09/run.py` | Campaign part loop, smoke prefix, `write_batch`, `consolidate_final` |
| `/workspace/experiments/test_separability_original_mirror_posts_2026_09_09/schema.py` | Split LLM schema vs persisted row, `FeatureSpec` |
| `/workspace/experiments/test_separability_original_mirror_posts_2026_09_09/bedrock_runner.py` | `label_tasks_collecting_failures` plus raised `max_tokens` |
| `/workspace/experiments/test_separability_original_mirror_posts_2026_09_09/openai_runner.py` | `build_openai_engine` |
| `/workspace/data_platform/generate_features/models.py` | `FeatureSpec`, `LabelTask`, `FeatureRunConfig` |
| `/workspace/data_platform/generate_features/engines/openai_engine.py` | `build_openai_engine`, default model `gpt-5.4-nano` |
| `/workspace/data_platform/generate_features/engines/bedrock_engine.py` | `label_tasks_collecting_failures`, `create_bedrock_runtime_client`, `BEDROCK_MAX_TOKENS` is 32 |
| `/workspace/data_platform/generate_features/engines/bedrock_campaign.py` | `BEDROCK_CAMPAIGN_MAX_CONCURRENCY` is 8 |
| `/workspace/data_platform/generate_features/s3_feature_campaign.py` | `CampaignObjectStore`, `parse_s3_uri`, `FeaturePaths.from_root_uri`, `put_new` |
| `/workspace/experiments/generate_study_user_assignments_2026_09_08/constants.py` | `OUTPUT_S3_BUCKET` and `OUTPUT_S3_KEY` equal to the local experiment path |
| `/workspace/experiments/test_separability_original_mirror_posts_2026_09_09/constants.py` | `OUTPUT_S3_BUCKET` and `PRESENTATION_S3_KEY` equal to the local experiment path |
| `/workspace/data_platform/generate_features/s3_feature_batches.py` | `write_batch`, `consolidate_final`, `attach_row_metadata` |
| `/workspace/data_platform/generate_features/campaign_cost_report.py` | OpenAI Batch and Nova Micro rates |
| `/workspace/lib/constants.py` | `DEFAULT_LLM_MODEL`, `DEFAULT_BEDROCK_NOVA_MICRO`, `DEFAULT_BEDROCK_SONNET_MODEL`, `BEDROCK_REGION` |
| `/workspace/experiments/predict_keep_remove_2026_07_01/models/llm_finetuning/api_baselines/constants.py` | `qwen.qwen3-32b-v1:0` |
| `/workspace/experiments/predict_keep_remove_2026_07_01/models/llm_finetuning/api_baselines/prompts.py` | Authoritative study instruction wording |
| `/workspace/experiments/finetune_qwen_model_2026_08_08/evaluate.py` | `zero_division=0`, remove as positive class |
| `/workspace/experiments/filter_posts_used_for_stimulus_dataset_2026_09_08/README.md` | Agent read-only banner |
| `/workspace/.cursor/skills/implement-plan-and-open-pr/UNIT_TESTING_STANDARDS.md` | Arrange-act-assert, one test class per function |

## Files allowed to change

- `/workspace/experiments/ai_simulation_responses_2026_09_11/README.md` (new)
- `/workspace/experiments/ai_simulation_responses_2026_09_11/shared/__init__.py` (new)
- `/workspace/experiments/ai_simulation_responses_2026_09_11/shared/constants.py` (new)
- `/workspace/experiments/ai_simulation_responses_2026_09_11/shared/schema.py` (new)
- `/workspace/experiments/ai_simulation_responses_2026_09_11/shared/prompts.py` (new)
- `/workspace/experiments/ai_simulation_responses_2026_09_11/shared/cohort.py` (new)
- `/workspace/experiments/ai_simulation_responses_2026_09_11/shared/write.py` (new)
- `/workspace/experiments/ai_simulation_responses_2026_09_11/shared/openai_runner.py` (new)
- `/workspace/experiments/ai_simulation_responses_2026_09_11/shared/bedrock_runner.py` (new)
- `/workspace/experiments/ai_simulation_responses_2026_09_11/shared/score.py` (new)
- `/workspace/experiments/ai_simulation_responses_2026_09_11/shared/run.py` (new)
- `/workspace/experiments/ai_simulation_responses_2026_09_11/shared/tests/__init__.py` (new)
- `/workspace/experiments/ai_simulation_responses_2026_09_11/shared/tests/conftest.py` (new)
- `/workspace/experiments/ai_simulation_responses_2026_09_11/shared/tests/test_build_cohort.py` (new)
- `/workspace/experiments/ai_simulation_responses_2026_09_11/shared/tests/test_render_prompt.py` (new)
- `/workspace/experiments/ai_simulation_responses_2026_09_11/shared/tests/test_expand_remove_indexes.py` (new)
- `/workspace/experiments/ai_simulation_responses_2026_09_11/shared/tests/test_score_predictions.py` (new)
- `/workspace/experiments/ai_simulation_responses_2026_09_11/shared/tests/test_mirrored_s3_key.py` (new)
- `/workspace/experiments/ai_simulation_responses_2026_09_11/experiment1/README.md` (new)
- `/workspace/experiments/ai_simulation_responses_2026_09_11/experiment1/SETUP.md` (new)
- `/workspace/experiments/ai_simulation_responses_2026_09_11/experiment1/run.py` (new)
- `/workspace/experiments/ai_simulation_responses_2026_09_11/experiment2/README.md` (new)
- `/workspace/experiments/ai_simulation_responses_2026_09_11/experiment2/SETUP.md` (new)
- `/workspace/experiments/ai_simulation_responses_2026_09_11/experiment2/run.py` (new)
- `/workspace/experiments/ai_simulation_responses_2026_09_11/experiment3/README.md` (new)
- `/workspace/experiments/ai_simulation_responses_2026_09_11/experiment3/SETUP.md` (new)
- `/workspace/experiments/ai_simulation_responses_2026_09_11/experiment3/run.py` (new)
- `/workspace/experiments/ai_simulation_responses_2026_09_11/experiment4/README.md` (new)
- `/workspace/experiments/ai_simulation_responses_2026_09_11/experiment4/SETUP.md` (new)
- `/workspace/experiments/ai_simulation_responses_2026_09_11/experiment4/run.py` (new)
- `/workspace/experiments/ai_simulation_responses_2026_09_11/experiment5/README.md` (new)
- `/workspace/experiments/ai_simulation_responses_2026_09_11/experiment5/SETUP.md` (new)
- `/workspace/experiments/ai_simulation_responses_2026_09_11/experiment5/run.py` (new)
- `/workspace/.gitignore` (ignore `cache/` and `outputs/` and local parquet under this experiment folder only)

Do not write `RESULTS.md` or `COST_ESTIMATE.md` in this step. `experiment2/SETUP.md` may contain the unfilled prompt template, and Step 2 will add one filled example after the cohort exists.

## Files forbidden to change

- `/workspace/data_platform/**`
- `/workspace/webapp/**`
- `/workspace/scripts/export_study_results.py`
- `/workspace/lib/constants.py`
- `/workspace/shared/flip_generation/**`
- `/workspace/shared/data/**`
- `/workspace/tests/**`
- `/workspace/CHANGELOG.md`
- Objects under `s3://jspsych-mirror-view-2026-09-09/`

## README contract

Write the parent README and the five experiment READMEs first, then implement modules to match them.

Parent README must:

1. Start with the agent read-only banner.
2. Say this folder runs issue 290 on the September 2026 study.
3. Point at `shared/`, `experiment1` through `experiment5`, `SETUP.md`, and `RESULTS.md`.

Each of experiments 1 to 4 README must:

1. Start with the banner.
2. State the ablation question in one or two sentences.
3. Redirect to that folder's `SETUP.md` and `RESULTS.md`.

Experiment 5 README must say it ranks posts and users with the highest error rates from the four labeling experiments and does not call a model.

## Public contracts

Keep functions under 20 lines. Use frozen dataclasses. Do not pass unstructured dictionaries for source identity. Reuse `CampaignObjectStore`, `parse_s3_uri`, `sha256_hex`, `build_openai_engine`, `label_tasks_collecting_failures`, `write_batch`, and `consolidate_final`. Do not copy a new S3 client. Import `list_csv_keys`, `download_csvs`, and `filter_manual_test_rows` from `scripts/export_study_results.py`. Do not edit that script.

### `constants.py`

Pinned values: posts per user 20, cohort cap 1000 complete participants, smoke user count 10, Bedrock max tokens 256, study bucket `jspsych-mirror-view-2026-09-09`, prefix `data/prolific/`, since date 2026-09-09, output bucket `mirrorview-experimental-artifacts`, output prefix `experiments/ai_simulation_responses_2026_09_11/` (the S3 key equals this local prefix plus the rest of the relative path), model ids from the plan, experiment numbers 1 to 4, model folder names `openai`, `bedrock_micro_nova`, `bedrock_qwen`, `bedrock_claude`. Do not use the older finetune prefix `mirrorview-finetune_qwen_model_2026_08_08/`.

Frozen dataclasses at least:

- `CohortUser` with `prolific_id`, `participant_id`, `source_file_epoch_ms`, `party_group`, demographic fields, `phase1_pair_reflection_text`, `phase1_pair_influence_rating`
- `CohortTrial` with `prolific_id`, `pair_index` (1 to 20), `post_id`, `original_text`, `mirror_text`, `pair_order`, `gold_remove`, `sampled_stance`, `sample_toxicity_type`, `trial_index`
- `ModelSpec` with `folder`, `engine_kind` (`openai` or `bedrock`), `model_id`
- `CostRow` with `model`, `estimated_tokens_in`, `estimated_tokens_out`, `median_cost_usd`, `low_cost_usd`, `high_cost_usd`

### `cohort.py`

- `list_september_csv_keys(store_or_s3_client)` lists keys using `list_csv_keys` with since date 2026-09-09.
- `build_cohort(csv_paths)` returns users and trials. Drop `manual-test` / `pid` / `dev` prolific ids using the export script's filters. Require 20 linked-fate keep/remove trials, stored `pair_order`, reflection text, and influence rating. Sort by `source_file_epoch_ms` ascending, then `prolific_id` for ties, and take at most 1,000 complete participants. If fewer complete users exist, return all of them.
- `pair_index` is 1-indexed in `trial_index` order.

### `prompts.py`

- `STUDY_SYSTEM_PROMPT` is the training_assisted instruction copy plus the 1-indexed remove-list task change from the plan.
- `render_pairs(trials)` writes `## Post pair {n}` then `Post 1:` and `Post 2:` in `pair_order`.
- `render_demographics(user)` emits only non-empty exported fields, using the survey labels in the plan.
- `render_reflection(user)` emits the exact reflection question from `webapp/public/main.js` lines 706 to 722, the written answer, and the 1 to 7 rating with the "Not at all" / "Very much" anchors.
- `render_user_prompt(experiment_number, user, trials)` returns experiment 1 pairs only, experiment 2 demographics then pairs, experiment 3 reflection then pairs, experiment 4 demographics then reflection then pairs.

### `schema.py`

- `LlmRemoveIndexesModel` with `remove_pair_indexes: list[int]`
- `RemoveIndexesRow` with `source_record_id`, `label_timestamp`, `remove_pair_indexes`
- `remove_indexes_spec(engine_type)` returns a `FeatureSpec` whose `system_prompt` is `STUDY_SYSTEM_PROMPT` and whose `llm_output_schema` is `LlmRemoveIndexesModel`
- `expand_remove_indexes(remove_pair_indexes)` returns a length-20 list of 0/1. Raise `ValueError` on duplicates or values outside 1 to 20.

### `openai_runner.py` / `bedrock_runner.py`

Bodies may stay as `raise NotImplementedError` until Step 2, but signatures must exist.

- `openai_runner.label_tasks(spec, tasks)` calls `build_openai_engine`
- `bedrock_runner.label_tasks(spec, tasks, model_id)` calls `label_tasks_collecting_failures` with `max_tokens=256`

### `score.py`

- `user_metrics(gold, pred)` returns accuracy, precision, recall, F1 for one user
- `pooled_metrics(gold, pred)` returns the same four plus `baseline_remove_rate`
- `slice_tables(...)` builds party, toxicity, and stance tables from the plan

### `write.py`

- `mirrored_s3_key(relative_path)` returns the S3 key, which equals the repo-relative path. The path must start with `experiments/ai_simulation_responses_2026_09_11/`. Raise `ValueError` if it does not, or if it has a leading slash, or if it uses the older finetune prefix.
- `put_new_mirrored(store, relative_path, body)` writes `REPO_ROOT / relative_path`, then `store.put_new(relative_path, body)`. The store bucket is `mirrorview-experimental-artifacts`, matching `experiments/generate_study_user_assignments_2026_09_08/constants.py` `OUTPUT_S3_BUCKET` and `experiments/test_separability_original_mirror_posts_2026_09_09/constants.py` `OUTPUT_S3_BUCKET`.
- `upload_cohort(users, trials, store)` writes both parquet files through `put_new_mirrored`
- `require_cohort_keys_absent(store)` raises `FileExistsError` if either key exists
- Later steps reuse `put_new_mirrored` for `COST_ESTIMATE.md`, `RESULTS.md`, and experiment 5 CSVs. Step 1 does not write those files.

Cohort keys:

```text
experiments/ai_simulation_responses_2026_09_11/shared/cohort_users.parquet
experiments/ai_simulation_responses_2026_09_11/shared/cohort_trials.parquet
```

### `run.py`

`parse_args` accepts `--write-cohort`, `--smoke`, `--estimate-cost`, `--print-experiment-2-prompt`, `--experiment`, `--model`, `--score`, `--analyze-errors`. Step 1 only implements `--write-cohort`. Other flags may exist as stubs that raise `NotImplementedError`.

`--write-cohort` prints:

```text
user_count=
trial_rows=
dropped_incomplete=
dropped_missing_pair_order=
dropped_missing_reflection=
users_s3_uri=
trials_s3_uri=
users_sha256=
trials_sha256=
```

### Thin experiment callers

Each of `experiment1/run.py` through `experiment4/run.py` calls `shared/run.py` with a fixed `--experiment`. `experiment5/run.py` only exposes `--analyze-errors`.

## Prompt template (for experiment 2 approval)

System prompt is `STUDY_SYSTEM_PROMPT`. Experiment 2 user prompt shape:

```text
## Participant information

The following answers were provided by the participant whose keep/remove choices you are simulating. Use them if they help you match that participant's decisions.

- Age: {age}
- Gender: {gender}
- Education: {education}
- Political affiliation: {political_affiliation}
- Party lean: {party_lean}
- Party group: {party_group}
- Political ideology (1 = Extremely liberal, 7 = Extremely conservative): {political_ideology}
- How closely do you follow politics (1 = Not closely at all, 7 = Very closely): {political_follow}
- I identify with the Republican Party (1 = Fully Disagree, 7 = Fully agree): {rep_id}
- I identify with the Democratic Party (1 = Fully Disagree, 7 = Fully agree): {dem_id}
- Reducing access to abortion (0 = Strongly Oppose, 100 = Strongly Support): {attitude_reduce_abortion}
- Providing a path to citizenship for undocumented immigrants (0 to 100): {attitude_citizenship_undocumented}
- Increasing restrictions on gun ownership (0 to 100): {attitude_restrict_guns}
- Increasing government regulations to protect the environment (0 to 100): {attitude_regulate_environment}
- Raising taxes on the wealthiest Americans (0 to 100): {attitude_raise_wealth_taxes}
- Expanding Medicaid to cover all currently uninsured Americans (0 to 100): {attitude_expand_medicaid}

## Post pair 1

Post 1:
{first text in pair_order}

Post 2:
{second text in pair_order}

## Post pair 2

...
```

Omit any bullet whose value is empty. Experiment 2 labeling waits on approval of this template.

## Pytest files

Tests must not download S3 and must not call a model. Build in-memory frames in `conftest.py`. Use Arrange-Act-Assert. Name classes `Test{FunctionName}`. Use `result` and `expected`. Patch with `unittest.mock`.

### `tests/test_build_cohort.py`

Class `TestBuildCohort`.

```text
given three complete users with epochs 30, 10, and 20
when build_cohort
then user order is epoch 10, then 20, then 30
and each user has 20 trials
and pair_index runs 1 through 20

given a user with 19 linked-fate decisions
when build_cohort
then that user is dropped
and dropped_incomplete increments

given a user with 20 trials and missing pair_order
when build_cohort
then that user is dropped

given a user with 20 trials and empty reflection text
when build_cohort
then that user is dropped

given 1001 complete users
when build_cohort
then user_count is 1000
and the excluded user is the latest epoch
```

### `tests/test_render_prompt.py`

Class `TestRenderUserPrompt`.

```text
given pair_order ["mirror", "original"]
when render_pairs
then Post 1 is mirror_text and Post 2 is original_text
and the heading is Post pair {pair_index}

given experiment 1
when render_user_prompt
then the prompt has no Participant information heading
and no Participant reflection heading

given experiment 2 and a missing education value
when render_user_prompt
then the education bullet is absent
and the age bullet is present when age is set

given experiment 3
when render_user_prompt
then the prompt contains the reflection question from main.js
and contains the written answer
and contains the 1 to 7 rating
```

### `tests/test_expand_remove_indexes.py`

Class `TestExpandRemoveIndexes`.

```text
given [1, 20]
when expand_remove_indexes
then the length-20 list is 1 at indexes 0 and 19, else 0

given []
when expand_remove_indexes
then all 20 values are 0

given [0]
when expand_remove_indexes
then raise ValueError

given [1, 1]
when expand_remove_indexes
then raise ValueError

given [21]
when expand_remove_indexes
then raise ValueError
```

### `tests/test_mirrored_s3_key.py`

Class `TestMirroredS3Key`.

```text
given experiments/ai_simulation_responses_2026_09_11/shared/cohort_users.parquet
when mirrored_s3_key
then the key equals that path
and the key does not add another prefix

given experiments/ai_simulation_responses_2026_09_11/experiment5/outputs/false_negative_posts.csv
when mirrored_s3_key
then the key equals that path

given shared/cohort_users.parquet
when mirrored_s3_key
then raise ValueError

given /experiments/ai_simulation_responses_2026_09_11/shared/cohort_users.parquet
when mirrored_s3_key
then raise ValueError

given mirrorview-finetune_qwen_model_2026_08_08/data/x.parquet
when mirrored_s3_key
then raise ValueError
```

Tests must not call S3. `put_new_mirrored` may be tested by patching `CampaignObjectStore.put_new` and a temp directory, or left to the live `--write-cohort` command.

### `tests/test_score_predictions.py`

Class `TestUserMetrics` and `TestPooledMetrics`.

```text
given gold [1, 0, 1, 0] and pred [1, 1, 1, 0]
when user_metrics
then precision, recall, f1, and accuracy match sklearn with zero_division=0
and positive class is 1

given two users where user A is all correct and user B is all wrong
and each user has 20 pairs
when mean user-level accuracy
then the mean is 0.5
and pooled accuracy is also 0.5 because both users have the same pair count

given party_group democrat vs republican
when slice_tables
then democrat user-level means use only democrat users
```

## Main caller

```bash
PYTHONPATH=. uv run pytest experiments/ai_simulation_responses_2026_09_11/shared/tests -q
```

Expected: exit 0.

```bash
export AWS_ACCESS_KEY_ID="$LAB_AWS_ACCESS_KEY_ID"
export AWS_SECRET_ACCESS_KEY="$LAB_AWS_ACCESS_KEY_SECRET"

PYTHONPATH=. uv run python experiments/ai_simulation_responses_2026_09_11/shared/run.py --write-cohort
```

Expected: prints the `user_count=` block from above. A second run exits non-zero.

## Must pass

- Imports from `shared/run.py` resolve.
- Parent README and five experiment READMEs exist and carry the banner.
- `PYTHONPATH=. uv run pytest experiments/ai_simulation_responses_2026_09_11/shared/tests -q` exits 0.
- `--write-cohort` writes both parquet files locally and uploads them with `put_new` at keys that equal those relative paths.
- Printed `users_s3_uri=` and `trials_s3_uri=` start with `s3://mirrorview-experimental-artifacts/experiments/ai_simulation_responses_2026_09_11/shared/`.
- Product engines, website files, and `scripts/export_study_results.py` are unchanged.

## Must fail

- Second `--write-cohort` against existing S3 keys.
- Cohort builder keeping a user with 19 trials, missing `pair_order`, or empty reflection.
- `expand_remove_indexes` accepting 0 or 21.
- Experiment 1 prompt containing the demographics heading.
- `mirrored_s3_key` accepting a path outside `experiments/ai_simulation_responses_2026_09_11/` or the older finetune prefix.

## Implement-from-spec notes

Follow `/implement-from-spec`. Full auto. Do not pause after contracts.

Phase 1 names `shared/run.py` `--write-cohort` as the caller.

Phase 2 scaffolds modules with stub bodies and writes READMEs.

Phase 3 locks dataclasses and public signatures. Bodies stay `raise NotImplementedError`.

Phase 4 writes the pytest files from the given/when/then blocks. Tests must fail for `NotImplementedError` or a wrong result, not for missing imports.

Phase 5 implements in this order, one commit per unit of work:

1. README files and `constants.py`
2. `expand_remove_indexes` until `test_expand_remove_indexes.py` is green
3. `render_pairs` / `render_user_prompt` until `test_render_prompt.py` is green
4. `build_cohort` until `test_build_cohort.py` is green
5. `user_metrics` / `pooled_metrics` / `slice_tables` until `test_score_predictions.py` is green
6. `mirrored_s3_key` until `test_mirrored_s3_key.py` is green
7. local parquet writer plus `put_new_mirrored`
8. `--write-cohort` wiring, S3 `put_new`, missing-key error
9. runner signatures and thin experiment `run.py` files

Phase 6 is complete when the pytest command exits 0, `--write-cohort` can run, and Step 2 can smoke without inventing schema or prompt code.
