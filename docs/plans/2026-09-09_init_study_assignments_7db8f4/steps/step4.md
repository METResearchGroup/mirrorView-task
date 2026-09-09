# Step 4: Upload the batch, upload the site, and complete one manual run per party

## Scope

- **Caller:** upload of `/Users/mark/src/work/mirrorView-task/experiments/load_study_assignments_2026_09_09/batch/` plus `/Users/mark/src/work/mirrorView-task/webapp/scripts/upload_to_s3/run_upload.sh`
- **Task:** Put `config.yaml` and the two party CSVs under `s3://jspsych-mirror-view-2026-09-09/precomputed_assignments/<timestamp>/`, upload the web app and catalog, then complete one Democrat test run and one Republican test run.
- **Out of scope:** Feed conversion (Step 1), bucket creation (Step 2), hardcoded copies except filling the batch timestamp into `lambda-get-post-assignments.mjs` and the job YAML.

## Files to inspect (read-only)

| Path | Why |
|------|-----|
| `/Users/mark/Documents/work/study_participant_assignment_interface/jobs/mirrorview/upload_precomputed_data_to_s3.py` | S3 key layout this upload must match |
| `/Users/mark/Documents/work/study_participant_assignment_interface/lambdas/get_study_assignment/handler.py` | Request fields and how the Lambda loads `config.yaml` |
| `/Users/mark/src/work/mirrorView-task/docs/runbooks/MANUAL_TESTING.md` | Manual run checklist |
| `/Users/mark/src/work/mirrorView-task/docs/runbooks/SETTING_UP_A_NEW_DATA_COLLECTION_RUN.md` | Step 9 verification |
| `https://github.com/METResearchGroup/study_participant_assignment_interface/issues/17` | Must be applied before the assignment Lambda can read the new bucket |

## Files allowed to change

- `/Users/mark/src/work/mirrorView-task/jobs/config/mirrorview_2026_09_09.yaml` (`assignment.batch_uri` timestamp only)
- `/Users/mark/src/work/mirrorView-task/webapp/lambdas/lambda-get-post-assignments.mjs` (September batch URI timestamp only, then re-zip and `update-function-code` as in Step 3)
- `/Users/mark/src/work/mirrorView-task/experiments/load_study_assignments_2026_09_09/RESULTS.md` (new)
- `/Users/mark/src/work/mirrorView-task/CHANGELOG.md` (one line after a successful manual save)

## Files forbidden to change

- `/Users/mark/src/work/mirrorView-task/webapp/infra/main.tf`
- `/Users/mark/src/work/mirrorView-task/experiments/generate_study_user_assignments_2026_09_08/**`
- `/Users/mark/Documents/work/study_participant_assignment_interface/**`

## Blocker

Issue 17 must show the assignment Lambda role can `s3:GetObject` on `arn:aws:s3:::jspsych-mirror-view-2026-09-09/*` before any participant assignment call. If that grant is missing, the browser fails after consent.

```bash
aws iam get-role-policy \
  --role-name get_study_assignment-lambda \
  --policy-name dynamodb-s3-logs \
  --query 'PolicyDocument.Statement[?Sid==`S3GetObject`].Resource' \
  --output text
```

Expected: the printed ARNs include `arn:aws:s3:::jspsych-mirror-view-2026-09-09/*`.

## Upload the assignment batch

Use timestamp format matching `/Users/mark/src/work/mirrorView-task/lib/timestamp_utils.py` (`YYYY_MM_DD-HH:MM:SS`). Call that helper. Do not invent a different layout.

Upload from Step 1 output:

```text
s3://jspsych-mirror-view-2026-09-09/precomputed_assignments/<timestamp>/config.yaml
s3://jspsych-mirror-view-2026-09-09/precomputed_assignments/<timestamp>/democrat/training_assisted/assignments.csv
s3://jspsych-mirror-view-2026-09-09/precomputed_assignments/<timestamp>/republican/training_assisted/assignments.csv
```

`config.yaml` `s3.bucket` must be `jspsych-mirror-view-2026-09-09` and `s3.prefix` must be `precomputed_assignments`. The Lambda rejects a batch URI whose bucket or prefix disagrees with that file.

Write a small uploader in `/Users/mark/src/work/mirrorView-task/experiments/load_study_assignments_2026_09_09/upload.py` if Step 1 did not already include one. Do not add that module to the assignment-service repo.

```bash
export AWS_ACCESS_KEY_ID="$LAB_AWS_ACCESS_KEY_ID"
export AWS_SECRET_ACCESS_KEY="$LAB_AWS_ACCESS_KEY_SECRET"
PYTHONPATH=. uv run python experiments/load_study_assignments_2026_09_09/upload.py
```

Expected stdout includes the three keys and `batch_uri=s3://jspsych-mirror-view-2026-09-09/precomputed_assignments/<timestamp>`.

```bash
aws s3api head-object --bucket jspsych-mirror-view-2026-09-09 \
  --key precomputed_assignments/<timestamp>/config.yaml --region us-east-2
aws s3api head-object --bucket jspsych-mirror-view-2026-09-09 \
  --key precomputed_assignments/<timestamp>/democrat/training_assisted/assignments.csv --region us-east-2
aws s3api head-object --bucket jspsych-mirror-view-2026-09-09 \
  --key precomputed_assignments/<timestamp>/republican/training_assisted/assignments.csv --region us-east-2
```

Expected: all three succeed.

Put that `batch_uri` into `jobs/config/mirrorview_2026_09_09.yaml` and into `lambda-get-post-assignments.mjs`, then repeat the Step 3 zip and `update-function-code` for `jspsych-scroll-get-post-assignments`.

## Upload the site

```bash
bash webapp/scripts/upload_to_s3/run_upload.sh
```

Expected: verification in that script exits 0, and `img/flips_2026_09_09.csv` is among the uploaded keys.

```bash
aws s3api head-object --bucket jspsych-mirror-view-2026-09-09 \
  --key img/flips_2026_09_09.csv --region us-east-2
aws s3api head-object --bucket jspsych-mirror-view-2026-09-09 \
  --key config.js --region us-east-2
```

Expected: both succeed.

## Manual runs

Website:

```text
http://jspsych-mirror-view-2026-09-09.s3-website.us-east-2.amazonaws.com/?PROLIFIC_PID=manual-test-2026-09-09-d
```

Complete consent and pre-surveys as Democrat. Confirm 20 trials load with mirror text. Finish through post-surveys.

Repeat with `PROLIFIC_PID=manual-test-2026-09-09-r` as Republican.

`webapp/public/main.js` sets `isTestParticipant` only when the Prolific id is missing. `lambda-save-jspsych-data.mjs` treats ids that start with `UNKNOWN_` or `TEST_` as test. `manual-test-` matches neither rule, so these two runs write under `data/prolific/` and use study iteration `mirrorview_2026_09_09` in DynamoDB. They consume production assignment rows.

```bash
aws s3 ls s3://jspsych-mirror-view-2026-09-09/data/prolific/ --region us-east-2 | tail
```

Expected: two new objects after the two runs.

Spot-check DynamoDB in `us-east-2` table `user_assignments`:

- `study_id` `mirrorview`
- `iteration_user_key` `mirrorview_2026_09_09#manual-test-2026-09-09-d` and `mirrorview_2026_09_09#manual-test-2026-09-09-r`

Record the saved S3 keys in `RESULTS.md`.

CLI smoke that does not consume a production row, after issue 17:

```bash
aws lambda invoke \
  --function-name get_study_assignment \
  --region us-east-2 \
  --cli-binary-format raw-in-base64-out \
  --payload '{"study_id":"mirrorview","study_iteration_id":"dev-mirrorview_2026_09_09","prolific_id":"manual-cli-2026-09-09-d","political_party":"democrat","assignment_batch_uri":"s3://jspsych-mirror-view-2026-09-09/precomputed_assignments/<timestamp>"}' \
  /tmp/assign-d.json && cat /tmp/assign-d.json
```

Expected: JSON with `assigned_post_ids` length 20 and `condition` `training_assisted`. A second call with the same `prolific_id` and the same `study_iteration_id` returns the same ids.

## RESULTS.md

Write `/Users/mark/src/work/mirrorView-task/experiments/load_study_assignments_2026_09_09/RESULTS.md` with the batch URI, catalog SHA-256, Democrat and Republican row counts, the two manual Prolific ids, and the S3 keys of the saved CSVs.

## Fail

The step fails if assignment files land in `jspsych-mirror-view-4`, if you treat AccessDenied from `get_study_assignment` as success before issue 17 is applied, if you skip the Republican manual run, or if you apply this repo's Terraform.
