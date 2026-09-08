# Calculate required label count per stimulus post, results

## Command

```bash
export AWS_ACCESS_KEY_ID="$LAB_AWS_ACCESS_KEY_ID"
export AWS_SECRET_ACCESS_KEY="$LAB_AWS_ACCESS_KEY_SECRET"

PYTHONPATH=. uv run python experiments/calculate_required_label_count_per_stimulus_post_2026_09_08/run.py
```

## New sample

Object `s3://mirrorview-experimental-artifacts/experiments/filter_posts_used_for_stimulus_dataset_2026_09_08/dataset.parquet` SHA-256 `9788331f898aa27352dcdf32a962b5722aecc1da61a4638b7bbd77a404415ab9` has 10200 rows.

## Old catalog

Catalog `shared/data/raw/study_phase_2_part_2/stimuli/flips.csv` has 10000 unique ids. Remaining labels equal 5 minus the number of unique `prolific_id` raters per `post_id`.

## Remaining labels

| File | Path | SHA-256 |
| ---- | ---- | ------- |
| Local CSV | `experiments/calculate_required_label_count_per_stimulus_post_2026_09_08/required_label_count_per_stimulus_post.csv` | `0c9985db2024cd4b10c8508d6e21edfce5c4eb73beedef8a4e7ba2e8918282a5` |
| S3 CSV | `s3://mirrorview-experimental-artifacts/experiments/calculate_required_label_count_per_stimulus_post_2026_09_08/required_label_count_per_stimulus_post.csv` | `0c9985db2024cd4b10c8508d6e21edfce5c4eb73beedef8a4e7ba2e8918282a5` |

| Batch | Posts | Remaining labels |
| ----- | ----: | ---------------: |
| old | 8899 | 27557 |
| new | 10200 | 51000 |
| total | 19099 | 78557 |
