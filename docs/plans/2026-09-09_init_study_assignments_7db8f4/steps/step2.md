# Step 2: Create the new study bucket and point save-data at it

## Scope

- **Caller:** `/Users/mark/src/work/mirrorView-task/scripts/provision_jspsych_mirror_view_2026_09_09.py` `main`
- **Task:** Create S3 bucket `jspsych-mirror-view-2026-09-09` in `us-east-2` if it does not exist, enable static website hosting and public read for the site, and point the save-data Lambda at that bucket. Leave `jspsych-mirror-view-4` in Terraform state.
- **Out of scope:** Assignment Lambda IAM ([issue 17](https://github.com/METResearchGroup/study_participant_assignment_interface/issues/17)), converting feeds (Step 1), web app hardcoded copies (Step 3), uploading assignment files (Step 4), `terraform apply` in this repo.

## Files to inspect (read-only)

| Path | Why |
|------|-----|
| `/Users/mark/src/work/mirrorView-task/webapp/infra/main.tf` | Current `aws_s3_bucket.site` is `jspsych-mirror-view-4`. Website config, public access block, public GetObject policy, save-data `s3:PutObject` on `data/*`, save-data env `BUCKET_NAME` |
| `/Users/mark/src/work/mirrorView-task/webapp/lambdas/lambda-save-jspsych-data.mjs` | Fallback `BUCKET_NAME` when env is unset |
| `/Users/mark/src/work/mirrorView-task/docs/bugs/fail_save_s3_2026_06_18.md` | Save-data env and IAM must match the bucket the code writes to |
| `/Users/mark/src/work/mirrorView-task/docs/runbooks/AWS_DEPLOYMENT_GUIDE.md` | Website hosting and public read pattern |
| `https://github.com/METResearchGroup/study_participant_assignment_interface/issues/17` | Assignment Lambda read grant is a separate apply in the other repo |

## Files allowed to change

- `/Users/mark/src/work/mirrorView-task/scripts/provision_jspsych_mirror_view_2026_09_09.py` (new)
- `/Users/mark/src/work/mirrorView-task/scripts/provision_jspsych_mirror_view_2026_09_09.md` (new operator notes)

## Files forbidden to change

- `/Users/mark/src/work/mirrorView-task/webapp/infra/main.tf`
- `/Users/mark/src/work/mirrorView-task/jobs/terraform/mirrorview_scaled_2026_06_18.tfvars`
- `/Users/mark/Documents/work/study_participant_assignment_interface/infra/**` (issue 17 owns that change)
- `/Users/mark/src/work/mirrorView-task/experiments/load_study_assignments_2026_09_09/**` except if Step 1 already wrote them

## Why not Terraform in this repo

`webapp/infra/main.tf` has one `aws_s3_bucket.site` whose name is `var.bucket_name`. Applying with `bucket_name = "jspsych-mirror-view-2026-09-09"` would try to replace `jspsych-mirror-view-4`. Keep June in state. Create September with the AWS API.

## Script contract

Constants at module top:

- `AWS_REGION` = `us-east-2`
- `BUCKET_NAME` = `jspsych-mirror-view-2026-09-09`
- `SAVE_DATA_FUNCTION` = `jspsych-scroll-save-data`
- `SAVE_DATA_ROLE_NAME` = `jspsych-scroll-save-data-role`
- `SAVE_DATA_EXTRA_POLICY_NAME` = `jspsych-mirror-view-2026-09-09-put-data`
- `DATA_PREFIX` = `data/*`

The script must:

1. Create the bucket in `us-east-2` if `head-bucket` returns 404. If the bucket already exists, continue.
2. Put website configuration with index document `index.html`, matching `/Users/mark/src/work/mirrorView-task/webapp/infra/main.tf` `aws_s3_bucket_website_configuration.site`.
3. Set public access block `block_public_acls`, `ignore_public_acls`, `block_public_policy`, and `restrict_public_buckets` all to false, matching the June bucket.
4. Put a bucket policy that allows `s3:GetObject` on `arn:aws:s3:::jspsych-mirror-view-2026-09-09/*` for principal `*`.
5. Put an extra inline IAM policy on `jspsych-scroll-save-data-role` named `jspsych-mirror-view-2026-09-09-put-data` that allows `s3:PutObject` on `arn:aws:s3:::jspsych-mirror-view-2026-09-09/data/*`. Do not replace the existing June write policy.
6. Update `jspsych-scroll-save-data` environment so `BUCKET_NAME` is `jspsych-mirror-view-2026-09-09`, and keep `DATA_PREFIX_PROLIFIC` and `DATA_PREFIX_TEST` as they are.

Leave objects in `jspsych-mirror-view-4` untouched. Issue 17 owns IAM on `get_study_assignment-lambda`.

Operator notes in `provision_jspsych_mirror_view_2026_09_09.md` must say:

- After this script, do not run `terraform apply` in `/Users/mark/src/work/mirrorView-task/webapp/infra` with a new `bucket_name`, and do not apply the June tfvars either, because that apply would set save-data `BUCKET_NAME` back to `jspsych-mirror-view-4`.
- Assignment reads still need [issue 17](https://github.com/METResearchGroup/study_participant_assignment_interface/issues/17) applied in the other repo.

## Command that must pass

```bash
export AWS_ACCESS_KEY_ID="$LAB_AWS_ACCESS_KEY_ID"
export AWS_SECRET_ACCESS_KEY="$LAB_AWS_ACCESS_KEY_SECRET"

PYTHONPATH=. uv run python scripts/provision_jspsych_mirror_view_2026_09_09.py
```

Expected: exit 0, and stdout includes `bucket=jspsych-mirror-view-2026-09-09` and `save_data_bucket_name=jspsych-mirror-view-2026-09-09`.

Verify:

```bash
aws s3api head-bucket --bucket jspsych-mirror-view-2026-09-09 --region us-east-2
aws s3api get-bucket-website --bucket jspsych-mirror-view-2026-09-09 --region us-east-2
aws lambda get-function-configuration \
  --function-name jspsych-scroll-save-data \
  --region us-east-2 \
  --query 'Environment.Variables.BUCKET_NAME' \
  --output text
aws iam get-role-policy \
  --role-name jspsych-scroll-save-data-role \
  --policy-name jspsych-mirror-view-2026-09-09-put-data
```

Expected:

- `head-bucket` succeeds.
- Website configuration has `IndexDocument.Suffix` = `index.html`.
- `BUCKET_NAME` prints `jspsych-mirror-view-2026-09-09`.
- The extra policy document includes `arn:aws:s3:::jspsych-mirror-view-2026-09-09/data/*`.

June bucket still exists:

```bash
aws s3api head-bucket --bucket jspsych-mirror-view-4 --region us-east-2
```

Expected: success.

## Fail

The step fails if you run `terraform apply` in `/Users/mark/src/work/mirrorView-task/webapp/infra`, if the script edits `get_study_assignment-lambda` IAM, or if `jspsych-mirror-view-4` is destroyed or emptied.
