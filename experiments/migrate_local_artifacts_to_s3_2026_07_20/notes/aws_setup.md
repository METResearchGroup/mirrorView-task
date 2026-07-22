# AWS setup — mirrorview-experimental-artifacts

**Date:** 2026-07-20  
**Bucket:** `mirrorview-experimental-artifacts`  
**Region:** `us-east-2`  
**Purpose:** Durable home for allowlisted experiment `*.csv` / `*.json` (path-preserving keys).

## Create bucket (one-time)

```bash
aws s3api create-bucket \
  --bucket mirrorview-experimental-artifacts \
  --region us-east-2 \
  --create-bucket-configuration LocationConstraint=us-east-2

aws s3api put-public-access-block \
  --bucket mirrorview-experimental-artifacts \
  --public-access-block-configuration \
  BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true

aws s3api put-bucket-encryption \
  --bucket mirrorview-experimental-artifacts \
  --server-side-encryption-configuration \
  '{"Rules":[{"ApplyServerSideEncryptionByDefault":{"SSEAlgorithm":"AES256"}}]}'
```

## Credentials

Operator needs permission to:

- `s3:PutObject`, `s3:GetObject`, `s3:HeadObject`, `s3:ListBucket` on this bucket

Verify:

```bash
aws sts get-caller-identity
aws s3 ls s3://mirrorview-experimental-artifacts/ --region us-east-2
```

## Key convention

```text
s3://mirrorview-experimental-artifacts/{repo-relative-path}
```

Example:

```text
s3://mirrorview-experimental-artifacts/experiments/followup_model_error_analysis_2026_07_15/outputs/run_manifest.json
```

Do **not** share this keyspace with study/release buckets (`scripts/upload_to_s3/`) without an explicit prefix policy.

## Consume path

```bash
aws s3 cp \
  s3://mirrorview-experimental-artifacts/experiments/followup_model_error_analysis_2026_07_15/outputs/run_manifest.json \
  ./run_manifest.json \
  --region us-east-2
```

Or sync a folder prefix:

```bash
aws s3 sync \
  s3://mirrorview-experimental-artifacts/experiments/followup_model_error_analysis_2026_07_15/ \
  ./restore/ \
  --region us-east-2
```
