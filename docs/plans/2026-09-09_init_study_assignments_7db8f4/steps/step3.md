# Step 3: Point this repo's web app at the new run

## Scope

- **Caller:** hardcoded study files listed below, copied from a new job YAML
- **Task:** Add `/Users/mark/src/work/mirrorView-task/jobs/config/mirrorview_2026_09_09.yaml` and copy its values into the files the browser, assignment-lookup Lambda, upload script, and export script still read. Deploy new assignment-lookup Lambda code without an infra apply that would reset save-data.
- **Out of scope:** Bucket creation (Step 2), converting feeds (Step 1), uploading the batch and site (Step 4), assignment-service IAM (issue 17).

## Files to inspect (read-only)

| Path | Why |
|------|-----|
| `/Users/mark/src/work/mirrorView-task/docs/runbooks/SETTING_UP_A_NEW_DATA_COLLECTION_RUN.md` | Config to file mapping |
| `/Users/mark/src/work/mirrorView-task/jobs/config/mirrorview_scaled_2026_06_18.yaml` | Template |
| `/Users/mark/src/work/mirrorView-task/webapp/public/config.js` | Study id, iteration, API URLs, Prolific completion |
| `/Users/mark/src/work/mirrorView-task/webapp/public/main.js` | `STUDY_SPEC` |
| `/Users/mark/src/work/mirrorView-task/webapp/lambdas/lambda-get-post-assignments.mjs` | `SCALED_ITERATION_PREFIX`, `SCALED_BATCH_URI`, `resolveAssignmentBatchUri` |
| `/Users/mark/src/work/mirrorView-task/webapp/scripts/upload_to_s3/constants.py` | `TARGET_BUCKET`, catalog key allowlist |
| `/Users/mark/src/work/mirrorView-task/scripts/export_study_results.py` | `BUCKET_NAME` |
| `/Users/mark/src/work/mirrorView-task/docs/runbooks/MANUAL_TESTING.md` | Example website URL |

## Files allowed to change

- `/Users/mark/src/work/mirrorView-task/jobs/config/mirrorview_2026_09_09.yaml` (new)
- `/Users/mark/src/work/mirrorView-task/webapp/public/config.js`
- `/Users/mark/src/work/mirrorView-task/webapp/public/main.js` (`STUDY_SPEC` and the YAML comment only)
- `/Users/mark/src/work/mirrorView-task/webapp/lambdas/lambda-get-post-assignments.mjs`
- `/Users/mark/src/work/mirrorView-task/webapp/lambdas/lambda-save-jspsych-data.mjs` (fallback `BUCKET_NAME` only)
- `/Users/mark/src/work/mirrorView-task/webapp/scripts/upload_to_s3/constants.py`
- `/Users/mark/src/work/mirrorView-task/scripts/export_study_results.py`
- `/Users/mark/src/work/mirrorView-task/docs/runbooks/MANUAL_TESTING.md`
- `/Users/mark/src/work/mirrorView-task/docs/runbooks/SETTING_UP_A_NEW_DATA_COLLECTION_RUN.md` (add this job to the reference table; do not rewrite the runbook)

## Files forbidden to change

- `/Users/mark/src/work/mirrorView-task/webapp/infra/main.tf`
- `/Users/mark/src/work/mirrorView-task/jobs/terraform/mirrorview_scaled_2026_06_18.tfvars`
- `/Users/mark/src/work/mirrorView-task/webapp/public/pre_surveys.js`
- `/Users/mark/Documents/work/study_participant_assignment_interface/**`

## Job YAML values

`/Users/mark/src/work/mirrorView-task/jobs/config/mirrorview_2026_09_09.yaml` must set:

- `aws.region`: `us-east-2`
- `aws.s3_bucket`: `jspsych-mirror-view-2026-09-09`
- `aws.api.post_assignments_url` and `aws.api.save_data_url`: keep the June URLs from `mirrorview_scaled_2026_06_18.yaml` (`https://bgdxga8s91.execute-api.us-east-2.amazonaws.com/prod/get-post-assignments` and `.../save-jspsych-data`) unless Step 2 printed different live API endpoints
- `aws.lambda.assignment_lambda_name`: `get_study_assignment`
- `study.id`: `mirrorview`
- `study.iteration_id`: `mirrorview_2026_09_09`
- `study.experiment_version`: `mirrorview_2026_09_09`
- `study.test_iteration_prefix`: `dev-`
- `design.conditions`: `training_assisted` only
- `design.condition_phase_modes.training_assisted.phase_1`: `linked_fate`
- `design.trials_per_phase`: 20, `num_phases`: 1, `num_trials`: 20, `posts_per_participant`: 20
- `stimuli.post_catalog_path`: `img/flips_2026_09_09.csv`
- `stimuli.post_id_field`: `post_primary_key`
- `stimuli.mirror_text_field`: `mirrored_text`
- `assignment.precomputed_assignments_prefix`: `precomputed_assignments/`
- `assignment.batch_uri`: leave a placeholder `s3://jspsych-mirror-view-2026-09-09/precomputed_assignments/TIMESTAMP` and replace `TIMESTAMP` in Step 4 after upload

Prolific completion code and link stay `CE5XLP3L` unless the operator supplies a new code before this step starts. If they do, put the new code in the YAML and copy it into `config.js`.

## Hardcoded copies

| File | Set |
|------|-----|
| `webapp/public/config.js` | `STUDY_ID` `mirrorview`, `STUDY_ITERATION_ID` `mirrorview_2026_09_09`, API URLs from the YAML, comment points at `jobs/config/mirrorview_2026_09_09.yaml` |
| `webapp/public/main.js` | `STUDY_SPEC.experimentVersion` `mirrorview_2026_09_09`, `postCatalogPath` `img/flips_2026_09_09.csv`, conditions and trial counts unchanged from June |
| `webapp/lambdas/lambda-get-post-assignments.mjs` | Replace `SCALED_ITERATION_PREFIX` with `mirrorview_2026_09_09`. Replace `SCALED_BATCH_URI` with the YAML `assignment.batch_uri` once Step 4 has a timestamp, or with a clearly named constant that Step 4 updates. `resolveAssignmentBatchUri` must return the September URI when the iteration id is `mirrorview_2026_09_09` or `dev-mirrorview_2026_09_09`. June and April URIs may remain as fallbacks for old iteration ids. |
| `webapp/lambdas/lambda-save-jspsych-data.mjs` | Fallback `BUCKET_NAME` `jspsych-mirror-view-2026-09-09` |
| `webapp/scripts/upload_to_s3/constants.py` | `TARGET_BUCKET` `jspsych-mirror-view-2026-09-09`. Replace `img/flips_scaled_2026_06_18.csv` with `img/flips_2026_09_09.csv` in `CRITICAL_S3_KEYS` and `ALLOWED_UPLOAD_KEYS` |
| `scripts/export_study_results.py` | `BUCKET_NAME` `jspsych-mirror-view-2026-09-09` |

Copy Step 1 `catalog.csv` to `/Users/mark/src/work/mirrorView-task/webapp/public/img/flips_2026_09_09.csv` so the upload allowlist has a local file. Gitignore that CSV if it is large, the same way the June catalog was handled.

## Deploy assignment-lookup code without resetting save-data

Do not run `terraform apply` in `/Users/mark/src/work/mirrorView-task/webapp/infra`. Zip `lambda-get-post-assignments.mjs` as `index.mjs` and update the function:

```bash
export AWS_ACCESS_KEY_ID="$LAB_AWS_ACCESS_KEY_ID"
export AWS_SECRET_ACCESS_KEY="$LAB_AWS_ACCESS_KEY_SECRET"

python - <<'PY'
from pathlib import Path
import zipfile
src = Path("webapp/lambdas/lambda-get-post-assignments.mjs")
out = Path("webapp/infra/get-post-assignments.zip")
with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as zf:
    zf.write(src, "index.mjs")
print(out)
PY

aws lambda update-function-code \
  --function-name jspsych-scroll-get-post-assignments \
  --zip-file fileb://webapp/infra/get-post-assignments.zip \
  --region us-east-2
```

Expected: the command prints a new `CodeSha256`.

Confirm save-data still points at September:

```bash
aws lambda get-function-configuration \
  --function-name jspsych-scroll-save-data \
  --region us-east-2 \
  --query 'Environment.Variables.BUCKET_NAME' \
  --output text
```

Expected: `jspsych-mirror-view-2026-09-09`. If it prints `jspsych-mirror-view-4`, Step 2 was overwritten. Re-run the Step 2 script before continuing.

## Checks that must pass

```bash
rg -n "jspsych-mirror-view-2026-09-09" webapp/public/config.js webapp/lambdas/lambda-save-jspsych-data.mjs webapp/scripts/upload_to_s3/constants.py scripts/export_study_results.py
rg -n "mirrorview_2026_09_09" webapp/public/config.js webapp/public/main.js webapp/lambdas/lambda-get-post-assignments.mjs jobs/config/mirrorview_2026_09_09.yaml
rg -n "img/flips_2026_09_09.csv" webapp/public/main.js webapp/scripts/upload_to_s3/constants.py
test -f webapp/public/img/flips_2026_09_09.csv
```

Expected: each `rg` prints at least one match in each listed file, and the catalog file exists.

```bash
rg -n "TARGET_BUCKET = \"jspsych-mirror-view-4\"" webapp/scripts/upload_to_s3/constants.py
```

Expected: no matches.

## Fail

The step fails if `webapp/infra/main.tf` `bucket_name` default changes, if you run `terraform apply` for this step, or if `STUDY_ITERATION_ID` stays `mirrorview_scaled_2026_06_18`.
