# Generate study user assignments, results

## Tests

`PYTHONPATH=. uv run pytest experiments/generate_study_user_assignments_2026_09_08/tests -q` exited 0.

## Command

```bash
export AWS_ACCESS_KEY_ID="$LAB_AWS_ACCESS_KEY_ID"
export AWS_SECRET_ACCESS_KEY="$LAB_AWS_ACCESS_KEY_SECRET"

PYTHONPATH=. uv run python experiments/generate_study_user_assignments_2026_09_08/run.py \
  --remaining-labels s3://mirrorview-experimental-artifacts/experiments/calculate_required_label_count_per_stimulus_post_2026_09_09/required_label_count_per_stimulus_post.csv
```

## Files

| File | Path | SHA-256 |
| ---- | ---- | ------- |
| Remaining labels | `s3://mirrorview-experimental-artifacts/experiments/calculate_required_label_count_per_stimulus_post_2026_09_09/required_label_count_per_stimulus_post.csv` | `188d627e8972d9b1ec5eb378814fd02fd588328df0a1ffc8603b0eba63d05c91` |
| New catalog | `s3://mirrorview-experimental-artifacts/experiments/curate_study_2_phase_3_stimuli/flips.csv` | `c90fdcf86e89e393f0de4cc34e1dc4e4bb2bd876405926ad654ff679f3ab4139` |
| Local CSV | `experiments/generate_study_user_assignments_2026_09_08/study_user_assignments.csv` | `e42f4dffbe55bed2c9d2c4dae6829de7508ffefef6564d095b3458d9599752ce` |
| S3 CSV | `s3://mirrorview-experimental-artifacts/experiments/generate_study_user_assignments_2026_09_08/study_user_assignments.csv` | `e42f4dffbe55bed2c9d2c4dae6829de7508ffefef6564d095b3458d9599752ce` |

## Feed kinds

Users 1 through 3202 have 10 left and 10 right. Users 3203 through 3879 have 20 left and 0 right.

| Count | Value |
| ----- | ----: |
| 10:10 feeds | 3202 |
| Left-only feeds | 677 |
| Users | 3879 |
| Assignment slots | 77580 |
| Extra labels | 23 |
| Extra left | 18 |
| Extra right | 5 |
| Unused remaining | 0 |

## Remaining versus assigned slots by cell

| Cell | Remaining | Assigned slots |
| ---- | --------: | -------------: |
| 1 left low | 10445 | 10463 |
| 2 left middle | 22001 | 22001 |
| 3 left high | 13096 | 13096 |
| 4 right low | 8791 | 8796 |
| 5 right middle | 16594 | 16594 |
| 6 right high | 6630 | 6630 |
