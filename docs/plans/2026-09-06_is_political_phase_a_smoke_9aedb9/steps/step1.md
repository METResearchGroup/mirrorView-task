# Step 1: Confirm the prefix is empty and run the smoke once

## Goal

Run the ten-post smoke for `is_political` exactly once against the canonical campaign prefix. The smoke may run only once per feature, so the run is gated on an empty prefix.

## Pinned values

| Field | Value |
|-------|-------|
| Campaign id | `bluesky_2026_09_03_235130_llm_features_v1` |
| Dataset id | `bluesky_7e2c4a91-3b5f-4d8e-a6c1-0f9b8d2e5a73` |
| Preprocessed run | `2026_09_03-23:51:30` |
| Feature | `is_political` |
| Label field | `is_political` (boolean `true` or `false`) |
| Feature prefix | `s3://mirrorview-experimental-artifacts/data_platform/data/bluesky/bluesky_7e2c4a91-3b5f-4d8e-a6c1-0f9b8d2e5a73/features/bluesky_2026_09_03_235130_llm_features_v1/is_political/` |
| Region | `us-east-2` |

## Files to inspect (read-only)

- `docs/plans/2026-09-05_generate_bluesky_llm_features_4d8a7c/steps/step9.md`
- `data_platform/generate_features/smoke_bluesky_campaign.py`

## Files allowed to change

None in this step. The smoke caller itself writes the Git copies under `docs/plans/2026-09-05_generate_bluesky_llm_features_4d8a7c/reports/smoke/is_political/`.

## Files forbidden to change

Everything under `data_platform/`, `lib/`, `ml_tooling/`, `tests/`, `pyproject.toml`, `CHANGELOG.md`, and every file in `docs/plans/2026-09-05_generate_bluesky_llm_features_4d8a7c/` other than the smoke report folder. Nothing under the S3 prefixes of the other six features, including `is_news_or_opinion/`.

## Commands

Export the credentials first. The `aws` CLI is not installed, so listings use boto3.

```bash
export AWS_ACCESS_KEY_ID="$LAB_AWS_ACCESS_KEY_ID"
export AWS_SECRET_ACCESS_KEY="$LAB_AWS_ACCESS_KEY_SECRET"
export AWS_DEFAULT_REGION=us-east-2
```

### List the prefix before the smoke

```bash
PYTHONPATH=. uv run python - <<'PY'
import boto3
BUCKET = "mirrorview-experimental-artifacts"
PREFIX = ("data_platform/data/bluesky/bluesky_7e2c4a91-3b5f-4d8e-a6c1-0f9b8d2e5a73/features/"
          "bluesky_2026_09_03_235130_llm_features_v1/is_political/")
s3 = boto3.client("s3", region_name="us-east-2")
objects = []
for page in s3.get_paginator("list_objects_v2").paginate(Bucket=BUCKET, Prefix=PREFIX):
    objects.extend(page.get("Contents", []))
print(f"object_count={len(objects)}")
for obj in sorted(objects, key=lambda o: o["Key"]):
    tags = s3.get_object_tagging(Bucket=BUCKET, Key=obj["Key"])["TagSet"]
    print(f"  {obj['Key'].removeprefix(PREFIX)} size={obj['Size']} tags={tags}")
PY
```

Expected: `object_count=0`. If the count is not zero, stop and report. Do not run the smoke.

### Run the smoke once

```bash
PYTHONPATH=. uv run python data_platform/generate_features/smoke_bluesky_campaign.py \
  --campaign-id bluesky_2026_09_03_235130_llm_features_v1 \
  --dataset-id bluesky_7e2c4a91-3b5f-4d8e-a6c1-0f9b8d2e5a73 \
  --preprocessed-run 2026_09_03-23:51:30 \
  --feature is_political \
  --output-dir docs/plans/2026-09-05_generate_bluesky_llm_features_4d8a7c/reports/smoke/is_political
```

Expected stdout, in order, with exit code 0:

```text
smoke_prefix=s3://mirrorview-experimental-artifacts/.../is_political/smoke/
smoke_rows=10
avg_input_tokens=<number>
max_input_tokens=<number>
avg_output_tokens=<number>
max_output_tokens=<number>
estimated_full_run_usd_avg=<number>
estimated_full_run_usd_max=<number>
s3_smoke_output_ok=true
s3_smoke_resume_evidence_ok=true
no_batches_prefix_objects=true
canonical_smoke_prefix_touched=true
cost_report=docs/plans/2026-09-05_generate_bluesky_llm_features_4d8a7c/reports/smoke/is_political/is_political_cost_report.json
```

The caller makes one upload and one batch creation, saves the polling state, discards that client, and lets a fresh engine reattach to the same provider batch. Do not pass `--smoke-prefix`. Run the command once. If it fails midway, do not rerun. List the prefix again and report the state.

## Must pass

- The listing before the smoke prints `object_count=0`.
- The smoke exits 0 and prints the four `true` check lines.

## Must fail

- Any second smoke run for this feature. The caller writes the four objects with `If-None-Match: *`, so a second run fails with `FileExistsError`, but only after it has already submitted and paid for another provider job. The empty listing before the run is the gate that prevents the second job. Do not rely on the write-time refusal.
