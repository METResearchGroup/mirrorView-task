# Step 2: Join Jev probabilities and assign bins

Join the five-labeler frame to the stored Jev probabilities, then assign the five bins and the difference score. The caller in this step is `build_comparison_frame` in `experiments/compare_jev_human_uncertainty_2026_09_25/compare.py`. Tests pass frames in. They do not download S3.

## Task

`build_comparison_frame` takes the five-labeler frame and the Jev label frame and returns one row per shared `post_id` with `n_remove`, `p_remove`, `jev_bin`, and `difference_score`.

Out of scope: drawing figures, writing `RESULTS.md`, and uploading to S3. Figures, `RESULTS.md`, and the S3 upload are step 3.

## Decision

Bin edges are `0.0, 0.2, 0.4, 0.6, 0.8, 1.0`.

- Bin 0: `0.0 <= p_remove < 0.2`
- Bin 1: `0.2 <= p_remove < 0.4`
- Bin 2: `0.4 <= p_remove < 0.6`
- Bin 3: `0.6 <= p_remove < 0.8`
- Bin 4: `0.8 <= p_remove <= 1.0`

Bin 0 matches 0 remove votes. A probability below 0 or above 1 raises `ValueError`. The stored file's probabilities run from 0.09 to 0.95, so bin 4 is the closed end and no row lands on 1.0 today.

`difference_score` is `n_remove - jev_bin`. The issue's example is 1 human remove minus Jev bin 0, which is difference 1.

The join is an inner join on `post_id` with `validate="one_to_one"`. Duplicate `post_id` values in either frame raise. The live command in step 3 checks that the join has 15,113 rows. Step 2 unit tests use tiny frames and do not assert 15,113.

The Jev file check, used by the live command and by a pure function the tests call, requires 19,219 rows, unique `post_id`, no missing `p_remove`, and every `p_remove` inside 0 to 1 inclusive.

## Files to inspect

| Path | Why |
|------|-----|
| `/workspace/docs/plans/2026-09-25_jev_human_uncertainty_a38535/plan.md` | Parent plan |
| `/workspace/docs/plans/2026-09-25_jev_human_uncertainty_a38535/steps/step1.md` | Five-labeler frame columns |
| `/workspace/experiments/compare_jev_human_uncertainty_2026_09_25/human_counts.py` | `build_five_labeler_counts` return columns |
| `/workspace/experiments/compare_jev_human_uncertainty_2026_09_25/constants.py` | Constants from step 1 |
| `/workspace/lib/aws/s3.py` | `S3.get_bytes` for the live loader |
| `/workspace/shared/data/dataloader.py` | Bucket name `mirrorview-experimental-artifacts` and the lab-credential copy |

## Files allowed to change

- `/workspace/experiments/compare_jev_human_uncertainty_2026_09_25/constants.py`
- Create `/workspace/experiments/compare_jev_human_uncertainty_2026_09_25/jev_labels.py`
- Create `/workspace/experiments/compare_jev_human_uncertainty_2026_09_25/compare.py`
- Create `/workspace/experiments/compare_jev_human_uncertainty_2026_09_25/tests/test_jev_bins.py`
- Create `/workspace/experiments/compare_jev_human_uncertainty_2026_09_25/tests/test_compare.py`

## Files forbidden to change

- `/workspace/experiments/compare_jev_human_uncertainty_2026_09_25/human_counts.py`
- `/workspace/experiments/compare_jev_human_uncertainty_2026_09_25/tests/test_human_counts.py`
- `/workspace/shared/data/**`
- `/workspace/lib/aws/s3.py`
- `/workspace/docs/runbooks/**`

## Contracts

Add these constants to `constants.py`:

```text
JEV_BUCKET = "mirrorview-experimental-artifacts"
JEV_LABELS_KEY = "experiments/predict_keep_remove_jev_gepa_2026_09_23/jev_baseline_union/A1_pair_study_prompt/labels.parquet"
EXPECTED_JEV_ROWS = 19219
JEV_BIN_EDGES = (0.0, 0.2, 0.4, 0.6, 0.8, 1.0)
JEV_BIN_COUNT = 5
COMPARISON_COLUMNS = ("post_id", "n_remove", "p_remove", "jev_bin", "difference_score")
EXPECTED_JEV_BIN_COUNTS = (1479, 6282, 3774, 2738, 840)
```

`EXPECTED_JEV_BIN_COUNTS[k]` is the number of joined posts in bin `k`. Step 3 asserts `EXPECTED_JEV_BIN_COUNTS`. Step 2 tests do not read `EXPECTED_JEV_BIN_COUNTS`.

`jev_labels.py` file docstring includes:

```text
PYTHONPATH=. uv run pytest experiments/compare_jev_human_uncertainty_2026_09_25/tests/test_jev_bins.py -q
```

```text
assert_jev_label_frame(labels: pd.DataFrame) -> None
  Require columns post_id and p_remove.
  Require len(labels) == EXPECTED_JEV_ROWS, unique post_id, no missing p_remove,
  and every p_remove in [0, 1].
  Raise ValueError on any failed check.

load_jev_labels() -> pd.DataFrame
  Copy LAB_AWS_ACCESS_KEY_ID into AWS_ACCESS_KEY_ID when AWS_ACCESS_KEY_ID is empty,
  and copy LAB_AWS_ACCESS_KEY_SECRET into AWS_SECRET_ACCESS_KEY the same way.
  Download JEV_LABELS_KEY from JEV_BUCKET with lib.aws.s3.S3.get_bytes.
  Read the parquet, call assert_jev_label_frame, and return the frame.
  Tests do not call load_jev_labels.
```

`compare.py` file docstring includes:

```text
PYTHONPATH=. uv run pytest experiments/compare_jev_human_uncertainty_2026_09_25/tests/test_compare.py -q
```

```text
jev_bin_for_probability(probability: float) -> int
  Return bin 0 through 4 using the edges above.
  Raise ValueError when probability is outside [0, 1] or is missing.

attach_jev_bin(frame: pd.DataFrame) -> pd.DataFrame
  Add jev_bin from p_remove. Do not change the input frame.

attach_difference_score(frame: pd.DataFrame) -> pd.DataFrame
  Add difference_score = n_remove - jev_bin. Do not change the input frame.

join_on_post_id(human: pd.DataFrame, jev: pd.DataFrame) -> pd.DataFrame
  Inner join on post_id, validate one_to_one.
  Keep post_id, n_remove, and p_remove.
  Raise ValueError when post_id is duplicated in either input.
  Raise KeyError when post_id or n_remove is missing from human,
  or when post_id or p_remove is missing from jev.

build_comparison_frame(human: pd.DataFrame, jev: pd.DataFrame) -> pd.DataFrame
  join_on_post_id, then attach_jev_bin, then attach_difference_score.
  Column order is COMPARISON_COLUMNS.
```

Do not give these functions default arguments.

## Tests

`tests/test_jev_bins.py`

Class `TestAssertJevLabelFrame` for `assert_jev_label_frame`.

- `test_accepts_complete_frame`: 19,219 rows, unique `post_id`, `p_remove` 0.5. No exception.
- `test_rejects_missing_probability`: one missing `p_remove` raises `ValueError`.
- `test_rejects_wrong_row_count`: 3 rows raise `ValueError`.

Class `TestJevBinForProbability` for `jev_bin_for_probability`.

- Parameterized `test_bin_edges` with these pairs: `0.0 -> 0`, `0.199 -> 0`, `0.2 -> 1`, `0.4 -> 2`, `0.6 -> 3`, `0.8 -> 4`, `0.95 -> 4`, `1.0 -> 4`.
- `test_rejects_above_one`: `1.01` raises `ValueError`.
- `test_rejects_below_zero`: `-0.01` raises `ValueError`.

`tests/test_compare.py`

Class `TestJoinOnPostId` for `join_on_post_id`.

- `test_inner_join_drops_unmatched_posts`: human posts `a` and `b`, Jev posts `b` and `c`. The result is post `b` only.
- `test_duplicate_post_id_raises`: two human rows with `post_id` `a` raise `ValueError`.

Class `TestBuildComparisonFrame` for `build_comparison_frame`.

- `test_difference_score_matches_issue_example`: one row, `n_remove` 1, `p_remove` 0.1. `jev_bin` is 0 and `difference_score` is 1.
- `test_does_not_mutate_inputs`: after the call, the input frames have no `jev_bin` column.

## Pass

`PYTHONPATH=. uv run pytest experiments/compare_jev_human_uncertainty_2026_09_25/tests/test_jev_bins.py experiments/compare_jev_human_uncertainty_2026_09_25/tests/test_compare.py experiments/compare_jev_human_uncertainty_2026_09_25/tests/test_human_counts.py -q` exits 0.

## Fail

The command fails if a new test fails, if a step 1 test regresses, or if `jev_bin_for_probability(0.2)` returns 0.
