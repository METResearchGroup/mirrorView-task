# Generate study user assignments

<-- NOTE TO AI AGENTS: do NOT touch this file. This file is READ-ONLY. If something here is incorrect or needs updating, inform the user and they will make the change themselves -->

Each user sees 20 posts.

The run writes as many feeds with 10 left posts and 10 right posts as the remaining right labels can fill. It then writes the leftover left remaining labels into feeds with 20 left posts and 0 right posts. It does not write an 11 and 9 feed or a 12 and 8 feed.

Cells, from `sampled_stance` and `sample_toxicity_type`:

- cell 1: left, `sample_low_toxicity`
- cell 2: left, `sample_middle_toxicity`
- cell 3: left, `sample_high_toxicity`
- cell 4: right, `sample_low_toxicity`
- cell 5: right, `sample_middle_toxicity`
- cell 6: right, `sample_high_toxicity`

Recipe 1 preferred counts, in cell order 1 through 6, are 2, 5, 3, 2, 5, 3. Recipe 2 preferred counts are 3, 5, 2, 3, 5, 2. Odd 10:10 users inside the 10:10 block use recipe 1. Even 10:10 users use recipe 2. Odd left-only users inside the left-only block prefer 4, 10, 6 from cells 1, 2, 3. Even left-only users prefer 6, 10, 4 from cells 1, 2, 3.

If a cell does not have enough remaining labels, the assignment takes posts from another cell of the same party. Left posts come only from cells 1 to 3, and right posts come only from cells 4 to 6. A 10 left and 10 right feed stays 10 and 10, and a left-only feed stays 20 left and 0 right. The toxicity mix can differ from the preferred counts. A post can be assigned more times than its remaining count, and those extra assignments are extra labels.

Catalog shuffle uses seed 0. Each feed is shuffled with a seed equal to the user id.

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

## Live run

The live remaining-labels file produced 3,202 feeds at 10 left and 10 right, 677 left-only feeds, and 3,879 assignment rows.

## Verification page

`verification.html` in this folder runs the party-mix and extra-label checks in the browser. It loads `verification_dataset.json` by default, and it can recompute the same checks from local CSVs.

Preview (Vercel, this branch): [experiments/generate_study_user_assignments_2026_09_08/verification.html](https://mirrorview-task-git-cursor-study-13766b-marktorres10s-projects.vercel.app/experiments/generate_study_user_assignments_2026_09_08/verification.html)


## Run

```bash
export AWS_ACCESS_KEY_ID="$LAB_AWS_ACCESS_KEY_ID"
export AWS_SECRET_ACCESS_KEY="$LAB_AWS_ACCESS_KEY_SECRET"

PYTHONPATH=. uv run python experiments/generate_study_user_assignments_2026_09_08/run.py \
  --remaining-labels s3://mirrorview-experimental-artifacts/experiments/calculate_required_label_count_per_stimulus_post_2026_09_09/required_label_count_per_stimulus_post.csv
```
