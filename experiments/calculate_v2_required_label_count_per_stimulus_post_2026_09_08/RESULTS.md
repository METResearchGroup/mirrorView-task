# Calculate v2 required label count per stimulus post, results

## Command

```bash
export AWS_ACCESS_KEY_ID="$LAB_AWS_ACCESS_KEY_ID"
export AWS_SECRET_ACCESS_KEY="$LAB_AWS_ACCESS_KEY_SECRET"

PYTHONPATH=. uv run python experiments/calculate_v2_required_label_count_per_stimulus_post_2026_09_08/run.py
```

## New catalog

Object `s3://mirrorview-experimental-artifacts/experiments/curate_study_2_phase_3_stimuli/flips.csv` SHA-256 `c90fdcf86e89e393f0de4cc34e1dc4e4bb2bd876405926ad654ff679f3ab4139` has 10000 rows.

## Old catalog

Catalog `shared/data/raw/study_phase_2_part_2/stimuli/flips.csv` has 10000 unique ids. Remaining labels equal 5 minus the number of unique `prolific_id` raters per `post_id`.

## Remaining labels

| File | Path | SHA-256 |
| ---- | ---- | ------- |
| Local CSV | `experiments/calculate_v2_required_label_count_per_stimulus_post_2026_09_08/required_label_count_per_stimulus_post.csv` | `188d627e8972d9b1ec5eb378814fd02fd588328df0a1ffc8603b0eba63d05c91` |
| S3 CSV | `s3://mirrorview-experimental-artifacts/experiments/calculate_v2_required_label_count_per_stimulus_post_2026_09_08/required_label_count_per_stimulus_post.csv` | `188d627e8972d9b1ec5eb378814fd02fd588328df0a1ffc8603b0eba63d05c91` |

| Batch | Posts | Remaining labels |
| ----- | ----: | ---------------: |
| old | 8899 | 27557 |
| new | 10000 | 50000 |
| total | 18899 | 77557 |
