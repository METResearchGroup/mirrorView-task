# Step 3: Label the full cohort, one model per Cursor Grok High subagent

## Scope

- **Caller:** `experiments/ai_simulation_responses_2026_09_11/experiment6/run.py --model {openai,bedrock_micro_nova,bedrock_qwen}`
- **Task:** After written approval of `experiment6/COST_ESTIMATE.md`, label every unique cohort user times 20 pairs for the three models. Write campaign parquet parts and `final.parquet` to S3 at keys that equal `experiments/ai_simulation_responses_2026_09_11/experiment6/outputs/{model}/`. Three Cursor Grok High subagents run in parallel, one model per subagent.
- **Out of scope:** scoring (`RESULTS.md` is Step 4), Claude, overwriting smoke objects, overwriting the cohort, editing product engines, experiment 1 through 5 prefixes

## Files to inspect (read-only)

| Path | Why |
|------|-----|
| `/workspace/docs/plans/2026-09-12_ai_simulation_experiment6_795df1/plan.md` | Approval gate, 19,960 rows, no Claude |
| `/workspace/docs/plans/2026-09-12_ai_simulation_experiment6_795df1/steps/step1.md` | Pair ids, `pair_yes_no_spec` |
| `/workspace/docs/plans/2026-09-12_ai_simulation_experiment6_795df1/steps/step2.md` | Approval file |
| `/workspace/experiments/ai_simulation_responses_2026_09_11/shared/run.py` | `run_model_labeling`, `label_full_parts`, `call_full_label_fn`, `require_model_approval` |
| `/workspace/experiments/ai_simulation_responses_2026_09_11/APPROVAL.md` | Experiment 1 through 4 approval. Do not reuse it for experiment 6. |
| `/workspace/data_platform/generate_features/platform_cli.py` | `CAMPAIGN_BATCH_SIZE` is 2000 |

## Files allowed to change

- `/workspace/experiments/ai_simulation_responses_2026_09_11/shared/run.py` (experiment 6 `--model` path, experiment 6 approval path, `pair_yes_no_spec` instead of `remove_indexes_spec`, pair-level `expected_row_count`)
- `/workspace/experiments/ai_simulation_responses_2026_09_11/experiment6/run.py` (already exists from Step 1)
- `/workspace/experiments/ai_simulation_responses_2026_09_11/experiment6/APPROVAL.md` (new, only after the user approves the cost table in writing)
- `/workspace/experiments/ai_simulation_responses_2026_09_11/experiment6/SETUP.md` (record live run ids only)
- `/workspace/experiments/ai_simulation_responses_2026_09_11/shared/tests/test_full_label_paths.py` (experiment 6 approval gate)

Live parquet lives on S3 at keys that equal the local relative paths, and in gitignored local `outputs/`. Do not commit parquet.

## Files forbidden to change

- `/workspace/data_platform/**`
- `/workspace/webapp/**`
- `/workspace/scripts/export_study_results.py`
- `/workspace/lib/constants.py`
- `/workspace/tests/**`
- `/workspace/CHANGELOG.md`
- `/workspace/experiments/ai_simulation_responses_2026_09_11/shared/prompts.py`
- `/workspace/experiments/ai_simulation_responses_2026_09_11/COST_ESTIMATE.md`
- `/workspace/experiments/ai_simulation_responses_2026_09_11/APPROVAL.md`
- Cohort S3 objects
- Smoke prefixes from Step 2
- Experiment 1 through 5 `final.parquet`

## Approval gate

Do not run any `--model` command in this step unless `experiments/ai_simulation_responses_2026_09_11/experiment6/APPROVAL.md` exists.

If that file is missing, the command exits non-zero and names `experiments/ai_simulation_responses_2026_09_11/experiment6/COST_ESTIMATE.md` and `experiments/ai_simulation_responses_2026_09_11/experiment6/APPROVAL.md`.

Do not treat parent `APPROVAL.md` as sufficient. Experiment 1 through 4 `--model` still uses parent `APPROVAL.md` only.

Write `experiment6/APPROVAL.md` only after the user has approved the experiment 6 cost table in the conversation. The file body must say the user approved `experiment6/COST_ESTIMATE.md` and that Claude is excluded.

## Subagent split

Launch three Cursor Grok High subagents after approval. Each subagent owns one model and must not label another model.

| Subagent | Command |
|----------|---------|
| OpenAI | `PYTHONPATH=. uv run python experiments/ai_simulation_responses_2026_09_11/experiment6/run.py --model openai` |
| Nova Micro | `PYTHONPATH=. uv run python experiments/ai_simulation_responses_2026_09_11/experiment6/run.py --model bedrock_micro_nova` |
| Qwen | `PYTHONPATH=. uv run python experiments/ai_simulation_responses_2026_09_11/experiment6/run.py --model bedrock_qwen` |

Do not start Step 4 scoring inside these subagents. Do not start a Claude job.

## Label contract

Root URI:

`s3://mirrorview-experimental-artifacts/experiments/ai_simulation_responses_2026_09_11/experiment6/outputs/`

Call `FeaturePaths.from_root_uri` with that root and feature `{model}`, so `final.parquet` lands at `experiments/ai_simulation_responses_2026_09_11/experiment6/outputs/{model}/final.parquet`. Spec is `pair_yes_no_spec`. `expected_row_count` is 19,960 (998 unique users times 20). Part size is 2000, so parts are `part-00000` through `part-00009`.

`LabelTask.uri` is `{prolific_id}:{pair_index}`. `LabelTask.text` is `render_single_pair(trial)`. Full labeling uses `label_tasks` (not `label_tasks_with_usage`).

Resume skips parts listed in `manifest.json`. If `final.parquet` already exists for that model, print `final exists` and return 0 without labeling.

OpenAI uses `build_openai_engine`. Bedrock uses `label_tasks_collecting_failures` with `max_tokens=256`. Do not retry Bedrock content-filter failures through OpenAI.

Print:

```text
experiment=6
model=
labeled_pairs=
failed_pairs=
scored_users=
failed_users=
final_uri=
```

`scored_users` is the count of prolific ids with 20 successful pair rows. `failed_users` is 998 minus `scored_users`. A user with 19 successes and 1 failure is a failed user. Do not impute `no`.

`--model bedrock_claude` still exits non-zero.

## Must pass

- Three `final.parquet` objects exist after all subagents finish, at `s3://mirrorview-experimental-artifacts/experiments/ai_simulation_responses_2026_09_11/experiment6/outputs/{openai,bedrock_micro_nova,bedrock_qwen}/final.parquet`.
- No `experiment6/outputs/bedrock_claude/` prefix exists.
- Smoke prefixes are unchanged.
- A rerun of the same `--model` after `final.parquet` exists labels 0 new pairs.
- Pytest still exits 0.

## Must fail

- Labeling without `experiment6/APPROVAL.md`
- Using parent `APPROVAL.md` as the experiment 6 gate
- A Claude run that writes experiment 6 objects
- A Qwen run that goes through `build_bedrock_engine`
- Writing experiment 6 labels into experiment 1 prefixes
- Writing labels under a prefix that is not `experiments/ai_simulation_responses_2026_09_11/experiment6/outputs/{model}/`

## Commands

```bash
export AWS_ACCESS_KEY_ID="$LAB_AWS_ACCESS_KEY_ID"
export AWS_SECRET_ACCESS_KEY="$LAB_AWS_ACCESS_KEY_SECRET"

PYTHONPATH=. uv run python experiments/ai_simulation_responses_2026_09_11/experiment6/run.py --model openai
PYTHONPATH=. uv run python experiments/ai_simulation_responses_2026_09_11/experiment6/run.py --model bedrock_micro_nova
PYTHONPATH=. uv run python experiments/ai_simulation_responses_2026_09_11/experiment6/run.py --model bedrock_qwen
```

Expected: each command prints `final_uri=` under `experiment6/outputs/` and `labeled_pairs=` near 19960.

## Implement-from-spec notes

Follow `/implement-from-spec`. Full auto after the approval gate.

Phase 1 names `experiment6/run.py --model openai` as the first caller.

Phase 5: experiment 6 approval helper, pair-level `run_model_labeling` using `pair_yes_no_spec` and 19,960 ids, summary print. One commit per unit of work. Live model jobs are not extra code commits; they are the Step 3 execution.

Phase 6 is complete when the three finals exist or the failed-count printout explains any shortfall.
