# Step 2: Run live recent search and commit the raw run

## Scope

- **Caller:** `data_platform/ingestion/sync_twitter.py` `main`. It loads `--config` through `run_sync_cli` and passes the path to `sync_records`.
- **Task:** Record X project usage, run live recent search for the 2026-09-07 config without `--run-dir` on first start, resume with `--run-dir {timestamp}` only if interrupted, verify empty username and Posts Read usage, then commit the raw files.
- **Out of scope:** Preprocess, features, curate, S3, ingest Python, a second dataset identity, adding pytest, a live X test module.

`sync_records` writes `dataset.json` and starts or resumes a raw run under `data_platform/data/twitter/twitter_5901767a-e609-46fc-9a17-742516b548f2/raw/{timestamp}/`. It prints `sync_records: wrote {n} rows to {output_dir} (status={sync_status})`. Twitter has no `new-run` subcommand.

## Files to inspect (read-only)

- `/workspace/data_platform/ingestion/sync_twitter.py` (print line and `--run-dir` resume. Do not edit.)
- `/workspace/data_platform/ingestion/twitter_client.py` (no user expansions. `username` is empty. Do not edit.)
- `/workspace/data_platform/ingestion/configs/twitter/mirrorview_2026-09-07.yaml` (written in step 1)

## Files allowed to change

- `/workspace/data_platform/data/twitter/twitter_5901767a-e609-46fc-9a17-742516b548f2/dataset.json`
- `/workspace/data_platform/data/twitter/twitter_5901767a-e609-46fc-9a17-742516b548f2/raw/{timestamp}/posts.csv`
- `/workspace/data_platform/data/twitter/twitter_5901767a-e609-46fc-9a17-742516b548f2/raw/{timestamp}/metadata.json`

`{timestamp}` is the UTC run folder from `lib.timestamp_utils.get_current_timestamp`.

## Files forbidden to change

- `/workspace/data_platform/ingestion/configs/twitter/mirrorview_2026-09-05.yaml`
- `/workspace/data_platform/ingestion/sync_twitter.py`
- `/workspace/data_platform/ingestion/twitter_client.py`
- `/workspace/data_platform/data/twitter/twitter_fba4ddb2-fcf7-4a13-a7cc-0d98db44b547/**`
- `/workspace/data_platform/preprocessing/**`
- `/workspace/data_platform/generate_features/**`
- `/workspace/data_platform/curate/**`
- Any file under `/workspace/tests/`
- Any file outside the allowed list, except git commits of this work and the files already changed in step 1

## Locked contracts

- Dataset id stays `twitter_5901767a-e609-46fc-9a17-742516b548f2`.
- Empty `username` on every raw row.
- Cost is Posts Read at `$0.005` per post. Ceiling is about `$40` for 8,000 posts.
- Usage increase should equal the row count, plus or minus a small number of extra Posts Read from pagination.
- Fail if usage increased by about three times the row count. That pattern is User Read.
- Expect `project_id=2061451038012448768`.
- A documented 7-day recent-search shortfall below 8,000 with `status=completed` is success.
- `posts.csv` is Git LFS. `dataset.json` and `metadata.json` are ordinary git files.

## Given / when / then (Phase 4, no new pytest)

```text
given X_BEARER_TOKEN is set
when GET https://api.x.com/2/usage/tweets
then http_status is 200
and project_id is 2061451038012448768
and project_usage is an integer saved as the before value

given the dated config and Git LFS matching already in place
when PYTHONPATH=. uv run python data_platform/ingestion/sync_twitter.py --config data_platform/ingestion/configs/twitter/mirrorview_2026-09-07.yaml
then stdout includes sync_records: wrote {n} rows to .../raw/{timestamp} (status=completed)
and n is 8000, or n is lower because the 7-day window ran out

given that completed raw run
when posts.csv and metadata.json are checked
then sync_status is completed
and csv row count equals metadata row_count
and every username is empty
and a second usage GET shows an increase near the row count, not about three times the row count
```

## Exact commands and expected output

Record usage before the sync:

```bash
python - <<'PY'
import json, os, urllib.request
token = os.environ["X_BEARER_TOKEN"]
req = urllib.request.Request(
    "https://api.x.com/2/usage/tweets",
    headers={"Authorization": f"Bearer {token}"},
)
with urllib.request.urlopen(req, timeout=30) as resp:
    data = json.load(resp)["data"]
print("http_status=200")
print(f"project_id={data['project_id']}")
print(f"project_cap={data['project_cap']}")
print(f"project_usage={data['project_usage']}")
print(f"cap_reset_day={data['cap_reset_day']}")
PY
```

Expected: `http_status=200`, `project_id=2061451038012448768`, and a `project_usage` integer. Save that integer as the before value.

Run the sync from the repo root. Do not pass `--run-dir` on the first start.

```bash
PYTHONPATH=. uv run python data_platform/ingestion/sync_twitter.py \
  --config data_platform/ingestion/configs/twitter/mirrorview_2026-09-07.yaml
```

Stdout includes:

```text
sync_records: wrote 8000 rows to /workspace/data_platform/data/twitter/twitter_5901767a-e609-46fc-9a17-742516b548f2/raw/{timestamp} (status=completed)
```

A documented 7-day window shortfall may print a `wrote` count below 8000 with `status=completed`.

If the process stops before `completed`, resume the same raw folder:

```bash
PYTHONPATH=. uv run python data_platform/ingestion/sync_twitter.py \
  --config data_platform/ingestion/configs/twitter/mirrorview_2026-09-07.yaml \
  --run-dir {timestamp}
```

Do not start a second dataset id.

Check the raw run:

```bash
python - <<'PY'
from pathlib import Path
import csv, json, yaml
cfg = yaml.safe_load(Path("data_platform/ingestion/configs/twitter/mirrorview_2026-09-07.yaml").read_text())
dataset_id = cfg["dataset_id"]
assert dataset_id == "twitter_5901767a-e609-46fc-9a17-742516b548f2"
raw_root = Path("data_platform/data/twitter") / dataset_id / "raw"
run_dir = sorted(p for p in raw_root.iterdir() if p.is_dir())[-1]
meta = json.loads((run_dir / "metadata.json").read_text())
assert meta["sync_status"] == "completed", meta["sync_status"]
row_count = int(meta["row_count"])
assert row_count > 0
with (run_dir / "posts.csv").open(newline="", encoding="utf-8") as handle:
    rows = list(csv.DictReader(handle))
assert len(rows) == row_count, (len(rows), row_count)
nonempty = [row["tweet_id"] for row in rows if row.get("username")]
assert nonempty == [], nonempty[:5]
print(f"run_dir={run_dir}")
print(f"row_count={row_count}")
print("username_empty=yes")
print("shortfall=yes" if row_count < 8000 else "shortfall=no")
PY
```

Expected: `sync_status` completed, `username_empty=yes`, and either `row_count=8000` with `shortfall=no` or a lower count with `shortfall=yes`.

Record usage after the sync with the same snippet. Subtract the before value. The increase should equal the row count, plus or minus a small number of extra Posts Read from pagination. Fail if the increase is about three times the row count.

```bash
git add \
  data_platform/data/twitter/twitter_5901767a-e609-46fc-9a17-742516b548f2/dataset.json \
  data_platform/data/twitter/twitter_5901767a-e609-46fc-9a17-742516b548f2/raw/{timestamp}/metadata.json \
  data_platform/data/twitter/twitter_5901767a-e609-46fc-9a17-742516b548f2/raw/{timestamp}/posts.csv
git status --short
git lfs ls-files | grep twitter_5901767a-e609-46fc-9a17-742516b548f2
git check-attr filter -- data_platform/data/twitter/twitter_5901767a-e609-46fc-9a17-742516b548f2/raw/{timestamp}/posts.csv
```

Expected: `git check-attr` prints `filter: lfs`. `git lfs ls-files` lists the new `posts.csv`. `dataset.json` and `metadata.json` are ordinary git files.

The implementation pull request body must include: dataset id, raw run path, row_count, `username_empty=yes`, project_usage before, project_usage after, usage increase, shortfall yes or no and the reason if yes, `Fixes #252`, and `Part of #251`.

## Pass / fail

The step passes when the raw run is `completed`, every `username` is empty, usage increased by about the row count, `posts.csv` is Git LFS, and a shortfall below 8,000 is documented if it happens.

The step fails when any item below is true.

- the dataset id was regenerated or reused from the 2026-09-05 collection
- `username` is non-empty
- usage increased by about three times the row count
- `sync_status` is not `completed`
- `posts.csv` is not Git LFS
- preprocess, features, or S3 upload ran
