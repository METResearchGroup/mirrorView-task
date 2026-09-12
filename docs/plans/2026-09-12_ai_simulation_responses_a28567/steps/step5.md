# Step 5: Analyze error-rate ranks and prediction variance

## Scope

- **Caller:** `experiments/ai_simulation_responses_2026_09_11/experiment5/run.py --analyze-errors`
- **Task:** Read the 16 `final.parquet` files from experiments 1 to 4. Write the 75 false-negative posts, the 75 false-positive posts, the 100 lowest-F1 users, within-user variance, and across-model variance into `experiment5/RESULTS.md`. Upload that report and the three ranked CSVs with `put_new_mirrored`. Do not call a model. Do not train a classifier.
- **Out of scope:** new prompts, new labels, editing experiments 1 to 4 `RESULTS.md`, editing product engines

## Files to inspect (read-only)

| Path | Why |
|------|-----|
| `/workspace/docs/plans/2026-09-12_ai_simulation_responses_a28567/plan.md` | Experiment 5 ranking rules |
| `/workspace/experiments/ai_simulation_responses_2026_09_11/shared/score.py` | User-level F1 helper |
| `/workspace/experiments/ai_simulation_responses_2026_09_11/shared/cohort.py` | Trial fields `sampled_stance`, `sample_toxicity_type` |

## Files allowed to change

- `/workspace/experiments/ai_simulation_responses_2026_09_11/shared/error_analysis.py` (new)
- `/workspace/experiments/ai_simulation_responses_2026_09_11/shared/run.py`
- `/workspace/experiments/ai_simulation_responses_2026_09_11/shared/write.py` (reuse `put_new_mirrored`)
- `/workspace/experiments/ai_simulation_responses_2026_09_11/experiment5/run.py`
- `/workspace/experiments/ai_simulation_responses_2026_09_11/experiment5/RESULTS.md` (new, local and S3)
- `/workspace/experiments/ai_simulation_responses_2026_09_11/experiment5/outputs/false_negative_posts.csv` (new, local and S3)
- `/workspace/experiments/ai_simulation_responses_2026_09_11/experiment5/outputs/false_positive_posts.csv` (new, local and S3)
- `/workspace/experiments/ai_simulation_responses_2026_09_11/experiment5/outputs/lowest_f1_users.csv` (new, local and S3)
- `/workspace/experiments/ai_simulation_responses_2026_09_11/experiment5/SETUP.md` (record input URIs)
- `/workspace/experiments/ai_simulation_responses_2026_09_11/shared/tests/test_error_analysis.py` (new)
- `/workspace/CHANGELOG.md` (one line after live `RESULTS.md` exists)

## Files forbidden to change

- `/workspace/data_platform/**`
- `/workspace/webapp/**`
- `/workspace/experiments/ai_simulation_responses_2026_09_11/shared/prompts.py`
- Cohort parquet
- The 16 `final.parquet` files
- Experiments 1 to 4 `RESULTS.md`

## Analysis contract

`--analyze-errors` exits non-zero if any of the 16 finals is missing, and names the URI.

Pool predictions across experiments 1 to 4 and all four models. For each `prolific_id` plus `pair_index` plus `post_id`, false-negative rate is the share of scored model-experiment cells where gold is 1 and prediction is 0. False-positive rate is the share where gold is 0 and prediction is 1. Ties break by `post_id` ascending.

Write two post lists of 75. If fewer than 75 posts have a nonzero rate, take all of them and print the shortfall. For the combined 150, print counts of `sample_toxicity_type` and `sampled_stance` next to the same counts on all other cohort posts.

Required ranked files, written locally and uploaded with `put_new_mirrored`:

```text
experiments/ai_simulation_responses_2026_09_11/experiment5/outputs/false_negative_posts.csv
experiments/ai_simulation_responses_2026_09_11/experiment5/outputs/false_positive_posts.csv
experiments/ai_simulation_responses_2026_09_11/experiment5/outputs/lowest_f1_users.csv
experiments/ai_simulation_responses_2026_09_11/experiment5/RESULTS.md
```

Print those four S3 URIs. A second `--analyze-errors` against existing keys raises `FileExistsError`. Experiment 5 has no model `final.parquet` folders. The ranked CSVs live under `experiment5/outputs/` as analysis files, not as campaign labels.

User rank: mean of user-level F1 across the 16 model-experiment cells that scored that user. Lowest mean F1 first. Take 100. Describe `party_group`, `political_ideology`, `age`, `education`, and that user's gold remove rate. No extra classifier.

Within-user variance: for experiment 1 only, for each model, per user compute the variance of the 20 per-pair correctness indicators (1 if prediction equals gold). Then report mean, median, 25th percentile, and 75th percentile of those user variances, one row per model.

Across-model variance: for experiment 1 only, for each user-pair, compute the standard deviation of the four models' remove predictions. Then report mean, median, 25th percentile, and 75th percentile of those standard deviations.

## Pytest

Class `TestRankFalseNegativePosts` and `TestRankWorstUsers`.

```text
given two posts where post A is a false negative on every model-experiment cell and post B is never a false negative
when rank false-negative posts
then post A ranks above post B

given 10 users with distinct mean F1
when rank worst users with k=3
then the three lowest F1 users are returned in increasing F1 order
```

Tests use in-memory frames. They must not read S3.

## Must pass

- `experiment5/RESULTS.md` exists locally and at `s3://mirrorview-experimental-artifacts/experiments/ai_simulation_responses_2026_09_11/experiment5/RESULTS.md`, and names 75 false-negative posts, 75 false-positive posts, and 100 users (or the shortfall).
- The three ranked CSVs exist locally and at the matching S3 keys under `experiment5/outputs/`.
- Toxicity and stance shares appear for the 150-post set and for the remaining posts.
- No language model is called.
- `PYTHONPATH=. uv run pytest experiments/ai_simulation_responses_2026_09_11/shared/tests -q` exits 0.
- `CHANGELOG.md` has one line that names issue 290 and the complete-participant count.

## Must fail

- `--analyze-errors` with a missing `final.parquet`
- Adding a new LLM or a trained classifier
- Ranking posts by toxicity instead of error rate
- `--analyze-errors` writing reports only locally and skipping S3
- Taking 150 posts of one error type instead of 75 false negatives plus 75 false positives

## Implement-from-spec notes

Follow `/implement-from-spec`. Full auto.

Phase 1 names `experiment5/run.py --analyze-errors` as the caller.

Phase 4 writes `test_error_analysis.py` before the rankers.

Phase 5 implements false-negative ranking, false-positive ranking, user ranking, then variance summaries, then `RESULTS.md` and the three CSV uploads. One commit per unit of work.

Phase 6 is complete when `RESULTS.md` and the three CSVs exist locally and on S3, pytest is green, and `CHANGELOG.md` has the live complete-participant count.
