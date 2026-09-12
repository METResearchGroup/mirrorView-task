# Step 3: Label the full cohort for experiments 1 through 4

## Scope

- **Caller:** `experiments/ai_simulation_responses_2026_09_11/experiment{1,2,3,4}/run.py` with `--model {openai,bedrock_micro_nova,bedrock_qwen,bedrock_claude}`
- **Task:** After written approval of `COST_ESTIMATE.md` and the experiment 2 prompt, label every cohort user for experiments 1 to 4 on all four models. Write campaign parquet parts and `final.parquet`. Four Cursor Grok High subagents run in parallel, one experiment per subagent.
- **Out of scope:** scoring tables (`RESULTS.md` is Step 4), experiment 5, overwriting smoke objects, overwriting the cohort, editing product engines

## Files to inspect (read-only)

| Path | Why |
|------|-----|
| `/workspace/docs/plans/2026-09-12_ai_simulation_responses_a28567/plan.md` | Model list, S3 layout, resume rules |
| `/workspace/docs/plans/2026-09-12_ai_simulation_responses_a28567/steps/step1.md` | Shared runner and schema |
| `/workspace/docs/plans/2026-09-12_ai_simulation_responses_a28567/steps/step2.md` | Approval gate |
| `/workspace/experiments/test_separability_original_mirror_posts_2026_09_09/run.py` | Part loop, `write_batch`, `consolidate_final`, skip existing parts |
| `/workspace/data_platform/generate_features/s3_feature_batches.py` | Immutable parts |
| `/workspace/data_platform/generate_features/platform_cli.py` | `CAMPAIGN_BATCH_SIZE` is 2000 |

## Files allowed to change

- `/workspace/experiments/ai_simulation_responses_2026_09_11/shared/run.py`
- `/workspace/experiments/ai_simulation_responses_2026_09_11/experiment1/run.py`
- `/workspace/experiments/ai_simulation_responses_2026_09_11/experiment2/run.py`
- `/workspace/experiments/ai_simulation_responses_2026_09_11/experiment3/run.py`
- `/workspace/experiments/ai_simulation_responses_2026_09_11/experiment4/run.py`
- `/workspace/experiments/ai_simulation_responses_2026_09_11/experiment1/SETUP.md` (record live run ids only)
- `/workspace/experiments/ai_simulation_responses_2026_09_11/experiment2/SETUP.md`
- `/workspace/experiments/ai_simulation_responses_2026_09_11/experiment3/SETUP.md`
- `/workspace/experiments/ai_simulation_responses_2026_09_11/experiment4/SETUP.md`

Live parquet lives on S3 and in gitignored local `outputs/`. Do not commit parquet.

## Files forbidden to change

- `/workspace/data_platform/**`
- `/workspace/webapp/**`
- `/workspace/scripts/export_study_results.py`
- `/workspace/lib/constants.py`
- `/workspace/tests/**`
- `/workspace/CHANGELOG.md`
- `/workspace/experiments/ai_simulation_responses_2026_09_11/shared/prompts.py` after Step 2 approval (do not silently edit the approved experiment 2 template)
- Cohort S3 objects
- Smoke prefixes from Step 2

## Approval gate

Do not run any command in this step unless the user has approved both of:

1. `experiments/ai_simulation_responses_2026_09_11/COST_ESTIMATE.md`
2. The experiment 2 prompt printed in Step 2

If either approval is missing, the command exits non-zero with a message that names both files.

## Subagent split

Launch four Cursor Grok High subagents after approval. Each subagent owns one experiment folder and must not label another experiment.

| Subagent | Working directory | Commands |
|----------|-------------------|----------|
| Experiment 1 | repo root | `experiment1/run.py --model` for each of the four models |
| Experiment 2 | repo root | same with `experiment2/run.py` |
| Experiment 3 | repo root | same with `experiment3/run.py` |
| Experiment 4 | repo root | same with `experiment4/run.py` |

Each subagent may run its four models sequentially. Do not start Step 4 scoring inside these subagents. Do not start experiment 5.

## Label contract

Root URI:

`s3://mirrorview-experimental-artifacts/experiments/ai_simulation_responses_2026_09_11/experiment{N}/outputs/{model}/`

Reuse `FeaturePaths.from_root_uri`, `write_batch`, `adopt_unrecorded_batch`, `consolidate_final`, `new_manifest`, `save_manifest`, and `append_errors` the same way `experiments/test_separability_original_mirror_posts_2026_09_09/run.py` does.

`LabelTask.uri` is `prolific_id`. `LabelTask.text` is `render_user_prompt(experiment_number, user, trials)`.

Part size is `CAMPAIGN_BATCH_SIZE` (2000). One thousand users become `part-00000` only. Resume skips parts listed in `manifest.json`. If `final.parquet` already exists for that experiment and model, print `final exists` and return 0 without labeling.

OpenAI uses `build_openai_engine`. Bedrock models use `label_tasks_collecting_failures` with the model id from the plan and `max_tokens=256`. Do not retry Bedrock content-filter failures through OpenAI.

Print:

```text
experiment=
model=
labeled=
failed=
final_uri=
```

## Must pass

- Sixteen `final.parquet` objects exist after all subagents finish (4 experiments times 4 models), or fewer only when a model is entirely content-filtered, which must be reported.
- Smoke prefixes are unchanged.
- Experiment 2 prompts match the approved template.
- A rerun of the same `--model` after `final.parquet` exists labels 0 new users.

## Must fail

- Labeling without the approval gate
- A Qwen or Claude run that goes through `build_bedrock_engine`
- Writing experiment 2 labels into experiment 1 prefixes
- Mixing OpenAI rows into a Bedrock `final.parquet`

## Implement-from-spec notes

Follow `/implement-from-spec`. Full auto after the approval gate.

Phase 1 names `experiment1/run.py --model openai` as the first caller. The other 15 commands reuse the same shared path.

Phase 5 implements one model path until it writes a real `final.parquet` on smoke-sized data already covered, then the remaining models. Do not batch all 16 commands into one commit of business logic. Shared resume loop is one unit of work. Each model id wiring is one unit of work.

Phase 6 is complete when the 16 finals exist or the failed-count printout explains any shortfall.
