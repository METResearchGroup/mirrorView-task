# Calculate v2 remaining labels per stimulus post

<-- NOTE TO AI AGENTS: do NOT touch this file. This file is READ-ONLY. If something here is incorrect or needs updating, inform the user and they will make the change themselves -->

The study needs 5 labels per post. That value lives in `constants.py`. The old batch is unchanged from pull request 271. The new batch is the 10,000 row catalog from `experiments/curate_study_2_phase_3_stimuli/`.

Output columns: `id`, `number_of_times_to_label`, and `batch`.

## Run

```bash
export AWS_ACCESS_KEY_ID="$LAB_AWS_ACCESS_KEY_ID"
export AWS_SECRET_ACCESS_KEY="$LAB_AWS_ACCESS_KEY_SECRET"

PYTHONPATH=. uv run python experiments/calculate_v2_required_label_count_per_stimulus_post_2026_09_08/run.py
```
