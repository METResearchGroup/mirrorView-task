# Step 4: Score experiments 1 through 4

## Scope

- **Caller:** `experiments/ai_simulation_responses_2026_09_11/experiment{1,2,3,4}/run.py --score`
- **Task:** Join each model's `final.parquet` to `cohort_trials.parquet`. Expand `remove_pair_indexes` into 20 binary predictions. Write user-level, post-level, party, toxicity, and stance tables into that experiment's `RESULTS.md`, then upload the same bytes with `put_new_mirrored`.
- **Out of scope:** experiment 5, new model calls, changing gold labels, editing product engines

## Files to inspect (read-only)

| Path | Why |
|------|-----|
| `/workspace/docs/plans/2026-09-12_ai_simulation_responses_a28567/plan.md` | Metric tables and positive class |
| `/workspace/experiments/ai_simulation_responses_2026_09_11/shared/score.py` | `user_metrics`, `pooled_metrics`, `slice_tables` |
| `/workspace/experiments/finetune_qwen_model_2026_08_08/evaluate.py` | sklearn `zero_division=0` |
| `/workspace/experiments/test_separability_original_mirror_posts_2026_09_09/RESULTS.md` | Table tone for an experiment RESULTS file |

## Files allowed to change

- `/workspace/experiments/ai_simulation_responses_2026_09_11/shared/score.py`
- `/workspace/experiments/ai_simulation_responses_2026_09_11/shared/run.py`
- `/workspace/experiments/ai_simulation_responses_2026_09_11/shared/write.py` (reuse `put_new_mirrored` for each RESULTS file)
- `/workspace/experiments/ai_simulation_responses_2026_09_11/experiment1/RESULTS.md` (new, local and S3)
- `/workspace/experiments/ai_simulation_responses_2026_09_11/experiment2/RESULTS.md` (new, local and S3)
- `/workspace/experiments/ai_simulation_responses_2026_09_11/experiment3/RESULTS.md` (new, local and S3)
- `/workspace/experiments/ai_simulation_responses_2026_09_11/experiment4/RESULTS.md` (new, local and S3)
- `/workspace/experiments/ai_simulation_responses_2026_09_11/shared/tests/test_score_predictions.py` (add table-shape cases if missing)

## Files forbidden to change

- `/workspace/data_platform/**`
- `/workspace/webapp/**`
- `/workspace/CHANGELOG.md` until Step 5 has experiment 5 `RESULTS.md`
- Cohort parquet
- Any `final.parquet` or smoke object
- `shared/prompts.py`

## Scoring contract

`--score` requires `final.parquet` for all four models of that experiment. If one is missing, exit non-zero and name the URI.

Join key is `prolific_id` = `source_record_id`. Users in `errors.jsonl` are omitted from that model's scores and counted as `failed_users`.

`expand_remove_indexes` must not raise on a stored row. Rows that would raise should already be in `errors.jsonl`. If a stored list is invalid, count it as failed rather than crashing the whole score run.

Positive class is remove (1). Use sklearn accuracy, precision, recall, and F1 with `zero_division=0`.

### User-level table

One row per model. Columns: model, n_users, mean accuracy, mean precision, mean recall, mean F1.

### Post-level table

One row per model. Columns: model, n_pairs, baseline remove rate, accuracy, precision, recall, F1.

### By political stance (user-level)

Two blocks, `party_group=democrat` and `party_group=republican`. Same columns as the user-level table. Users with empty `party_group` are omitted from these blocks only.

### By toxicity tier of the original post (post-level)

Three blocks: `sample_low_toxicity`, `sample_middle_toxicity`, `sample_high_toxicity`. Same columns as the post-level table.

### By political lean of the original post (post-level)

Two blocks: `sampled_stance=left` and `sampled_stance=right`. Same columns as the post-level table.

Each table states `scored_users` or `scored_pairs` and `failed_users`. Do not add p-values.

`--score` also prints the user-level table and the post-level table to stdout, plus `results_s3_uri=` for that experiment.

Each `RESULTS.md` is uploaded with `put_new_mirrored` so the S3 key equals `experiments/ai_simulation_responses_2026_09_11/experiment{N}/RESULTS.md`. A second `--score` for the same experiment raises `FileExistsError` if that key exists.

## Must pass

- Four `RESULTS.md` files exist, one per experiment 1 to 4, locally and at `s3://mirrorview-experimental-artifacts/experiments/ai_simulation_responses_2026_09_11/experiment{N}/RESULTS.md`.
- User-level mean accuracy is the mean of per-user accuracies, not the pooled accuracy relabeled as user-level.
- Baseline remove rate appears in every post-level table.
- Pytest still exits 0.

## Must fail

- `--score` when a model `final.parquet` is missing
- Treating user-level F1 as pooled F1
- Counting `errors.jsonl` users as correct
- `--score` writing `RESULTS.md` only locally and skipping S3

## Implement-from-spec notes

Follow `/implement-from-spec`. Full auto.

Phase 1 names `experiment1/run.py --score` as the caller.

Phase 4 adds any missing pytest cases for party, toxicity, and stance slices on in-memory frames.

Phase 5 implements `write_results_md` then wires `--score`. One commit per unit of work.

Phase 6 is complete when all four `RESULTS.md` files exist and stdout printed both overall tables for experiment 1.
