# Step 3: Write the five figures, the results file, and the S3 copies

Draw the five figures, write `RESULTS.md` from the joined frame, and upload the artifacts. The caller is `main` in `experiments/compare_jev_human_uncertainty_2026_09_25/run.py`.

## Task

`main` loads the session export, builds the five-labeler counts, loads the Jev file, builds the comparison frame, checks the pinned counts, writes tables and figures, writes `RESULTS.md`, and uploads those files.

Out of scope: changing the bin edges, changing the five-labeler rule, and editing `human_counts.py` or `compare.py`.

## Decision

Figures use matplotlib with the Agg backend, the same setup as `experiments/unanimous_vs_majority_labels_2026_08_08/src/plot_analysis1_bars.py`. Each figure is a bar chart or a histogram of post counts. The y-axis label is `Posts`.

Figure files, under `experiments/compare_jev_human_uncertainty_2026_09_25/outputs/figures/`:

1. `human_remove_counts.png`. Bars at x = 0, 1, 2, 3, 4, 5. The height is the number of posts with that many remove votes. Missing counts are 0. X-axis label: `Remove votes`.
2. `jev_probability.png`. Histogram of `p_remove` with 20 equal-width bins on the closed range 0 to 1. X-axis label: `Jev p_remove`.
3. `jev_five_bins.png`. Bars at x = 0, 1, 2, 3, 4. Tick labels are `0 remove`, `1 remove`, `2 remove`, `3 remove`, `4 remove`. The height is the number of posts in that Jev bin.
4. `overlay_human_vs_jev.png`. Grouped bars at x = 0, 1, 2, 3, 4, 5. One series is the human remove-vote counts. The other series is the Jev bin counts. The Jev series is 0 at x = 5, because there is no sixth bin. Legend entries: `Human remove votes` and `Jev bin`.
5. `difference_score.png`. Bars at every integer from -4 to 5, including zeros. X-axis label: `Human remove count minus Jev bin`.

Count tables, under `experiments/compare_jev_human_uncertainty_2026_09_25/outputs/tables/`:

- `human_remove_counts.csv` with columns `n_remove`, `n_posts`
- `jev_bins.csv` with columns `jev_bin`, `n_posts`
- `difference_scores.csv` with columns `difference_score`, `n_posts`
- `remove_by_jev_bin.csv`, a crosstab with `n_remove` as rows and `jev_bin` as columns

Also write `outputs/joined.parquet` with `COMPARISON_COLUMNS`. Add `outputs/joined.parquet` to the experiment `.gitignore`. Commit the four CSVs, the five PNGs, and `RESULTS.md`.

`RESULTS.md` is written by `write_results`, not by hand. It contains the five images with relative links, the four tables, the mean difference score rounded to 4 decimal places, and the sentence that moderation trials have no skip decision. The pinned mean is `-0.1946`.

Before writing files, `assert_pinned_counts` checks:

- comparison rows equal `EXPECTED_FIVE_LABELER_POSTS` (15113)
- remove-vote counts equal `EXPECTED_REMOVE_COUNTS`
- Jev bin counts equal `EXPECTED_JEV_BIN_COUNTS`
- mean difference score rounded to 4 decimal places equals `-0.1946`

A mismatch raises `ValueError` and writes nothing.

Upload with `lib.aws.s3.S3.upload_file` to bucket `mirrorview-experimental-artifacts`. The object key is the path relative to the repo root. Uploading an existing key overwrites it. Upload `RESULTS.md`, the five PNGs, the four CSVs, and `outputs/joined.parquet`.

## Files to inspect

| Path | Why |
|------|-----|
| `/workspace/docs/plans/2026-09-25_jev_human_uncertainty_a38535/plan.md` | Parent plan and pinned counts |
| `/workspace/docs/plans/2026-09-25_jev_human_uncertainty_a38535/steps/step1.md` | Five-labeler builder |
| `/workspace/docs/plans/2026-09-25_jev_human_uncertainty_a38535/steps/step2.md` | Comparison frame and Jev loader |
| `/workspace/experiments/unanimous_vs_majority_labels_2026_08_08/src/plot_analysis1_bars.py` | Agg backend and figure paths |
| `/workspace/experiments/unanimous_vs_majority_labels_2026_08_08/RESULTS.md` | Relative image links in a results file |
| `/workspace/lib/aws/s3.py` | `upload_file` |
| `/workspace/shared/data/dataloader.py` | `load_dataset` |

## Files allowed to change

- `/workspace/experiments/compare_jev_human_uncertainty_2026_09_25/constants.py`
- Create `/workspace/experiments/compare_jev_human_uncertainty_2026_09_25/plots.py`
- Create `/workspace/experiments/compare_jev_human_uncertainty_2026_09_25/report.py`
- Create `/workspace/experiments/compare_jev_human_uncertainty_2026_09_25/run.py`
- Create `/workspace/experiments/compare_jev_human_uncertainty_2026_09_25/.gitignore`
- Create `/workspace/experiments/compare_jev_human_uncertainty_2026_09_25/tests/test_plots.py`
- Create `/workspace/experiments/compare_jev_human_uncertainty_2026_09_25/tests/test_report.py`
- Create `/workspace/experiments/compare_jev_human_uncertainty_2026_09_25/RESULTS.md` by running the command
- Create the figure and table files named above by running the command

## Files forbidden to change

- `/workspace/experiments/compare_jev_human_uncertainty_2026_09_25/human_counts.py`
- `/workspace/experiments/compare_jev_human_uncertainty_2026_09_25/jev_labels.py`
- `/workspace/experiments/compare_jev_human_uncertainty_2026_09_25/compare.py`
- `/workspace/experiments/compare_jev_human_uncertainty_2026_09_25/tests/test_human_counts.py`
- `/workspace/experiments/compare_jev_human_uncertainty_2026_09_25/tests/test_jev_bins.py`
- `/workspace/experiments/compare_jev_human_uncertainty_2026_09_25/tests/test_compare.py`
- `/workspace/shared/data/**`
- `/workspace/lib/aws/s3.py`

## Contracts

Add to `constants.py`:

```text
PROBABILITY_HIST_BINS = 20
DIFFERENCE_SCORE_MIN = -4
DIFFERENCE_SCORE_MAX = 5
EXPECTED_MEAN_DIFFERENCE = -0.1946
FIGURE_DIRNAME = "outputs/figures"
TABLE_DIRNAME = "outputs/tables"
JOINED_FILENAME = "outputs/joined.parquet"
RESULTS_FILENAME = "RESULTS.md"
```

`plots.py` file docstring includes:

```text
PYTHONPATH=. uv run pytest experiments/compare_jev_human_uncertainty_2026_09_25/tests/test_plots.py -q
```

Each plot function takes the comparison frame and a destination `Path`, writes one PNG, and returns that path. Names:

```text
plot_human_remove_counts(frame: pd.DataFrame, path: Path) -> Path
plot_jev_probabilities(frame: pd.DataFrame, path: Path) -> Path
plot_jev_five_bins(frame: pd.DataFrame, path: Path) -> Path
plot_overlay(frame: pd.DataFrame, path: Path) -> Path
plot_difference_scores(frame: pd.DataFrame, path: Path) -> Path
write_figures(frame: pd.DataFrame, figure_dir: Path) -> tuple[Path, Path, Path, Path, Path]
```

`write_figures` calls the five plot functions and returns the five paths in the order listed in Decision.

`report.py` file docstring includes:

```text
PYTHONPATH=. uv run pytest experiments/compare_jev_human_uncertainty_2026_09_25/tests/test_report.py -q
```

```text
assert_pinned_counts(frame: pd.DataFrame) -> None
  Raise ValueError when any pinned count or the rounded mean differs.

write_count_tables(frame: pd.DataFrame, table_dir: Path) -> tuple[Path, Path, Path, Path]
  Write the four CSVs. Return paths in the order human, jev bins, difference, crosstab.

write_results(frame: pd.DataFrame, results_path: Path) -> Path
  Write RESULTS.md with the five image links, the four tables, the mean, and the no-skip sentence.

upload_outputs(paths: tuple[Path, ...], bucket: str) -> None
  Upload each path. The key is the path relative to the repo root, using forward slashes.
```

`run.py` file docstring includes:

```text
PYTHONPATH=. uv run python experiments/compare_jev_human_uncertainty_2026_09_25/run.py
```

```text
main() -> None
  load_dataset(STUDY_PHASE_2_PART_2_AND_3_RESULTS_FULL)
  build_five_labeler_counts
  load_jev_labels
  build_comparison_frame
  assert_pinned_counts
  write outputs/joined.parquet
  write_count_tables
  write_figures
  write_results
  upload_outputs
  Print these lines:
    jev_rows=19219
    null_p_remove=0
    five_labeler_posts=15113
    inner_join_posts=15113
```

`README.md` stays the two-line file from step 1. `SETUP.md` already names the two inputs. Do not rewrite `README.md`.

`.gitignore` contains `outputs/joined.parquet` and `__pycache__/`.

## Tests

`tests/test_plots.py`

Class `TestWriteFigures` for `write_figures`.

- `test_writes_five_pngs`: a two-row frame with `n_remove` 0 and 1, `p_remove` 0.1 and 0.85, `jev_bin` 0 and 4, `difference_score` 0 and -3. After `write_figures` into `tmp_path`, five PNG files exist and each starts with the PNG magic bytes `\x89PNG`.

`tests/test_report.py`

Class `TestAssertPinnedCounts` for `assert_pinned_counts`.

- `test_rejects_short_frame`: a one-row comparison frame raises `ValueError`.

Class `TestWriteCountTables` for `write_count_tables`.

- `test_writes_remove_counts`: the same two-row frame. `human_remove_counts.csv` has `n_posts` 1 for `n_remove` 0 and 1 for `n_remove` 1.

Class `TestWriteResults` for `write_results`.

- `test_links_figures_and_states_no_skip`: the written markdown contains `human_remove_counts.png` and the sentence that moderation trials have no skip decision. The test may call `assert_pinned_counts` only if the frame is built to satisfy the pins. For this test, call `write_results` on the two-row frame without the pin check, and do not require the pinned totals in the file. `write_results` writes the counts that are in the frame it receives.

## Pass

Unit tests:

```bash
PYTHONPATH=. uv run pytest experiments/compare_jev_human_uncertainty_2026_09_25/tests -q
```

Expected: the process exits 0.

Live command, from the repo root, with lab credentials in the environment:

```bash
export AWS_ACCESS_KEY_ID="$LAB_AWS_ACCESS_KEY_ID"
export AWS_SECRET_ACCESS_KEY="$LAB_AWS_ACCESS_KEY_SECRET"
export AWS_DEFAULT_REGION=us-east-2
PYTHONPATH=. uv run python experiments/compare_jev_human_uncertainty_2026_09_25/run.py
```

Expected stdout includes:

```text
jev_rows=19219
null_p_remove=0
five_labeler_posts=15113
inner_join_posts=15113
```

Expected exit code: 0.

Expected local files:

- `experiments/compare_jev_human_uncertainty_2026_09_25/outputs/figures/human_remove_counts.png`
- `experiments/compare_jev_human_uncertainty_2026_09_25/outputs/figures/jev_probability.png`
- `experiments/compare_jev_human_uncertainty_2026_09_25/outputs/figures/jev_five_bins.png`
- `experiments/compare_jev_human_uncertainty_2026_09_25/outputs/figures/overlay_human_vs_jev.png`
- `experiments/compare_jev_human_uncertainty_2026_09_25/outputs/figures/difference_score.png`
- `experiments/compare_jev_human_uncertainty_2026_09_25/outputs/tables/human_remove_counts.csv`
- `experiments/compare_jev_human_uncertainty_2026_09_25/outputs/tables/jev_bins.csv`
- `experiments/compare_jev_human_uncertainty_2026_09_25/outputs/tables/difference_scores.csv`
- `experiments/compare_jev_human_uncertainty_2026_09_25/outputs/tables/remove_by_jev_bin.csv`
- `experiments/compare_jev_human_uncertainty_2026_09_25/RESULTS.md`

`human_remove_counts.csv` contains the six rows 3986, 4592, 3332, 1929, 950, 324. `jev_bins.csv` contains 1479, 6282, 3774, 2738, 840.

Expected S3 keys under `s3://mirrorview-experimental-artifacts/`:

- `experiments/compare_jev_human_uncertainty_2026_09_25/RESULTS.md`
- `experiments/compare_jev_human_uncertainty_2026_09_25/outputs/joined.parquet`
- `experiments/compare_jev_human_uncertainty_2026_09_25/outputs/figures/human_remove_counts.png`
- `experiments/compare_jev_human_uncertainty_2026_09_25/outputs/figures/jev_probability.png`
- `experiments/compare_jev_human_uncertainty_2026_09_25/outputs/figures/jev_five_bins.png`
- `experiments/compare_jev_human_uncertainty_2026_09_25/outputs/figures/overlay_human_vs_jev.png`
- `experiments/compare_jev_human_uncertainty_2026_09_25/outputs/figures/difference_score.png`
- `experiments/compare_jev_human_uncertainty_2026_09_25/outputs/tables/human_remove_counts.csv`
- `experiments/compare_jev_human_uncertainty_2026_09_25/outputs/tables/jev_bins.csv`
- `experiments/compare_jev_human_uncertainty_2026_09_25/outputs/tables/difference_scores.csv`
- `experiments/compare_jev_human_uncertainty_2026_09_25/outputs/tables/remove_by_jev_bin.csv`

## Fail

The live command fails if the join is not 15,113 rows, if a pinned count differs, if a figure file is missing, or if an upload raises.
