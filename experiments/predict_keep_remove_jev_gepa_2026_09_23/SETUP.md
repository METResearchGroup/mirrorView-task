# Setup

## Data requirements

1. Registry dataset `STUDY_PHASE_2_PART_3_RESULTS_FULL` at `shared/data/raw/study_phase_2_part_3/results/full.csv` (131,175 rows, frozen 2026-09-22 snapshot).
2. Registry dataset `STUDY_PHASE_2_PART_3_STIMULI` at `shared/data/raw/study_phase_2_part_3/stimuli/flips.csv` (18,899 posts).
3. S3 artifact prefix `s3://mirrorview-experimental-artifacts/experiments/predict_keep_remove_jev_gepa_2026_09_23/`.
4. Wandb project `predict_keep_remove_jev_gepa_2026_09_23` under entity `mind_technology_lab`.

## Build cohort A and frozen splits

```bash
export AWS_ACCESS_KEY_ID="$LAB_AWS_ACCESS_KEY_ID"
export AWS_SECRET_ACCESS_KEY="$LAB_AWS_ACCESS_KEY_SECRET"

PYTHONPATH=. uv run python experiments/predict_keep_remove_jev_gepa_2026_09_23/shared/splits.py --write-counts
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
