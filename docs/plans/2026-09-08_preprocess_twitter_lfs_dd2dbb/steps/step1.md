# Step 1: Confirm the completed raw run

## Scope

- **Caller:** `data_platform/preprocessing/preprocess_twitter.py` `main`, which calls `preprocess_records`. Step 1 does not run the caller. It only confirms the raw input the caller will load.
- **Task:** Confirm the locked raw run is present and completed, and that local storage is set, before preprocess writes files.
- **Out of scope:** Running preprocess, changing preprocess Python, ingest, features, curate, S3, adding pytest.

## Files to inspect (read-only)

- `/workspace/data_platform/data/twitter/twitter_5901767a-e609-46fc-9a17-742516b548f2/dataset.json` (format must stay `csv`)
- `/workspace/data_platform/data/twitter/twitter_5901767a-e609-46fc-9a17-742516b548f2/raw/2026_09_08-01:37:50/metadata.json` (must be `sync_status=completed`, `row_count=6900`)
- `/workspace/data_platform/data/twitter/twitter_5901767a-e609-46fc-9a17-742516b548f2/raw/2026_09_08-01:37:50/posts.csv` (Git LFS csv already on this stack)
- `/workspace/data_platform/preprocessing/preprocess_twitter.py` (caller. Do not edit.)
- `/workspace/.gitattributes` (Step 1 of the ingest child already marks this dataset csv as Git LFS. Do not edit.)

## Files allowed to change

None in this step. Confirmation only.

## Files forbidden to change

- `/workspace/data_platform/preprocessing/**`
- `/workspace/data_platform/ingestion/**`
- `/workspace/data_platform/generate_features/**`
- `/workspace/data_platform/curate/**`
- `/workspace/.gitignore`
- `/workspace/.gitattributes`
- `/workspace/data_platform/data/twitter/twitter_fba4ddb2-fcf7-4a13-a7cc-0d98db44b547/**`
- `/workspace/docs/plans/2026-09-07_twitter_sync_preprocess_llm_curate_4a9cd5/**`
- `/workspace/docs/plans/2026-09-07_generate_twitter_llm_features_e3c91a/**`
- Any file under `/workspace/tests/`
- Any file outside the allowed list for this pull request

## Locked contracts

Raw run path:

```text
data_platform/data/twitter/twitter_5901767a-e609-46fc-9a17-742516b548f2/raw/2026_09_08-01:37:50
```

`sync_status` is `completed`. Raw `row_count` is `6900`. `dataset.json` format is `csv`. Username is empty.

Storage must be local:

```bash
export DATA_PLATFORM_STORAGE_BACKEND=local
```

Do not upload to S3 in this child.

## Given / when / then (Phase 4, no new pytest)

```text
given the locked dataset from the ingest child
when dataset.json and the raw run metadata are read
then format is csv
and sync_status is completed
and row_count is 6900
and DATA_PLATFORM_STORAGE_BACKEND is local
```

## Exact commands and expected output

```bash
export DATA_PLATFORM_STORAGE_BACKEND=local
python - <<'PY'
from pathlib import Path
import json
dataset_id = "twitter_5901767a-e609-46fc-9a17-742516b548f2"
root = Path("data_platform/data/twitter") / dataset_id
dataset = json.loads((root / "dataset.json").read_text())
assert dataset.get("format") == "csv", dataset
run_dir = root / "raw" / "2026_09_08-01:37:50"
meta = json.loads((run_dir / "metadata.json").read_text())
assert meta["sync_status"] == "completed", meta["sync_status"]
assert int(meta["row_count"]) == 6900, meta["row_count"]
assert (run_dir / "posts.csv").is_file()
print("raw_run=2026_09_08-01:37:50")
print("sync_status=completed")
print("row_count=6900")
print("format=csv")
PY
```

Expected: `sync_status=completed`, `row_count=6900`, `format=csv`.

## Pass / fail

The step passes when the locked raw run is completed with 6900 rows, format is csv, and local storage is set.

The step fails when any item below is true.

- `sync_status` is not `completed`
- raw `row_count` is not 6900
- `dataset.json` format is not `csv`
- `DATA_PLATFORM_STORAGE_BACKEND` is unset or is not `local`
- preprocess Python changed
