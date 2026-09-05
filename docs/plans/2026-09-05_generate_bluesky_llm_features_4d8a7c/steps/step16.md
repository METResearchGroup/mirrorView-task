# Step 16: Expire intermediate data platform S3 batches after 30 days

## Goal

Add an S3 bucket lifecycle rule on `mirrorview-experimental-artifacts` that expires only intermediate batches: objects under the `data_platform/data/` prefix that carry the object tag `intermediate-artifact=true`. Final Parquet feature files, hash manifests, progress records, and permanent run reports must not match the rule and must remain until deleted by other processes.

## Dependencies

- **Step 5 merged (only technical prerequisite):** feature batch writes apply `Tagging` `intermediate-artifact=true` on `batches/part-*.parquet` objects only. The lifecycle rule is inert for correctly tagged batches until Step 5 lands.
- See `docs/plans/2026-09-05_generate_bluesky_llm_features_4d8a7c/campaign_contract.md` for tagging rules.

Step 16 is listed last in the epic schedule. It does not depend on Steps 8 through 15. No IAM policy changes and no bucket versioning changes in this step.

## Main caller and implementation slice

**Main caller:** `data_platform/infra/apply_data_platform_s3_lifecycle.py` `main`.

**Implementation slice for this PR:** commit a version-controlled lifecycle configuration JSON and a small Python script that calls `put_bucket_lifecycle_configuration` to install one rule with AND filter (prefix + tag), 30-day expiration, and no effect on untagged or final artifacts.

## Files to inspect (read-only)

| Path | Why |
|------|-----|
| `/workspace/docs/plans/2026-09-05_generate_bluesky_llm_features_4d8a7c/plan.md` | Locked prefix, tag, and retention intent |
| `/workspace/data_platform/data/bluesky/bluesky_7e2c4a91-3b5f-4d8e-a6c1-0f9b8d2e5a73/s3_migration_inventory.json` | Example long-lived objects without the intermediate tag |
| `/workspace/lib/aws/s3.py` | Region default `us-east-2` |
| `/workspace/experiments/finetune_qwen_model_2026_08_08/infra/main.tf` | Prior lab use of `mirrorview-experimental-artifacts` (read only; do not edit) |
| `/workspace/AGENTS.md` | AWS credential export pattern |

## Files allowed to change

- `/workspace/data_platform/infra/data_platform_s3_lifecycle.json` (new, permanent config)
- `/workspace/data_platform/infra/apply_data_platform_s3_lifecycle.py` (new)
- `/workspace/data_platform/infra/verify_data_platform_s3_lifecycle.py` (new, read-only verifier)

Temporary smoke objects under `data_platform/data/bluesky/_lifecycle_smoke_2026_09_05/` may be uploaded and committed as manifest-only evidence for review; delete smoke objects from S3 and remove the manifest from git before merge.

Do not edit plan package files during implementation.

## Files forbidden to change

- `/workspace/data_platform/utils/storage.py`
- `/workspace/data_platform/utils/object_store.py`
- `/workspace/data_platform/generate_features/**` (tagging is Step 5)
- `/workspace/lib/aws/s3.py` unless a one-line helper is absolutely required; prefer boto3 calls inside the infra script
- Any IAM policy, role, or Terraform file
- Bucket versioning settings
- `/workspace/data_platform/data/bluesky/bluesky_7e2c4a91-3b5f-4d8e-a6c1-0f9b8d2e5a73/s3_migration_inventory.json`
- `/workspace/CHANGELOG.md`
- Any file under `/workspace/tests/`
- Any file outside the allowed list

## Locked contracts

| Item | Value |
|------|-------|
| Bucket | `mirrorview-experimental-artifacts` |
| Region | `us-east-2` |
| Rule id | `expire-data-platform-intermediate-artifacts` |
| Prefix filter | `data_platform/data/` |
| Tag filter | Key `intermediate-artifact`, value `true` |
| Filter composition | AWS lifecycle AND of prefix and tag (both required) |
| Expiration | 30 days after object creation |
| Non-expiring objects | Final feature parquet, hash manifests, progress JSON, permanent run reports, pinned preprocessed input, and any object without the tag |
| Tag application | Only Step 5 batch writes under `batches/` set `intermediate-artifact=true`; this step does not retroactively tag objects |
| IAM | No new policies or role changes |
| Versioning | No enable/disable/versioning configuration changes |
| Config file | `data_platform/infra/data_platform_s3_lifecycle.json` documents the rule verbatim for review |
| Apply script idempotency | Re-running apply replaces the named rule without duplicating rules |

`data_platform_s3_lifecycle.json` must contain exactly one rule matching:

```json
{
  "Rules": [
    {
      "ID": "expire-data-platform-intermediate-artifacts",
      "Status": "Enabled",
      "Filter": {
        "And": {
          "Prefix": "data_platform/data/",
          "Tags": [
            {
              "Key": "intermediate-artifact",
              "Value": "true"
            }
          ]
        }
      },
      "Expiration": {
        "Days": 30
      }
    }
  ]
}
```

## Ordered implementation work

1. Add the lifecycle JSON with the locked rule shape.
2. Add `apply_data_platform_s3_lifecycle.py` that loads the JSON, merges or replaces the rule by `ID`, and calls `put_bucket_lifecycle_configuration`.
3. Add `verify_data_platform_s3_lifecycle.py` that calls `get_bucket_lifecycle_configuration` and asserts the rule id, prefix, tag, and 30-day expiration.
4. Export AWS credentials and apply the rule in the lab bucket.
5. Upload one temporary tagged smoke object under `data_platform/data/bluesky/_lifecycle_smoke_2026_09_05/tagged_batch.parquet` with `intermediate-artifact=true` and confirm lifecycle configuration lists the rule (do not wait 30 days).
6. Upload one untagged smoke object beside it and confirm the rule filter would not target it (manual reasoning plus tag listing).
7. Delete smoke S3 objects and any temporary manifest before merge.

## Live smoke and basic check commands

Export AWS credentials:

```bash
export AWS_ACCESS_KEY_ID="$LAB_AWS_ACCESS_KEY_ID"
export AWS_SECRET_ACCESS_KEY="$LAB_AWS_ACCESS_KEY_SECRET"
aws sts get-caller-identity --region us-east-2
```

Expected: exit code 0 with caller ARN JSON.

Apply lifecycle configuration:

```bash
PYTHONPATH=. uv run python data_platform/infra/apply_data_platform_s3_lifecycle.py
```

Expected stdout: `applied lifecycle rule expire-data-platform-intermediate-artifacts on mirrorview-experimental-artifacts` and exit code 0.

Verify installed rule:

```bash
PYTHONPATH=. uv run python data_platform/infra/verify_data_platform_s3_lifecycle.py
```

Expected stdout: `OK: rule expire-data-platform-intermediate-artifacts prefix=data_platform/data/ tag=intermediate-artifact=true expiration_days=30` and exit code 0.

Cross-check with AWS CLI:

```bash
aws s3api get-bucket-lifecycle-configuration \
  --bucket mirrorview-experimental-artifacts \
  --region us-east-2 \
  --query 'Rules[?ID==`expire-data-platform-intermediate-artifacts`]' \
  --output json
```

Expected JSON array with one element whose `Filter.And.Prefix` is `data_platform/data/`, whose `Filter.And.Tags` contains `Key=intermediate-artifact,Value=true`, and whose `Expiration.Days` is `30`.

**Tagged smoke object** (delete after verification):

```bash
echo 'smoke' > /tmp/lifecycle_smoke.parquet
aws s3api put-object \
  --bucket mirrorview-experimental-artifacts \
  --key data_platform/data/bluesky/_lifecycle_smoke_2026_09_05/tagged_batch.parquet \
  --body /tmp/lifecycle_smoke.parquet \
  --tagging "TagSet=[{Key=intermediate-artifact,Value=true}]" \
  --region us-east-2

aws s3api get-object-tagging \
  --bucket mirrorview-experimental-artifacts \
  --key data_platform/data/bluesky/_lifecycle_smoke_2026_09_05/tagged_batch.parquet \
  --region us-east-2
```

Expected tagging output includes `intermediate-artifact` = `true`.

**Untagged control object** (delete after verification):

```bash
aws s3api put-object \
  --bucket mirrorview-experimental-artifacts \
  --key data_platform/data/bluesky/_lifecycle_smoke_2026_09_05/final_feature.parquet \
  --body /tmp/lifecycle_smoke.parquet \
  --region us-east-2

aws s3api get-object-tagging \
  --bucket mirrorview-experimental-artifacts \
  --key data_platform/data/bluesky/_lifecycle_smoke_2026_09_05/final_feature.parquet \
  --region us-east-2
```

Expected: empty `TagSet` or no `intermediate-artifact` tag.

Clean up smoke objects:

```bash
aws s3 rm s3://mirrorview-experimental-artifacts/data_platform/data/bluesky/_lifecycle_smoke_2026_09_05/ --recursive --region us-east-2
```

Expected: two deleted keys, exit code 0.

Confirm pinned inventory object is not tagged as intermediate:

```bash
aws s3api get-object-tagging \
  --bucket mirrorview-experimental-artifacts \
  --key data_platform/data/bluesky/bluesky_7e2c4a91-3b5f-4d8e-a6c1-0f9b8d2e5a73/preprocessed/2026_09_03-23:51:30/posts.parquet \
  --region us-east-2
```

Expected: no `intermediate-artifact=true` tag (empty tag set is fine).

## Acceptance criteria

- Lifecycle rule `expire-data-platform-intermediate-artifacts` is enabled on `mirrorview-experimental-artifacts`.
- Rule uses AND of prefix `data_platform/data/` and tag `intermediate-artifact=true`.
- Expiration is 30 days.
- Apply and verify scripts are committed under `data_platform/infra/`.
- Smoke demonstrates tagged vs untagged objects under the prefix.
- No IAM or versioning changes.
- Pinned preprocessed input and migration inventory objects are not tagged as intermediate.

## Failure conditions

- Rule expires all objects under `data_platform/data/` without requiring the tag.
- Rule targets a different prefix (for example `data_platform/` only or a duplicated `data_platform/data_platform/`).
- Expiration is not 30 days.
- IAM policies or bucket versioning are modified.
- Feature final artifacts or manifests are tagged `intermediate-artifact=true` in this PR (tagging belongs to Step 5).
- Automated tests are added or run.

## PR artifact and commit rules

- One independently mergeable PR, intended to merge after Step 5 tagging is live even though it is numbered last in the plan.
- Commit JSON config and scripts together; apply output may be noted in PR description but need not commit secrets.
- Temporary smoke paths under `data_platform/data/bluesky/_lifecycle_smoke_2026_09_05/` must be removed from S3 and not remain in git after merge.
- Do not add pytest files or run pytest.
- Do not edit `plan.md` or other step specs.
- PR title suggestion: `Add 30-day S3 lifecycle for tagged data platform intermediate batches`.
