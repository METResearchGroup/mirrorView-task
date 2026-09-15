# Setup

Labels come from the latest September 2026 Prolific export through `scripts/export_study_results.py` with `--since-date 2026-09-09`. The command does not load the registered Phase 2 Part 2 CSV.

The live study bucket is read-only: `s3://jspsych-mirror-view-2026-09-09/data/prolific/`. Derived files go to bucket `mirrorview-experimental-artifacts` under prefix `experiments/reasoning_during_moderation_2026_09_15/`.

A post needs at least four unique raters after one rating per worker and post. Worker-post pairs with both keep and remove are dropped.

The three groups are:

- `split`, only for vote patterns 2 keep and 2 remove, 3 keep and 2 remove, or 2 keep and 3 remove
- `unanimous_keep`
- `unanimous_remove`

Other disagreements stay out.

Post 1 and Post 2 order is shuffled per post with seed 0, stored on the cohort, and reused by both models and both prompt arms.

On the 2026-09-15 snapshot the counts are `csv_files=3075`, `split=2200`, `unanimous_keep=2256`, `unanimous_remove=208`, and `eligible_posts=4664`. A later export may print larger counts. The command fails if any group is empty, or if `csv_files` is less than 3075.

## Commands

```bash
export AWS_ACCESS_KEY_ID="$LAB_AWS_ACCESS_KEY_ID"
export AWS_SECRET_ACCESS_KEY="$LAB_AWS_ACCESS_KEY_SECRET"

PYTHONPATH=. uv run python experiments/reasoning_during_moderation_2026_09_15/shared/cohort.py --write-counts
```

```bash
PYTHONPATH=. uv run pytest experiments/reasoning_during_moderation_2026_09_15/shared/tests -q
```
