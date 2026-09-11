# Upsample mixed study feeds

<-- NOTE TO AI AGENTS: do NOT touch this file. This file is READ-ONLY. If something here is incorrect or needs updating, inform the user and they will make the change themselves -->

A feed is assigned when a participant starts, so dropouts still consume a row. The command adds 1000 extra mixed assignment rows so recruiting about 4000 people does not exhaust the 3879 original rows. It does not add posts to the stimulus catalog. The total is 4879 rows, and 4879 is the agreed total.

Mixed feeds are 10 left and 10 right. Leftover-left feeds are not cloned.

Sampling is 1000 mixed feeds without replacement, seed 0.

The original 3879 rows are copied unchanged. Extra user ids are 3880 through 4879. Odd original ids go to `democrat`. Even original ids go to `republican`. Extra Democrat count is 500. Extra Republican count is 500.

Extras are appended at the end of each party file, so Democrat ids `democrat-training_assisted-0001` through `democrat-training_assisted-1940` keep the original posts.

The live prefix `2026_09_09-23:06:02` is left in place, because returning users still read that prefix from DynamoDB. DynamoDB counters are not reset. The lookup Lambda and job YAML are not changed.

Output columns: `id`, `assigned_post_ids`, `political_party`, `condition`, `created_at`.

Local file and experimental S3 object: `study_user_assignments_overprovisioned.csv`

S3 URI: `s3://mirrorview-experimental-artifacts/experiments/upsample_mixed_study_feeds_2026_09_11/study_user_assignments_overprovisioned.csv`

Required files: `constants.py`, `upsample.py`, `split_batch.py`, `write.py`, `run.py`, and the pytest files under `tests/`.

## Tests

```bash
PYTHONPATH=. uv run pytest experiments/upsample_mixed_study_feeds_2026_09_11/tests -q
```

## Live run

```bash
export AWS_ACCESS_KEY_ID="$LAB_AWS_ACCESS_KEY_ID"
export AWS_SECRET_ACCESS_KEY="$LAB_AWS_ACCESS_KEY_SECRET"

PYTHONPATH=. uv run python experiments/upsample_mixed_study_feeds_2026_09_11/run.py
```
