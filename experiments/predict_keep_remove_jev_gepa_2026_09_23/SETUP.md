# Setup

## Data requirements

1. Registry dataset `STUDY_PHASE_2_PART_3_RESULTS_FULL` at `shared/data/raw/study_phase_2_part_3/results/full.csv` (131,175 rows, frozen 2026-09-22 snapshot).
2. Registry dataset `STUDY_PHASE_2_PART_2_AND_3_RESULTS_FULL` at `shared/data/raw/study_phase_2_part_2_and_3/results/full.csv` (168,871 rows; Part 2 block then Part 3 block).
3. Registry dataset `STUDY_PHASE_2_PART_3_STIMULI` at `shared/data/raw/study_phase_2_part_3/stimuli/flips.csv` (18,899 posts).
4. S3 artifact prefix `s3://mirrorview-experimental-artifacts/experiments/predict_keep_remove_jev_gepa_2026_09_23/`.
5. Wandb project `predict_keep_remove_jev_gepa_2026_09_23` under entity `mind_technology_lab`.

## Build cohort A and frozen splits (Part 3 only)

```bash
export AWS_ACCESS_KEY_ID="$LAB_AWS_ACCESS_KEY_ID"
export AWS_SECRET_ACCESS_KEY="$LAB_AWS_ACCESS_KEY_SECRET"

PYTHONPATH=. uv run python experiments/predict_keep_remove_jev_gepa_2026_09_23/shared/splits.py --write-counts --cohort-source part3
```

Expected counts (frozen 2026-09-24, with dedupe before aggregation):

Counts below are from the spec-correct pipeline (one rating per participant × post, then majority with n_raters ≥ 3). An earlier probe reported 14,941 posts because it aggregated without deduping duplicate participant × post rows first.

| Check | Expected |
|-------|----------|
| Cohort A posts | 14,955 |
| Cohort A keep | 11,775 |
| Cohort A remove | 3,180 |
| Unanimous posts | 4,939 |
| Test split | 2,991 |
| Dev split | 1,496 |
| GEPA pool | 10,468 |
| GEPA val | 300 (150/150) |
| GEPA train | 2,000 (1000/1000) |

Live regression (rebuild from S3, does not rewrite parquet unless you pass `--write-counts` above):

```bash
PYTHONPATH=. uv run python experiments/predict_keep_remove_jev_gepa_2026_09_23/shared/verify_part3_cohort_regression.py
```

## Build union cohort (Part 2 + Part 3) with nested splits

`study_part` on each rating is `part3` when `attention_check_passed` is non-empty and `part2` otherwise (Part 3-only columns are blank on Part 2 rows in the combined export).

```bash
export AWS_ACCESS_KEY_ID="$LAB_AWS_ACCESS_KEY_ID"
export AWS_SECRET_ACCESS_KEY="$LAB_AWS_ACCESS_KEY_SECRET"

PYTHONPATH=. uv run python experiments/predict_keep_remove_jev_gepa_2026_09_23/shared/splits.py --write-counts --cohort-source union
```

Measured union counts (2026-09-24 build):

| Check | Measured |
|-------|----------|
| Union cohort posts | 19,219 |
| Union keep | 15,210 |
| Union remove | 4,009 |
| Remove rate | 20.9% |
| Excluded (missing stance/toxicity) | 0 |
| Overlap with frozen Part 3 cohort A | 14,842 |
| Label changed vs Part 3 | 174 |
| Dropped from Part 3 cohort | 113 |
| New Part 2-only posts | 4,377 |
| Test split | 3,841 |
| Dev split | 1,927 |
| GEPA pool | 13,451 |
| GEPA val | 300 (150/150) |
| GEPA train | 2,000 (1000/1000) |
| Shared test posts with Part 3 test | 2,965 |
| GEPA val members changed vs frozen | 20 |
| GEPA train members changed vs frozen | 120 |

Outputs: `data/cohort_union_splits.parquet`, `data/cohort_union_split_hash.json` (S3 prefix above). Frozen `data/cohort_a_splits.parquet` is not modified.
