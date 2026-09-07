# Step 2: Verify the S3 state and commit the temporary artifacts

## Goal

Show that the smoke ran once, wrote only the four untagged `smoke/` objects, labeled the shared deterministic ten posts with boolean values, and wrote nothing under `batches/`. Commit the three temporary Git artifacts that `step10.md` names.

## Files to inspect (read-only)

- `docs/plans/2026-09-05_generate_bluesky_llm_features_4d8a7c/reports/smoke/deterministic_ten_post_ids.json`

## Files allowed to change

- `docs/plans/2026-09-05_generate_bluesky_llm_features_4d8a7c/reports/smoke/is_likely_spam/is_likely_spam_cost_report.json`
- `docs/plans/2026-09-05_generate_bluesky_llm_features_4d8a7c/reports/smoke/is_likely_spam/is_likely_spam_resume_evidence.json`
- `docs/plans/2026-09-05_generate_bluesky_llm_features_4d8a7c/reports/smoke/is_likely_spam/is_likely_spam_s3_checks.txt`

The first two files are written by the smoke caller and are committed as written. The checks file is written by the smoke caller and then extended with the observed listing, the id comparison, and the label type check.

## Files forbidden to change

Any Parquet or CSV file. Everything under `data_platform/`, `lib/`, `ml_tooling/`, `tests/`, `pyproject.toml`, `CHANGELOG.md`, `plan.md`, and `steps/*.md` of the epic plan folder. The `is_news_or_opinion/` and `is_political/` smoke artifacts.

## Commands

### List the prefix after the smoke

Run the same boto3 listing as Step 1.

Expected: `object_count=4`, the four keys `smoke/input.parquet`, `smoke/output.parquet`, `smoke/cost_report.json`, and `smoke/resume_evidence.json`, each with `tags=[]`, and no key starting with `batches/`.

### Compare the output ids with the deterministic sample and check the label type

```bash
PYTHONPATH=. uv run python - <<'PY'
import io, json, boto3, pandas as pd
BUCKET = "mirrorview-experimental-artifacts"
KEY = ("data_platform/data/bluesky/bluesky_7e2c4a91-3b5f-4d8e-a6c1-0f9b8d2e5a73/features/"
       "bluesky_2026_09_03_235130_llm_features_v1/is_likely_spam/smoke/output.parquet")
s3 = boto3.client("s3", region_name="us-east-2")
frame = pd.read_parquet(io.BytesIO(s3.get_object(Bucket=BUCKET, Key=KEY)["Body"].read()))
expected = json.load(open(
    "docs/plans/2026-09-05_generate_bluesky_llm_features_4d8a7c/reports/smoke/deterministic_ten_post_ids.json"
))["source_record_ids"]
print(f"output_rows={len(frame)}")
print(f"output_columns={list(frame.columns)}")
print(f"deterministic_ids_match={str(sorted(frame['source_record_id']) == sorted(expected)).lower()}")
print(f"run_id_values={sorted(frame['run_id'].unique())}")
print(f"batch_id_values={sorted(frame['batch_id'].unique())}")
print(f"is_likely_spam_dtype={frame['is_likely_spam'].dtype}")
print(f"all_labels_boolean={str(all(isinstance(v, bool) for v in frame['is_likely_spam'].tolist())).lower()}")
print(f"is_likely_spam_counts={frame['is_likely_spam'].value_counts().to_dict()}")
PY
```

Expected: the Q44 columns `source_record_id`, `run_id`, `batch_id`, `request_id`, `attempt_count`, `label_timestamp`, `is_likely_spam`, then `deterministic_ids_match=true`, then `all_labels_boolean=true`, then counts that use only `True` and `False`.

### Record the observations

Append the listing before, the listing after, and the id and label check output to `is_likely_spam_s3_checks.txt` under a heading that names each command. Keep the caller's own check lines at the top of the file unchanged.

### Commit

```bash
git add docs/plans/2026-09-05_generate_bluesky_llm_features_4d8a7c/reports/smoke/is_likely_spam/is_likely_spam_cost_report.json \
        docs/plans/2026-09-05_generate_bluesky_llm_features_4d8a7c/reports/smoke/is_likely_spam/is_likely_spam_resume_evidence.json \
        docs/plans/2026-09-05_generate_bluesky_llm_features_4d8a7c/reports/smoke/is_likely_spam/is_likely_spam_s3_checks.txt
git commit -m "Record the is_likely_spam Phase A smoke evidence (issue #190)"
```

Always add explicit paths. `git status` shows 24 Bluesky dump Parquet files as modified because of an LFS stat cache artifact, and those must never be staged.

## Must pass

- `object_count=4`, all four keys under `smoke/`, all `tags=[]`.
- Zero keys under `batches/`.
- `deterministic_ids_match=true`.
- `all_labels_boolean=true`.
- `resume_evidence.json` has `reattached_same_batch_id: true`, `resume_ok: true`, and `submit_calls_after_resume` equal to `{"files.create": 0, "batches.create": 0}`.
- `git show --stat HEAD` lists only the three files above.

## Must fail

- Any `.parquet` or `.csv` path in `git diff --cached --name-only`.
