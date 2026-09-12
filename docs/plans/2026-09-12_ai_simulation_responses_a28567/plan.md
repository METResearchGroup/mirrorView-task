# Predict September 2026 keep/remove choices with four prompt variants and four models

## Remember
- Exact file paths always
- Exact commands with expected output
- DRY, YAGNI, TDD, frequent commits
- Delegated tasks must be impossible to misread.

## Overview

Issue 290 asks whether language models can match the keep/remove choices that September 2026 MirrorView participants made on 20 linked-fate post pairs. The live study is `mirrorview_2026_09_09` in bucket `jspsych-mirror-view-2026-09-09`. The work lives under `experiments/ai_simulation_responses_2026_09_11/`, and every derived file is also stored on S3 at that same path in bucket `mirrorview-experimental-artifacts`. Four prompt variants share one cohort and one runner. They also share one output schema. A fifth folder only scores errors on those labels. No full model run starts until a smoke cost table is approved. Experiment 2 also waits on prompt-template approval.

## Happy flow

An operator downloads Prolific CSVs from the September bucket. The operator then confirms up to 1,000 complete participants in earliest-upload order and writes one shared cohort locally and on S3. Next the operator smokes 10 users on four models and writes a cost table at the same local path and S3 key. The operator then stops. After approval, four parallel Cursor Grok High subagents label the full cohort for experiments 1 through 4. A later command ranks 75 false-negative posts, 75 false-positive posts, and 100 lowest-F1 users, then uploads those lists to S3.

```mermaid
flowchart TD
    A[Download September Prolific CSVs] --> B[Confirm up to 1000 complete users]
    B --> C[Write shared cohort parquet locally and on S3]
    C --> D[Smoke 10 users on 4 models]
    D --> E[Write COST_ESTIMATE.md locally and on S3]
    E --> F{User approves cost and experiment 2 prompt}
    F -->|no| STOP[Stop]
    F -->|yes| G1[Experiment 1 four models]
    F -->|yes| G2[Experiment 2 four models]
    F -->|yes| G3[Experiment 3 four models]
    F -->|yes| G4[Experiment 4 four models]
    G1 --> H[Score experiments 1 to 4]
    G2 --> H
    G3 --> H
    G4 --> H
    H --> I[Experiment 5 error analysis]
    I --> J[Write RESULTS.md and ranked CSVs locally and on S3]
```

## Approach

Reuse the OpenAI Batch engine and the Bedrock Converse helpers that the original-versus-mirror separability experiment already uses. Do not copy those engines four times. One shared runner takes an experiment number and a model name. Experiments 1 through 4 only change the extra context block in the user prompt. Keep gold labels and predictions as separate parquet objects. Store every derived file in bucket `mirrorview-experimental-artifacts` with an object key that equals the local path, matching the other September 2026 experiments. Treat the four prompt variants as prompt ablations on the same people, not as a causal test of demographics or reflection. Report user-level means and post-level scores separately, because those two aggregations are not the same number. Simplicity and persona notes are in `reviews.md`.

## Decisions

- Create `experiments/ai_simulation_responses_2026_09_11/` with `shared/` plus `experiment1` through `experiment5`. Shared code lives in `shared/`. Each of experiments 1 to 4 has `README.md`, `SETUP.md`, `RESULTS.md`, and `outputs/{openai,bedrock_micro_nova,bedrock_qwen,bedrock_claude}/`. Experiment 5 has no model labels. Experiment 5 does have ranked CSVs under `experiment5/outputs/`.
- Store every derived file on S3 as well as locally. The bucket is `mirrorview-experimental-artifacts`. The object key equals the repo-relative path. `experiments/generate_study_user_assignments_2026_09_08` and `experiments/test_separability_original_mirror_posts_2026_09_09` already use that mapping. Do not copy the older finetune prefix `mirrorview-finetune_qwen_model_2026_08_08/`. Upload with `CampaignObjectStore.put_new`. A second upload of the same key raises `FileExistsError`. Python, tests, `README.md`, and `SETUP.md` stay in git only, because later steps still edit SETUP. Derived parquet, campaign label objects, `COST_ESTIMATE.md`, each `RESULTS.md`, and the experiment 5 ranked CSVs are required on S3. Do not upload to the study website bucket `jspsych-mirror-view-2026-09-09`.
- Parent `experiments/ai_simulation_responses_2026_09_11/README.md` is two sentences that name issue 290 and point at each experiment folder. Each experiment README is one or two sentences for the ablation question, then a redirect to that folder's `SETUP.md` and `RESULTS.md`. Start every README with the agent read-only banner from `experiments/filter_posts_used_for_stimulus_dataset_2026_09_08/README.md`.
- Do not use `shared/data/raw/study_phase_2_part_2/`. The September run is not in the registry yet. Download from `s3://jspsych-mirror-view-2026-09-09/data/prolific/` using the list, download, and filter helpers in `scripts/export_study_results.py`, with `--since-date 2026-09-09`. Keep the S3 filename epoch on every user. Do not sort by assignment-sheet `created_at`.
- A complete user has exactly 20 Phase 1 rows with `evaluation_mode` equal to `linked_fate` and `decision` in `{keep, remove}`, plus a non-empty `phase1_pair_reflection_text` and a 1 to 7 `phase1_pair_influence_rating`. Sort unique `prolific_id` values by the earliest matching `data_<epoch_ms>_*.csv` filename, then take the first 1,000. The target is 1,000 complete participants, not 1,000 trial rows. If fewer than 1,000 complete users exist, take all of them and record the count. `scripts/export_study_results.py` currently expects 190 files, so the live count may be under 1,000.
- Write `cohort_users.parquet` and `cohort_trials.parquet` once, locally and with `CampaignObjectStore.put_new`, at `experiments/ai_simulation_responses_2026_09_11/shared/{cohort_users,cohort_trials}.parquet`. The matching S3 objects are `s3://mirrorview-experimental-artifacts/experiments/ai_simulation_responses_2026_09_11/shared/{cohort_users,cohort_trials}.parquet`. A second upload of either key must raise `FileExistsError` before any model is called. Local parquet stays out of git.
- Pair presentation follows the stored `pair_order` on that trial, so Post 1 and Post 2 match what that participant saw. Do not reshuffle. If `pair_order` is missing or is not a two-item list of `original` and `mirror`, drop the user from the cohort and count the drop. Pair numbers are 1-indexed in the order of those 20 trials after sorting by `trial_index`.
- Gold label is 1 when `decision` is `remove` and 0 when `decision` is `keep`. The model returns a list of 1-indexed pair numbers to remove. Expand that list into 20 binary predictions. An empty list means keep all 20. A duplicate index, a value outside 1 to 20, or a parse failure sends the user to `errors.jsonl` and excludes that user from scoring for that model.
- Shared Pydantic output schema: one field, a list of integers named `remove_pair_indexes`. Persist a row model with `source_record_id`, `label_timestamp`, and that list. `source_record_id` is `prolific_id`.
- Instruction text is the training_assisted copy in `webapp/public/main.js` (the paragraph that starts "We are developing a new social media platform" and the political-mirror example). The task change from the website is that the model sees all 20 pairs at once and returns remove indexes instead of clicking Allow Both or Remove Both on each trial. State in every `SETUP.md` that humans judged one pair at a time and the model sees the full set in one prompt. Do not spend 20 calls per user to make the model judge one pair at a time.
- Experiment 1 user prompt is only the 20 pairs. Experiment 2 prepends every exported demographic and attitude field that is non-empty for that user. Experiment 3 prepends the exact reflection question from `webapp/public/main.js` plus the written answer and the 1 to 7 influence rating. Experiment 4 concatenates the experiment 2 block, then the experiment 3 block, then the pairs. Language, employment, and social-media items are collected in `webapp/public/post_surveys.js` but are not in `columnsToKeep` in `webapp/public/main.js`, so they are unavailable. Do not invent them.
- Demographic fields to render when present, with the survey wording as the label: `age`, `gender`, `education`, `political_affiliation`, `party_lean`, `party_group`, `political_ideology`, `political_follow`, `rep_id`, `dem_id`, `attitude_reduce_abortion`, `attitude_citizenship_undocumented`, `attitude_restrict_guns`, `attitude_regulate_environment`, `attitude_raise_wealth_taxes`, `attitude_expand_medicaid`. Likert items keep the 1 to 7 anchors from `webapp/public/post_surveys.js`. Attitude sliders are 0 to 100.
- Experiment 2 prompt template must be printed by `--print-experiment-2-prompt` and written into `experiments/ai_simulation_responses_2026_09_11/experiment2/SETUP.md` before any experiment 2 model call. Full labeling of experiment 2 waits on explicit approval of that template.
- Models, in output-folder order:
  - `openai`: OpenAI Batch, `gpt-5.4-nano` (`DEFAULT_LLM_MODEL`), through `build_openai_engine`
  - `bedrock_micro_nova`: Bedrock Converse, `us.amazon.nova-micro-v1:0`, through `label_tasks_collecting_failures`
  - `bedrock_qwen`: Bedrock Converse, `qwen.qwen3-32b-v1:0` from `experiments/predict_keep_remove_2026_07_01/models/llm_finetuning/api_baselines/constants.py`
  - `bedrock_claude`: Bedrock Converse, `us.anthropic.claude-sonnet-4-6` (`DEFAULT_BEDROCK_SONNET_MODEL`), the flips model
- Do not call `build_bedrock_engine` for Qwen or Claude, because that factory hardcodes Nova Micro. Do not call `generate_campaign_feature`, because the Reddit campaign retries Bedrock content-filter failures through OpenAI. Raise Bedrock `max_tokens` to 256 on this experiment's Converse calls only, the same override the separability experiment used. Concurrency for Bedrock is `BEDROCK_CAMPAIGN_MAX_CONCURRENCY` (8). OpenAI Batch part size is `CAMPAIGN_BATCH_SIZE` (2000), so 1,000 users become one part per model.
- Label layout matches campaign feature generation. The S3 key and the local relative path are the same string: `experiments/ai_simulation_responses_2026_09_11/experiment{N}/outputs/{model}/` plus `batches/part-NNNNN.parquet`, `manifest.json`, `progress.jsonl`, `errors.jsonl`, `final.parquet`, plus `active_openai_batch.json` or `active_bedrock_job.json` while a job is open. Smoke writes under that model's `smoke/` prefix and must not copy rows into `final.parquet`. Resume by skipping parts already in the manifest. If `final.parquet` exists, the command returns without labeling. Campaign helpers already write those objects to S3. A local cache under the same relative path is allowed and gitignored.
- Pricing constants for the cost table, in USD per million tokens. OpenAI Batch: 0.10 input, 0.625 output, from `data_platform/generate_features/campaign_cost_report.py`. Nova Micro on-demand: 0.035 input, 0.14 output, from the same file. Qwen3 32B on-demand in `us-east-2`: 0.15 input, 0.60 output, from the Bedrock price list. Claude Sonnet 4.6 on-demand: 3.00 input, 15.00 output, from the Bedrock Marketplace listing. Record those source URLs in `COST_ESTIMATE.md`. Smoke 10 users (or the full cohort if smaller) on all four models using the experiment 1 prompt. Estimate experiments 2 to 4 by scaling experiment 1 mean input tokens by the ratio of rendered prompt character counts. Keep output tokens at the experiment 1 smoke mean. Median cost is smoke-median tokens times user count times the rates. Low is 0.5 times median. High is 2 times median. Experiment 5 is 0. Stop after writing the tables. Do not start full labeling in the same command.
- Cost table columns, exactly: model, estimated tokens in, estimated tokens out, median estimated cost, low/high estimated cost. One section per experiment 1 to 4, then a total section. Write `experiments/ai_simulation_responses_2026_09_11/COST_ESTIMATE.md` locally and upload it with `put_new` to `s3://mirrorview-experimental-artifacts/experiments/ai_simulation_responses_2026_09_11/COST_ESTIMATE.md`. Print the file to stdout. A second cost upload raises `FileExistsError`.
- Scoring uses scikit-learn with `zero_division=0`, matching `experiments/finetune_qwen_model_2026_08_08/evaluate.py`. Positive class is remove. User-level scores are precision, recall, F1, and accuracy on that user's 20 pairs, then the mean of those user scores. Post-level scores are the same four metrics on all user-pair rows pooled, plus the baseline remove rate. Party tables repeat user-level scores inside `party_group` `democrat` and `republican`. Toxicity tables repeat post-level scores inside `sample_low_toxicity`, `sample_middle_toxicity`, and `sample_high_toxicity`. Stance tables repeat post-level scores inside `sampled_stance` `left` and `right`. Each table names the scored-row count and the error-row count. Do not add significance tests.
- Experiment 5 uses existing labels and existing post and user fields only. Rank posts by false-negative rate across models and experiments 1 to 4 (model said keep, gold is remove) and take the top 75. Rank posts by false-positive rate (model said remove, gold is keep) and take the top 75. Complementary errors are the split, so the 150-post set is 75 false negatives plus 75 false positives. Compare toxicity and stance shares in that set of 150 against the rest of the cohort posts. Rank users by mean user-level F1 across models and experiments 1 to 4, lowest first, and take 100. Describe those users with `party_group`, `political_ideology`, `age`, `education`, and mean gold remove rate. Within-user variance is the variance of per-pair correctness on experiment 1. Report summary statistics of that variance across users, one row per model. Across-model variance is the standard deviation of the four models' experiment 1 remove predictions on each user-pair. Report summary statistics of those standard deviations. Required ranked files, local and on S3, are `experiment5/outputs/false_negative_posts.csv`, `experiment5/outputs/false_positive_posts.csv`, and `experiment5/outputs/lowest_f1_users.csv`. `experiment5/RESULTS.md` is also required locally and on S3.
- After cost approval, launch four Cursor Grok High subagents in parallel, one per experiment 1 to 4. Each subagent runs all four models for its experiment and does not score. Scoring is Step 4. Experiment 5 starts only when all 16 `final.parquet` objects exist. Do not implement a plugin registry, a prompt-strategy interface, or a second schema.
- Pytest lives under `experiments/ai_simulation_responses_2026_09_11/shared/tests/` and must not call OpenAI, Bedrock, or S3. Cover cohort completeness, pair-order rendering, 1-indexed expansion, the metric tables, and the mirrored S3 key helper. The usual "experiments skip pytest" line in `UNIT_TESTING_STANDARDS.md` does not apply, because a 0-based index bug would invalidate every score.
- Do not edit `data_platform/`, `webapp/`, `scripts/export_study_results.py`, `lib/constants.py`, `shared/flip_generation/`, or files under repo-root `tests/`. Do not upload to the study website bucket. `CHANGELOG.md` waits until a live full run has `RESULTS.md` files.

## Artifact paths

Bucket `mirrorview-experimental-artifacts`. The object key equals the path under the repo root. Export `LAB_AWS_ACCESS_KEY_ID` and `LAB_AWS_ACCESS_KEY_SECRET` as `AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY` before any write, the same way the other experiments do.

| Local path | S3 URI |
| --- | --- |
| `experiments/ai_simulation_responses_2026_09_11/shared/cohort_users.parquet` | `s3://mirrorview-experimental-artifacts/experiments/ai_simulation_responses_2026_09_11/shared/cohort_users.parquet` |
| `experiments/ai_simulation_responses_2026_09_11/shared/cohort_trials.parquet` | `s3://mirrorview-experimental-artifacts/experiments/ai_simulation_responses_2026_09_11/shared/cohort_trials.parquet` |
| `experiments/ai_simulation_responses_2026_09_11/COST_ESTIMATE.md` | `s3://mirrorview-experimental-artifacts/experiments/ai_simulation_responses_2026_09_11/COST_ESTIMATE.md` |
| `experiments/ai_simulation_responses_2026_09_11/experiment{N}/outputs/{model}/` campaign objects | `s3://mirrorview-experimental-artifacts/experiments/ai_simulation_responses_2026_09_11/experiment{N}/outputs/{model}/` |
| `experiments/ai_simulation_responses_2026_09_11/experiment1/outputs/{model}/smoke/` | `s3://mirrorview-experimental-artifacts/experiments/ai_simulation_responses_2026_09_11/experiment1/outputs/{model}/smoke/` |
| `experiments/ai_simulation_responses_2026_09_11/experiment{N}/RESULTS.md` | `s3://mirrorview-experimental-artifacts/experiments/ai_simulation_responses_2026_09_11/experiment{N}/RESULTS.md` |
| `experiments/ai_simulation_responses_2026_09_11/experiment5/outputs/false_negative_posts.csv` | `s3://mirrorview-experimental-artifacts/experiments/ai_simulation_responses_2026_09_11/experiment5/outputs/false_negative_posts.csv` |
| `experiments/ai_simulation_responses_2026_09_11/experiment5/outputs/false_positive_posts.csv` | `s3://mirrorview-experimental-artifacts/experiments/ai_simulation_responses_2026_09_11/experiment5/outputs/false_positive_posts.csv` |
| `experiments/ai_simulation_responses_2026_09_11/experiment5/outputs/lowest_f1_users.csv` | `s3://mirrorview-experimental-artifacts/experiments/ai_simulation_responses_2026_09_11/experiment5/outputs/lowest_f1_users.csv` |

`N` is 1 to 4 for labels and 1 to 5 for `RESULTS.md`. `{model}` is `openai`, `bedrock_micro_nova`, `bedrock_qwen`, or `bedrock_claude`. Git-only files (`*.py`, tests, `README.md`, `SETUP.md`) are not uploaded. Parquet, campaign objects, and experiment 5 CSVs stay out of git. `COST_ESTIMATE.md` and `RESULTS.md` are committed after the live write, and they are also on S3.

## Steps

### Step 1: Add the shared cohort, prompts, schema, runner, and tests

Add the folder layout and confirm the September cohort. Implement prompt rendering, the output schema, the four model runners, the scorer, and the mirrored S3 path helper. Upload the cohort parquet locally and on S3. Do not call OpenAI or Bedrock. See [steps/step1.md](steps/step1.md).

### Step 2: Smoke 10 users, write the cost table, and print the experiment 2 prompt

Run a 10-user smoke on all four models with the experiment 1 prompt. Scale token estimates to experiments 2 to 4. Write `COST_ESTIMATE.md` locally and on S3, and print the experiment 2 template with one filled example. Stop for approval. See [steps/step2.md](steps/step2.md).

### Step 3: Label the full cohort for experiments 1 through 4

After explicit approval of the cost table and the experiment 2 template, run four parallel Cursor Grok High subagents. Each subagent labels all four models for one experiment into campaign parquet parts. See [steps/step3.md](steps/step3.md).

### Step 4: Score experiments 1 through 4

Join each `final.parquet` to the cohort gold labels. Write the user-level, post-level, party, toxicity, and stance tables into each experiment's `RESULTS.md`, then upload each `RESULTS.md` to the matching S3 key. See [steps/step4.md](steps/step4.md).

### Step 5: Analyze error-rate ranks and prediction variance

Read the 16 final parquets. Write the 75 false-negative posts, the 75 false-positive posts, the 100-user list, within-user variance, and across-model variance into `experiments/ai_simulation_responses_2026_09_11/experiment5/RESULTS.md`. Upload that report and the three ranked CSVs to S3. See [steps/step5.md](steps/step5.md).

## What "done" looks like

1. `experiments/ai_simulation_responses_2026_09_11/` has `shared/`, five experiment folders, parent `README.md`, and `COST_ESTIMATE.md` after Step 2.
2. Cohort parquet exists locally and at `s3://mirrorview-experimental-artifacts/experiments/ai_simulation_responses_2026_09_11/shared/` and has at most 1,000 complete participants, each with 20 gold pairs, stored pair order, and a reflection. A second cohort upload fails.
3. Step 2 wrote a cost table in the issue's column layout, smoked 10 users (or fewer) on four models, printed the experiment 2 prompt, and uploaded `COST_ESTIMATE.md` to `s3://mirrorview-experimental-artifacts/experiments/ai_simulation_responses_2026_09_11/COST_ESTIMATE.md`. Full labeling did not run in Step 2.
4. After approval, each of experiments 1 to 4 has four `final.parquet` files, one per model, at `s3://mirrorview-experimental-artifacts/experiments/ai_simulation_responses_2026_09_11/experiment{N}/outputs/{model}/final.parquet`, plus smoke objects that are separate from those finals.
5. Each of experiments 1 to 4 has `RESULTS.md` locally and at the matching S3 key, with user-level means, post-level scores including baseline remove rate, party tables, toxicity tables, and stance tables.
6. Experiment 5 `RESULTS.md` and the three ranked CSVs exist locally and on S3, with 75 false-negative posts, 75 false-positive posts, 100 users, within-user variance, and across-model variance, using only existing fields.
7. Every derived S3 key equals the repo-relative path under `experiments/ai_simulation_responses_2026_09_11/`. Python, tests, README, and SETUP were not uploaded. The study website bucket was not written.
8. `PYTHONPATH=. uv run pytest experiments/ai_simulation_responses_2026_09_11/shared/tests -q` exits 0. Product engines, the website, and the September study bucket objects are unchanged.

## Commands

Run from the repo root. Export AWS keys from `LAB_AWS_ACCESS_KEY_ID` and `LAB_AWS_ACCESS_KEY_SECRET`. Set `OPENAI_API_KEY` before any OpenAI command.

```bash
export AWS_ACCESS_KEY_ID="$LAB_AWS_ACCESS_KEY_ID"
export AWS_SECRET_ACCESS_KEY="$LAB_AWS_ACCESS_KEY_SECRET"

PYTHONPATH=. uv run pytest experiments/ai_simulation_responses_2026_09_11/shared/tests -q
```

Expected: exit 0.

```bash
PYTHONPATH=. uv run python experiments/ai_simulation_responses_2026_09_11/shared/run.py --write-cohort
```

Expected stdout includes `user_count=` (at most 1000 complete participants), `trial_rows=` (20 times user count), the two S3 URIs under `s3://mirrorview-experimental-artifacts/experiments/ai_simulation_responses_2026_09_11/shared/`, and both SHA-256 values. A second run exits non-zero because the cohort keys exist.

```bash
PYTHONPATH=. uv run python experiments/ai_simulation_responses_2026_09_11/shared/run.py --smoke
PYTHONPATH=. uv run python experiments/ai_simulation_responses_2026_09_11/shared/run.py --print-experiment-2-prompt
PYTHONPATH=. uv run python experiments/ai_simulation_responses_2026_09_11/shared/run.py --estimate-cost
```

Each smoke writes 10 labels (or the cohort size if smaller) under each model's `experiment1/outputs/{model}/smoke/` prefix on S3, with a gitignored local cache at that same relative path, and prints `labeled N of N`. `--estimate-cost` writes `COST_ESTIMATE.md` locally and on S3, prints `cost_s3_uri=`, and prints the four experiment sections plus the total. `--print-experiment-2-prompt` prints the template and one filled user. Full labeling must not start.

After written approval of the cost table and the experiment 2 prompt, one subagent per experiment runs the four `--model` commands. Scoring is a later command.

```bash
PYTHONPATH=. uv run python experiments/ai_simulation_responses_2026_09_11/experiment1/run.py --model openai
PYTHONPATH=. uv run python experiments/ai_simulation_responses_2026_09_11/experiment1/run.py --model bedrock_micro_nova
PYTHONPATH=. uv run python experiments/ai_simulation_responses_2026_09_11/experiment1/run.py --model bedrock_qwen
PYTHONPATH=. uv run python experiments/ai_simulation_responses_2026_09_11/experiment1/run.py --model bedrock_claude
```

Replace `experiment1` with `experiment2`, `experiment3`, or `experiment4`. Each label command prints `labeled N` or a scored-count plus failed-count line.

```bash
PYTHONPATH=. uv run python experiments/ai_simulation_responses_2026_09_11/experiment1/run.py --score
```

Replace `experiment1` the same way. `--score` writes that experiment's `RESULTS.md` locally and on S3, and prints `results_s3_uri=`.

```bash
PYTHONPATH=. uv run python experiments/ai_simulation_responses_2026_09_11/experiment5/run.py --analyze-errors
```

Expected: writes `experiment5/RESULTS.md` and the three ranked CSVs locally and on S3, and prints the 75, 75, and 100 counts plus those S3 URIs.
