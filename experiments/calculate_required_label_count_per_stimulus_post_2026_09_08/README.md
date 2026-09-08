# Calculate required label count per stimulus post

<-- NOTE TO AI AGENTS: do NOT touch this file. This file is READ-ONLY. If something here is incorrect or needs updating, inform the user and they will make the change themselves -->

The next study round needs 5 labels on every stimulus post. That value lives in `constants.py`.

Old batch: unique ids from `shared/data/raw/study_phase_2_part_2/stimuli/flips.csv`. Remaining labels for each id equal 5 minus the number of unique `prolific_id` raters for that id in `shared/data/raw/study_phase_2_part_2/results/full.csv`.

New batch: every post in the 10,200-row parquet from pull request 267 needs 5 labels.

The output CSV has columns `id`, `number_of_times_to_label`, and `batch`. Rows whose remaining count is 0 or less are dropped.

Upload to the `mirrorview-experimental-artifacts` bucket under the prefix `experiments/calculate_required_label_count_per_stimulus_post_2026_09_08/`. The output file is `required_label_count_per_stimulus_post.csv`.

Required files:

- constants.py
- load.py
- calculate.py
- write.py
- run.py

## Run

```bash
export AWS_ACCESS_KEY_ID="$LAB_AWS_ACCESS_KEY_ID"
export AWS_SECRET_ACCESS_KEY="$LAB_AWS_ACCESS_KEY_SECRET"

PYTHONPATH=. uv run python experiments/calculate_required_label_count_per_stimulus_post_2026_09_08/run.py
```
