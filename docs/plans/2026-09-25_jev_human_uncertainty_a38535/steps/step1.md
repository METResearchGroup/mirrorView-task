# Step 1: Count remove votes for posts with five labelers

Build the five-labeler remove counts from the Part 2 and Part 3 session export. The caller in step 1 is `build_five_labeler_counts` in `experiments/compare_jev_human_uncertainty_2026_09_25/human_counts.py`. Later steps join Jev probabilities onto the five-labeler frame. Step 1 does not download S3 and does not draw figures.

## Task

`build_five_labeler_counts` takes a raw session frame and returns one row per post that has exactly five labelers, with the remove-vote count.

Out of scope: reading the Jev parquet, binning probabilities, figures, `RESULTS.md`, and any edit under `shared/data/`.

## Decision

The session export has no `skip` value on moderation trials. Count `remove` only. Do not add a skip column.

A labeler is one `prolific_id` on one `post_id`. Sort by `post_id`, `prolific_id`, `time_elapsed`, `trial_index` with `kind="mergesort"`, then keep the first row of each pair. The Jev cohort uses the same sort in `dedupe_participant_post` inside `experiments/predict_keep_remove_jev_gepa_2026_09_23/shared/cohort.py` on branch `origin/cursor/predict-keep-remove-jev-gepa-plan-ed3f`. The current export has 2,040 extra rows before the dedupe. After the dedupe, 15,113 posts have five labelers, and the five-labeler set matches the Jev rows whose stored `n_raters` is 5.

Keep rows where `trial_type` is `moderation-trial`, `post_id` is non-empty after strip, and `decision` is `keep` or `remove`. Compare those fields after lowercasing and stripping. Drop a null `post_id` before the string conversion so it does not become the text `nan`.

## Files to inspect

| Path | Why |
|------|-----|
| `/workspace/docs/plans/2026-09-25_jev_human_uncertainty_a38535/plan.md` | Parent plan |
| `/workspace/shared/data/dataloader.py` | `load_dataset` reads the registered CSV from S3. Do not call it in tests. |
| `/workspace/shared/data/registry.py` | `STUDY_PHASE_2_PART_2_AND_3_RESULTS_FULL` |
| `/workspace/shared/data/raw/study_phase_2_part_2_and_3/README.md` | Combined export size |
| `/workspace/experiments/unanimous_vs_majority_labels_2026_08_08/src/build_cohort.py` | Earlier per-post keep and remove counts |
| `/workspace/.cursor/skills/implement-plan-and-open-pr/CODING_RULES.md` | Short functions, named constants, numpy-style docstrings |
| `/workspace/.cursor/skills/implement-plan-and-open-pr/UNIT_TESTING_STANDARDS.md` | One test class per function, arrange-act-assert |

## Files allowed to change

- Create `/workspace/experiments/compare_jev_human_uncertainty_2026_09_25/README.md`
- Create `/workspace/experiments/compare_jev_human_uncertainty_2026_09_25/SETUP.md`
- Create `/workspace/experiments/compare_jev_human_uncertainty_2026_09_25/constants.py`
- Create `/workspace/experiments/compare_jev_human_uncertainty_2026_09_25/human_counts.py`
- Create `/workspace/experiments/compare_jev_human_uncertainty_2026_09_25/tests/__init__.py`
- Create `/workspace/experiments/compare_jev_human_uncertainty_2026_09_25/tests/test_human_counts.py`

## Files forbidden to change

- `/workspace/shared/data/**`
- `/workspace/experiments/predict_keep_remove_jev_gepa_2026_09_23/**`
- `/workspace/webapp/**`
- `/workspace/docs/runbooks/**`

## Contracts

`constants.py` holds:

```text
EXPERIMENT_NAME = "compare_jev_human_uncertainty_2026_09_25"
REQUIRED_LABELERS = 5
DECISION_KEEP = "keep"
DECISION_REMOVE = "remove"
TRIAL_TYPE_MODERATION = "moderation-trial"
HUMAN_COUNT_COLUMNS = ("post_id", "n_raters", "n_remove")
EXPECTED_FIVE_LABELER_POSTS = 15113
EXPECTED_REMOVE_COUNTS = (3986, 4592, 3332, 1929, 950, 324)
```

`EXPECTED_REMOVE_COUNTS[k]` is the number of five-labeler posts with `k` remove votes, for `k` from 0 to 5. Step 3 asserts the live frame against `EXPECTED_FIVE_LABELER_POSTS` and `EXPECTED_REMOVE_COUNTS`. Step 1 tests do not read either constant.

`human_counts.py` file docstring includes:

```text
PYTHONPATH=. uv run pytest experiments/compare_jev_human_uncertainty_2026_09_25/tests/test_human_counts.py -q
```

Functions, in this order:

```text
select_scored_trials(raw: pd.DataFrame) -> pd.DataFrame
  Keep moderation-trial rows with a non-empty post_id and decision keep or remove.
  Raise KeyError when trial_type, post_id, decision, or prolific_id is missing.

dedupe_labeler_post(trials: pd.DataFrame) -> pd.DataFrame
  One row per (prolific_id, post_id), first row after the mergesort above.
  Raise KeyError when prolific_id, post_id, time_elapsed, or trial_index is missing.

aggregate_remove_counts(trials: pd.DataFrame) -> pd.DataFrame
  One row per post_id with n_raters and n_remove.
  n_raters is the row count. n_remove is the count of decision == "remove".
  Columns are HUMAN_COUNT_COLUMNS, sorted by post_id.

posts_with_labeler_count(counts: pd.DataFrame, labeler_count: int) -> pd.DataFrame
  Keep rows whose n_raters equals labeler_count.
  Raise ValueError when labeler_count < 1.

build_five_labeler_counts(raw: pd.DataFrame) -> pd.DataFrame
  select_scored_trials, then dedupe_labeler_post, then aggregate_remove_counts,
  then posts_with_labeler_count with REQUIRED_LABELERS.
```

Do not give these functions default arguments.

## Tests

File: `experiments/compare_jev_human_uncertainty_2026_09_25/tests/test_human_counts.py`

Class `TestSelectScoredTrials` for `select_scored_trials`.

- `test_keeps_moderation_keep_and_remove`: a frame with one keep trial, one remove trial, one instructions row, and one moderation row whose decision is blank. The result has the two scored trials only.
- `test_drops_blank_post_id`: a moderation keep row with a blank `post_id` is dropped.
- `test_missing_column_raises`: a frame without `decision` raises `KeyError`.

Class `TestDedupeLabelerPost` for `dedupe_labeler_post`.

- `test_keeps_first_row_per_person_and_post`: two rows share `prolific_id` `p1` and `post_id` `post-a`. The earlier `time_elapsed` says `remove`, and the later one says `keep`. The result is the `remove` row.

Class `TestAggregateRemoveCounts` for `aggregate_remove_counts`.

- `test_counts_remove_votes`: post `post-a` has two remove rows and one keep row. `n_raters` is 3 and `n_remove` is 2.

Class `TestPostsWithLabelerCount` for `posts_with_labeler_count`.

- `test_keeps_exact_labeler_count`: rows with `n_raters` 4, 5, and 5. `labeler_count` 5 returns the two rows with 5.
- `test_rejects_non_positive_labeler_count`: `labeler_count` 0 raises `ValueError`.

Class `TestBuildFiveLabelerCounts` for `build_five_labeler_counts`.

- `test_returns_only_posts_with_five_labelers`: five distinct people remove or keep `post-a`, and two people rate `post-b`. The result is the single `post-a` row, and `n_remove` matches the remove rows among those five.

## Pass

`PYTHONPATH=. uv run pytest experiments/compare_jev_human_uncertainty_2026_09_25/tests/test_human_counts.py -q` exits 0, and the output ends with a count of passed tests and no failures.

## Fail

The command fails if a test fails, if a test reads S3, or if `select_scored_trials` keeps a row whose decision is not `keep` or `remove`.
