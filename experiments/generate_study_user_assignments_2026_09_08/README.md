# Generate study user assignments

<-- NOTE TO AI AGENTS: do NOT touch this file. This file is READ-ONLY. If something here is incorrect or needs updating, inform the user and they will make the change themselves -->

Each user sees 20 posts.

The command fills as many 10 left and 10 right feeds as remaining right labels allow, then fills leftover left remaining into 20 left and 0 right feeds. The command does not write 11:9 or 12:8 feeds.

Cells, from `sampled_stance` and `sample_toxicity_type`:

- cell 1: left, `sample_low_toxicity`
- cell 2: left, `sample_middle_toxicity`
- cell 3: left, `sample_high_toxicity`
- cell 4: right, `sample_low_toxicity`
- cell 5: right, `sample_middle_toxicity`
- cell 6: right, `sample_high_toxicity`

Recipe 1 preferred counts, in cell order 1 through 6, are 2, 5, 3, 2, 5, 3. Recipe 2 preferred counts are 3, 5, 2, 3, 5, 2. Odd 10:10 users inside the 10:10 block use recipe 1. Even 10:10 users use recipe 2. Odd left-only users inside the left-only block prefer 4, 10, 6 from cells 1, 2, 3. Even left-only users prefer 6, 10, 4.

Steal stays inside left cells 1 to 3, or inside right cells 4 to 6. Party mix does not slip. Toxicity may slip. Remaining count may go below 0, and those assignments are extra labels.

Catalog shuffle uses seed 0. Each feed is shuffled with a numpy generator seeded by the user id.

Output columns are `id`, `assigned_post_ids`, `political_party`, `condition`, `created_at`.

Upload to `s3://mirrorview-experimental-artifacts/experiments/generate_study_user_assignments_2026_09_08/study_user_assignments.csv`.

Required files:

- constants.py
- load.py
- assign.py
- write.py
- run.py
- tests/ under this folder

## Tests

```bash
PYTHONPATH=. uv run pytest experiments/generate_study_user_assignments_2026_09_08/tests -q
```

## Run

```bash
export AWS_ACCESS_KEY_ID="$LAB_AWS_ACCESS_KEY_ID"
export AWS_SECRET_ACCESS_KEY="$LAB_AWS_ACCESS_KEY_SECRET"

PYTHONPATH=. uv run python experiments/generate_study_user_assignments_2026_09_08/run.py \
  --remaining-labels s3://mirrorview-experimental-artifacts/experiments/calculate_required_label_count_per_stimulus_post_2026_09_09/required_label_count_per_stimulus_post.csv
```
