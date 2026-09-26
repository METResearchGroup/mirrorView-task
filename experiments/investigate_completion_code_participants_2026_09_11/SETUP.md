# Setup

This lookup uses live September 2026 study records. It does not need a local copy of the jsPsych CSVs.

## Inputs

- DynamoDB table `user_assignments` in `us-east-2`. Partition key `study_id` `mirrorview`. Sort key `iteration_user_key` `{study_iteration_id}#{prolific_id}`.
- Session CSVs under `s3://jspsych-mirror-view-2026-09-09/data/prolific/` and `data/test/`.
- Precomputed assignment rows named in the DynamoDB payload `s3_key` (Democrat `training_assisted` for both people in the original request).

Out of scope: Prolific dashboard state, environment install, and changing the study UI.

## Credentials

```bash
export AWS_ACCESS_KEY_ID="$LAB_AWS_ACCESS_KEY_ID"
export AWS_SECRET_ACCESS_KEY="$LAB_AWS_ACCESS_KEY_SECRET"
```

## Run

```bash
PYTHONPATH=. uv run pytest experiments/investigate_completion_code_participants_2026_09_11/tests -q

PYTHONPATH=. uv run python experiments/investigate_completion_code_participants_2026_09_11/run.py
```

Pass `--prolific-id` more than once to look up other ids.
