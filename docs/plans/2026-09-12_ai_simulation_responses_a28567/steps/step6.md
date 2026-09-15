# Step 6: Repeat experiment 1 with one pair per prompt, then compare

## Scope

- **Caller:** `experiments/ai_simulation_responses_2026_09_11/experiment6/run.py`, dispatched through `shared/run.py` `main` with `--experiment 6`
- **Task:** Reuse the existing unique cohort. Add a one-pair yes/no prompt and a pair-level labeling grain. Smoke 10 users times 20 pairs on OpenAI, Nova Micro, and Qwen. Write `experiment6/COST_ESTIMATE.md` and stop. After written approval, label the unique cohort on those three models. Stitch 20 successful yes/no answers into the experiment 1 remove-list shape. Score experiment 6 and compare it to experiment 1 on the intersection of scored users.
- **Out of scope:** rebuilding the cohort, calling Claude, editing experiment 1 through 5 prompts or `RESULTS.md`, editing parent `COST_ESTIMATE.md`, folding labels into experiment 5, editing product engines

## Files to inspect (read-only)

| Path | Why |
|------|-----|
| `/workspace/docs/plans/2026-09-12_ai_simulation_responses_a28567/plan.md` | Experiment 6 setup, models, compare rows |
| `/workspace/experiments/ai_simulation_responses_2026_09_11/shared/prompts.py` | Confirmed `STUDY_SYSTEM_PROMPT` and `render_pairs`. Do not change the 20-pair string. |
| `/workspace/experiments/ai_simulation_responses_2026_09_11/shared/schema.py` | `LlmRemoveIndexesModel`, `RemoveIndexesRow`, `expand_remove_indexes` |
| `/workspace/experiments/ai_simulation_responses_2026_09_11/shared/run.py` | `--experiment` choices, smoke and full label paths |
| `/workspace/experiments/ai_simulation_responses_2026_09_11/shared/score.py` | Experiment 1 tables. `_load_final_labels` expects `source_record_id` = `prolific_id` and `remove_pair_indexes` |
| `/workspace/experiments/ai_simulation_responses_2026_09_11/experiment1/run.py` | Thin `--experiment 1` wrapper to copy |
| `/workspace/experiments/ai_simulation_responses_2026_09_11/experiment1/RESULTS.md` | Compare baseline. Read only. |
| `/workspace/experiments/filter_posts_used_for_stimulus_dataset_2026_09_08/README.md` | Agent read-only banner text |

## Files allowed to change

- `/workspace/experiments/ai_simulation_responses_2026_09_11/experiment6/README.md` (new)
- `/workspace/experiments/ai_simulation_responses_2026_09_11/experiment6/SETUP.md` (new)
- `/workspace/experiments/ai_simulation_responses_2026_09_11/experiment6/run.py` (new)
- `/workspace/experiments/ai_simulation_responses_2026_09_11/experiment6/COST_ESTIMATE.md` (new, after smoke)
- `/workspace/experiments/ai_simulation_responses_2026_09_11/experiment6/APPROVAL.md` (new, after written approval)
- `/workspace/experiments/ai_simulation_responses_2026_09_11/experiment6/RESULTS.md` (new, after scoring)
- `/workspace/experiments/ai_simulation_responses_2026_09_11/shared/constants.py` (add experiment 6 model order, `PAIR_YES_NO_FEATURE_NAME`, `PAIR_RECORD_SEPARATOR`; do not remove Claude from `MODEL_ORDER`)
- `/workspace/experiments/ai_simulation_responses_2026_09_11/shared/prompts.py` (add `STUDY_SYSTEM_PROMPT_SINGLE_PAIR` and `render_single_pair`; do not edit `STUDY_SYSTEM_PROMPT`)
- `/workspace/experiments/ai_simulation_responses_2026_09_11/shared/schema.py` (add yes/no models, pair record-id helpers, stitch helper)
- `/workspace/experiments/ai_simulation_responses_2026_09_11/shared/run.py` (`--experiment` include 6; pair-level input when experiment is 6; Claude rejection; do not change experiment 1 through 5 command behavior)
- `/workspace/experiments/ai_simulation_responses_2026_09_11/shared/score.py` (experiment 6 scoring and compare tables)
- `/workspace/experiments/ai_simulation_responses_2026_09_11/shared/tests/test_render_prompt.py`
- `/workspace/experiments/ai_simulation_responses_2026_09_11/shared/tests/test_pair_yes_no.py` (new)

Do not write parent `COST_ESTIMATE.md` or experiment 1 through 5 `RESULTS.md` in this step.

## Files forbidden to change

- `/workspace/data_platform/**`
- `/workspace/webapp/**`
- `/workspace/scripts/export_study_results.py`
- `/workspace/lib/constants.py`
- `/workspace/shared/flip_generation/**`
- `/workspace/tests/**`
- `/workspace/experiments/ai_simulation_responses_2026_09_11/README.md` (agent read-only)
- `/workspace/experiments/ai_simulation_responses_2026_09_11/COST_ESTIMATE.md`
- `/workspace/experiments/ai_simulation_responses_2026_09_11/experiment{1,2,3,4,5}/**` except you may read them
- Cohort parquet and all existing experiment 1 through 5 S3 objects

## Setup contract

`experiment6/SETUP.md` must state:

- Humans judged one pair at a time on the website. Experiment 1 showed all 20 pairs in one prompt. Experiment 6 matches the human process. Each call shows one unnumbered pair. The answer is yes or no on whether to remove both posts.
- Shared cohort parquet at `../shared/cohort_users.parquet` and `../shared/cohort_trials.parquet` (also on S3 under the same relative path in `mirrorview-experimental-artifacts`). Use the existing unique `prolific_id` values (998 in the live write). Do not rebuild the cohort.
- The user message is only `Post 1:` and `Post 2:` for that trial, following stored `pair_order`. It does not include a pair number or the other 19 pairs. System prompt is `STUDY_SYSTEM_PROMPT_SINGLE_PAIR` in `../shared/prompts.py`. Model output is JSON `{"remove": "yes"}` or `{"remove": "no"}`.
- Three models label the unique cohort. They are OpenAI `gpt-5.4-nano`, Bedrock Nova Micro, and Bedrock Qwen3 32B. Claude Sonnet 4.6 is excluded.
- After smoke, print one filled one-pair prompt into `SETUP.md`.

`experiment6/README.md` must start with the agent read-only banner, state in one or two sentences that this run repeats experiment 1 with one unnumbered pair per yes/no call and without Claude, then redirect to `SETUP.md` and `RESULTS.md`.

## Prompt and schema contract

Add `STUDY_SYSTEM_PROMPT_SINGLE_PAIR`. Copy the website instruction paragraph and the political-mirror example from `STUDY_SYSTEM_PROMPT`. Do not copy the sentence that says the model will see all 20 pairs. Close with the one-pair instruction. The model must return JSON `{"remove": "yes"}` or `{"remove": "no"}`. `yes` means remove both posts. `no` means keep both.

`render_single_pair(trial)` returns `Post 1:\n{first}\n\nPost 2:\n{second}` using stored `pair_order`. No `## Post pair`. No integer pair index. No "of 20". Do not route experiment 6 through `render_user_prompt`.

Output field `remove` is the string `yes` or the string `no`. Do not use a boolean, `1`/`0`, or `remove_pair_indexes` as the model output field.

Campaign record id is `{prolific_id}:{pair_index}`, parsed with `str.rsplit(":", 1)`. Feature name is `pair_yes_no`. Campaign id is `ai_simulation_responses_2026_09_11_experiment6`.

After 20 successes for one user, map `yes` on study pair `k` onto the user-level remove list as 1-indexed index `k`. `no` omits that index. The scored row shape then matches experiment 1. If any of a user's 20 pair calls fails, drop that user from scoring for that model. Do not impute `no`.

Expected successful rows per model are 998 times 20, which is 19,960. OpenAI Batch part size stays `CAMPAIGN_BATCH_SIZE` (2000), so one model is 10 parts.

`--model bedrock_claude` exits non-zero and names Claude as excluded.

## Smoke and cost contract

Smoke 10 unique cohort users, which is 200 pair calls per remaining model, under `experiment6/outputs/{model}/smoke/`. Call `FeaturePaths.from_root_uri` with root `.../experiment6/outputs/{model}/` and feature `smoke`. Smoke must not copy rows into `final.parquet`.

Cost scaling uses smoke-median tokens per pair call times 19,960 pair calls. Low is 0.5 times median. High is 2 times median. Pricing rates stay the experiment 1 rates for the three models (OpenAI Batch 0.10 / 0.625, Nova 0.035 / 0.14, Qwen 0.15 / 0.60 per million tokens). Write `experiment6/COST_ESTIMATE.md` locally and on S3 with `put_new_mirrored`. Stop. Do not start full labeling in the same command. Do not overwrite parent `COST_ESTIMATE.md`.

`experiment6/run.py --smoke` must not run the experiment 1 smoke path. Bare `--smoke` on `shared/run.py` without `--experiment 6` stays the experiment 1 four-model smoke.

## Label contract

Full `--model` labeling requires `experiments/ai_simulation_responses_2026_09_11/experiment6/APPROVAL.md`. After written approval of the experiment 6 cost table, launch three Cursor Grok High subagents in parallel, one per model. They do not score.

Call `FeaturePaths.from_root_uri` with root `.../experiment6/outputs/` and feature `{model}` so `final.parquet` lands at `experiment6/outputs/{model}/final.parquet`. If `final.parquet` exists, print `final exists` and return without labeling.

Print `labeled_pairs`, `failed_pairs`, `scored_users`, and `failed_users`, plus `final_uri=`.

Scoring starts only when all three `experiment6/outputs/{model}/final.parquet` objects exist.

## Score and compare contract

Scoring reuses the experiment 1 metric definitions. Use scikit-learn `zero_division=0`. The positive class is remove. User-level means are per-user accuracy, precision, recall, and F1. Post-level scores are pooled, plus baseline remove rate, then party, toxicity, and stance tables. Add predicted remove rate (share of scored pairs the model removed). Do not add significance tests.

For each of the three models, restrict the comparison to users scored in both experiment 1 and experiment 6. Required compare rows are user-level F1, post-level F1, accuracy, precision, recall, predicted remove rate, and the human gold remove rate on that intersection. Also report the share of user-pairs where experiment 1 and experiment 6 agree, and within-user variance of per-pair correctness for both experiments.

Write `experiment6/RESULTS.md` locally and on S3. Do not rewrite experiment 1 `RESULTS.md`. Do not fold experiment 6 into experiment 5 error ranks. Do not compare Claude.

## Pytest

Tests live under `experiments/ai_simulation_responses_2026_09_11/shared/tests/` and must not call OpenAI, Bedrock, or S3. Cover one-pair rendering (no pair number, no other pairs, `pair_order` preserved), `yes`/`no` parsing, stitch onto study indexes 1 to 20, all-or-nothing user drop when one pair fails, Claude rejection, and the compare intersection.

## Main caller

```bash
PYTHONPATH=. uv run pytest experiments/ai_simulation_responses_2026_09_11/shared/tests -q
```

Expected: exit 0.

```bash
export AWS_ACCESS_KEY_ID="$LAB_AWS_ACCESS_KEY_ID"
export AWS_SECRET_ACCESS_KEY="$LAB_AWS_ACCESS_KEY_SECRET"

PYTHONPATH=. uv run python experiments/ai_simulation_responses_2026_09_11/experiment6/run.py --smoke
PYTHONPATH=. uv run python experiments/ai_simulation_responses_2026_09_11/experiment6/run.py --estimate-cost
```

Each smoke writes 200 pair labels (10 users times 20) under each of the three models' `experiment6/outputs/{model}/smoke/` prefix on S3. `--estimate-cost` writes `experiment6/COST_ESTIMATE.md` locally and on S3, prints `cost_s3_uri=`, and does not start full labeling. Neither command calls Claude.

After written approval of that cost table in `experiment6/APPROVAL.md`:

```bash
PYTHONPATH=. uv run python experiments/ai_simulation_responses_2026_09_11/experiment6/run.py --model openai
PYTHONPATH=. uv run python experiments/ai_simulation_responses_2026_09_11/experiment6/run.py --model bedrock_micro_nova
PYTHONPATH=. uv run python experiments/ai_simulation_responses_2026_09_11/experiment6/run.py --model bedrock_qwen
```

```bash
PYTHONPATH=. uv run python experiments/ai_simulation_responses_2026_09_11/experiment6/run.py --model bedrock_claude
```

Expected: non-zero exit. Stderr names Claude as excluded from experiment 6.

```bash
PYTHONPATH=. uv run python experiments/ai_simulation_responses_2026_09_11/experiment6/run.py --score
```

Expected: writes `experiment6/RESULTS.md` locally and on S3, prints `results_s3_uri=`, and includes both the experiment 6 tables and the experiment 1 comparison for the three models.

## Must pass

- `experiment6/` exists with README, SETUP, and shared-runner wiring for `--experiment 6`. Experiment 1 through 5 artifacts are unchanged. Claude has no experiment 6 objects.
- Smoke wrote 200 pair calls per remaining model under `experiment6/outputs/{model}/smoke/` and did not write full-run `final.parquet`.
- `experiment6/COST_ESTIMATE.md` exists locally and on S3. Parent `COST_ESTIMATE.md` is unchanged.
- After approval, each of the three models has `s3://mirrorview-experimental-artifacts/experiments/ai_simulation_responses_2026_09_11/experiment6/outputs/{model}/final.parquet`.
- `experiment6/RESULTS.md` exists locally and on S3 with the experiment 1-style tables, predicted remove rate, and the intersection comparison.
- Pytest still exits 0.

## Must fail

- Rebuilding the cohort
- Calling Claude
- Writing experiment 6 labels into experiment 1 prefixes
- Imputing `no` when a pair call fails
- Overwriting parent `COST_ESTIMATE.md` or experiment 1 `RESULTS.md`
- Folding experiment 6 into experiment 5 ranks
- `--smoke` writing into `final.parquet`
- Full labeling without `experiment6/APPROVAL.md`

## Gate

Stop after writing `experiment6/COST_ESTIMATE.md`. Do not start full labeling until the user has approved that table in writing in `experiment6/APPROVAL.md`. Scoring starts only when all three `final.parquet` objects exist.

## Implement-from-spec notes

Follow `/implement-from-spec`. Full auto for prompt, schema, tests, and smoke code, then stop for approval.

Phase 1 names `experiment6/run.py --experiment 6` as the caller.

Phase 5 implements one-pair rendering, yes/no parse, stitch, failed-pair user drop, and Claude rejection until pytest is green, then smoke and cost, then labeling after approval, then score and compare. One commit per unit of work.

Phase 6 is complete when `experiment6/RESULTS.md` exists locally and on S3, the experiment 1 comparison is present, and parent experiment 1 through 5 S3 objects are unchanged.
