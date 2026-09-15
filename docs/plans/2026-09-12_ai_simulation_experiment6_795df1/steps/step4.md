# Step 4: Score experiment 6 and compare it to experiment 1

## Scope

- **Caller:** `experiments/ai_simulation_responses_2026_09_11/experiment6/run.py --score`
- **Task:** Join each experiment 6 `final.parquet` to `cohort_trials.parquet`. Parse pair record ids and `remove` yes/no into 20 binary predictions per complete user. Write the experiment 1-style metric tables plus an intersection comparison against experiment 1 into `experiment6/RESULTS.md`, then upload the same bytes with `put_new_mirrored`.
- **Out of scope:** experiment 5, new model calls, Claude rows, changing gold labels, rewriting experiment 1 `RESULTS.md`

## Files to inspect (read-only)

| Path | Why |
|------|-----|
| `/workspace/docs/plans/2026-09-12_ai_simulation_experiment6_795df1/plan.md` | Compare rows, predicted remove rate, intersection |
| `/workspace/experiments/ai_simulation_responses_2026_09_11/shared/score.py` | `score_experiment`, `user_metrics`, `pooled_metrics`, `write_results_md`, `_load_final_labels`, `_prediction_by_user` |
| `/workspace/experiments/ai_simulation_responses_2026_09_11/experiment1/RESULTS.md` | Table layout to copy for the experiment 6 section |
| `/workspace/experiments/ai_simulation_responses_2026_09_11/shared/error_analysis.py` | Within-user variance formula already used for experiment 1 |
| `/workspace/experiments/ai_simulation_responses_2026_09_11/shared/schema.py` | `stitch_pair_predictions`, `parse_pair_record_id`, `parse_remove_yes_no`, `expand_remove_indexes` |
| `/workspace/experiments/finetune_qwen_model_2026_08_08/evaluate.py` | sklearn `zero_division=0` |

## Files allowed to change

- `/workspace/experiments/ai_simulation_responses_2026_09_11/shared/score.py` (experiment 6 loader, predicted remove rate, compare section; do not change how experiments 1 through 4 load `remove_pair_indexes`)
- `/workspace/experiments/ai_simulation_responses_2026_09_11/shared/run.py` (`--score` allows experiment 6)
- `/workspace/experiments/ai_simulation_responses_2026_09_11/shared/write.py` (reuse `put_new_mirrored`)
- `/workspace/experiments/ai_simulation_responses_2026_09_11/experiment6/RESULTS.md` (new, local and S3)
- `/workspace/experiments/ai_simulation_responses_2026_09_11/shared/tests/test_score_predictions.py` (experiment 6 stitch scoring and intersection compare)
- `/workspace/CHANGELOG.md` (one line, only after `RESULTS.md` exists)

## Files forbidden to change

- `/workspace/data_platform/**`
- `/workspace/webapp/**`
- `/workspace/experiments/ai_simulation_responses_2026_09_11/shared/prompts.py`
- `/workspace/experiments/ai_simulation_responses_2026_09_11/experiment{1,2,3,4,5}/RESULTS.md`
- Cohort parquet
- Any `final.parquet` or smoke object
- Experiment 5 ranked CSVs

## Scoring contract

`--score` requires `final.parquet` for `openai`, `bedrock_micro_nova`, and `bedrock_qwen` under experiment 6. If one is missing, exit non-zero and name the URI. Do not require a Claude file.

Join:

- Pair-level `source_record_id` parses to `(prolific_id, pair_index)`.
- `remove` is `yes` or `no`. Invalid values count as a failed pair.
- Users in `errors.jsonl` (pair ids) fail the parent user.
- A user with fewer than 20 successful pairs is a `failed_user` and is omitted from that model's scores.
- Successful users go through `stitch_pair_predictions` then `expand_remove_indexes`.

Positive class is remove (1). Use sklearn accuracy, precision, recall, and F1 with `zero_division=0`.

### Experiment 6 tables (same shape as experiment 1)

User-level: model, n_users, mean accuracy, mean precision, mean recall, mean F1.

Post-level: model, n_pairs, baseline remove rate, accuracy, precision, recall, F1, plus predicted remove rate (`mean(pred)` on the same pooled pairs).

Party: `party_group=democrat` and `party_group=republican`, user-level columns.

Toxicity: `sample_low_toxicity`, `sample_middle_toxicity`, `sample_high_toxicity`, post-level columns.

Stance: `sampled_stance` `left` and `right`, post-level columns.

Each table states `scored_users` or `scored_pairs` and `failed_users`. Three model rows only. Do not add p-values.

### Comparison against experiment 1

Load existing `experiment1/outputs/{model}/final.parquet` for the same three models. For each model, keep users who have 20 valid predictions in both experiments.

Required compare table columns, one row per model:

- n_users in the intersection
- experiment 1 user-level F1
- experiment 6 user-level F1
- experiment 1 post-level F1
- experiment 6 post-level F1
- experiment 1 accuracy
- experiment 6 accuracy
- experiment 1 precision
- experiment 6 precision
- experiment 1 recall
- experiment 6 recall
- experiment 1 predicted remove rate
- experiment 6 predicted remove rate
- gold remove rate on the intersection
- agreement rate (share of user-pairs where both experiments predict the same keep/remove)

Also report within-user variance of per-pair correctness (same definition as experiment 5's experiment 1 variance): mean, median, p25, p75, one row per model per experiment.

`--score` prints the experiment 6 user-level table, the post-level table (including predicted remove rate), and the compare table, plus `results_s3_uri=`.

Upload with `put_new_mirrored` to `experiments/ai_simulation_responses_2026_09_11/experiment6/RESULTS.md`. A second `--score` raises `FileExistsError` if that key exists.

`--score` on experiments 1 through 4 must still require four models including Claude and must still omit predicted remove rate unless that would change frozen `RESULTS.md` files (it must not; those files already exist on S3). Do not regenerate experiment 1 through 4 `RESULTS.md`.

## Tests

1. Given 20 `yes`/`no` pair rows for one user, when experiment 6 score, then user-level pred matches stitch plus `expand_remove_indexes`.
2. Given 19 pair rows, when score, then that user is `failed_users` and is absent from user-level means.
3. Given experiment 1 pred `[1,0,...]` and experiment 6 pred `[0,0,...]` on the same user, when compare, then agreement rate uses 19/20 if only the first pair differs.
4. Given `score_experiment(1, ...)`, when run, then it still iterates `MODEL_ORDER` (four models) and still reads `remove_pair_indexes`.
5. Predicted remove rate equals `sum(pred) / len(pred)` on pooled pairs.

## Must pass

- `experiment6/RESULTS.md` exists locally and at `s3://mirrorview-experimental-artifacts/experiments/ai_simulation_responses_2026_09_11/experiment6/RESULTS.md`.
- Three models appear. Claude does not.
- User-level mean accuracy is the mean of per-user accuracies.
- Baseline remove rate and predicted remove rate both appear in the post-level table.
- Compare tables use the per-model intersection.
- Experiment 1 `RESULTS.md` on disk and S3 is unchanged.
- Pytest still exits 0.
- `CHANGELOG.md` has one 2026-09-12 (or run date) line for experiment 6 after the live `RESULTS.md` write.

## Must fail

- `--score` when a required experiment 6 `final.parquet` is missing
- `--score` requiring Claude
- Treating user-level F1 as pooled F1
- Counting incomplete users as scored
- Imputing `no` for failed pairs
- `--score` writing `RESULTS.md` only locally
- Rewriting experiment 1 `RESULTS.md`
- Folding experiment 6 into experiment 5 CSVs

## Commands

```bash
export AWS_ACCESS_KEY_ID="$LAB_AWS_ACCESS_KEY_ID"
export AWS_SECRET_ACCESS_KEY="$LAB_AWS_ACCESS_KEY_SECRET"

PYTHONPATH=. uv run python experiments/ai_simulation_responses_2026_09_11/experiment6/run.py --score
PYTHONPATH=. uv run pytest experiments/ai_simulation_responses_2026_09_11/shared/tests -q
```

Expected: `results_s3_uri=s3://mirrorview-experimental-artifacts/experiments/ai_simulation_responses_2026_09_11/experiment6/RESULTS.md` and pytest exit 0.

## Implement-from-spec notes

Follow `/implement-from-spec`. Full auto.

Phase 1 names `experiment6/run.py --score` as the caller.

Phase 4 adds pytest cases for stitch scoring, failed-pair drop, predicted remove rate, and intersection agreement.

Phase 5: experiment 6 label loader, predicted remove rate on post-level, compare renderer, `--score` dispatch, CHANGELOG. One commit per unit of work.

Phase 6 is complete when `RESULTS.md` exists locally and on S3 and stdout printed the experiment 6 tables plus the compare table.
