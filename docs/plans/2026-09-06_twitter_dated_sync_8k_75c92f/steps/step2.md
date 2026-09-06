# Step 2: Record usage and run the sync for 8,000 posts

## Goal

Record X project usage, then run Twitter recent search with the dated config. Stop when the raw run reaches 8,000 posts, or when the 7-day search window has no more posts.

## Caller / unit of work

The main caller is `data_platform/ingestion/sync_twitter.py` `main`, which calls `run_sync_cli` and then `sync_records`.

`sync_records` writes `dataset.json` and starts or resumes a raw run under `data_platform/data/twitter/{dataset_id}/raw/{timestamp}/`. It prints `sync_records: wrote {n} rows to {output_dir} (status={sync_status})`.

The task is to call that CLI with the dated config and a working `X_BEARER_TOKEN`. Resume with `--run-dir` if the process stops before `sync_status` is `completed`.

Leave these out of scope. Do not change `sync_twitter.py` or `twitter_client.py`. Do not run preprocess, features, or curate. Do not `git add` raw files in this step. Step 3 commits them. Do not add a usage helper to the repo. Do not upload to S3.

## Files to inspect (read-only)

| Path | Why |
|------|-----|
| `/workspace/docs/plans/2026-09-06_twitter_dated_sync_8k_75c92f/plan.md` | Parent plan. Cost ceiling about $40. |
| `/workspace/docs/plans/2026-09-06_twitter_dated_sync_8k_75c92f/steps/step1.md` | The dated config must already exist. |
| `/workspace/data_platform/ingestion/configs/twitter/mirrorview_2026-09-05.yaml` | `--config` path. Must have `max_posts: 8000` and `limit_per_task: 110`. |
| `/workspace/data_platform/ingestion/sync_twitter.py` | `sync_records` and the print line. Resume uses latest in-progress run, or `--run-dir`. |
| `/workspace/data_platform/ingestion/sync_checkpoint.py` | `prepare_sync_run`, `finalize_local_disk_sync`, `run_sync_cli`. |
| `/workspace/data_platform/ingestion/twitter_client.py` | No user expansions. `username` is empty. Page size is at most 100, so 110 posts for a keyword is two pages. |
| `/workspace/data_platform/ingestion/sync_clients.py` | `init_twitter_client` reads `X_BEARER_TOKEN`. |
| `/workspace/docs/runbooks/HOW_TO_RUN_DATA_INGESTION.md` | Says not to commit `data_platform/data/` run artifacts. |
| `/workspace/.gitignore` | `data_platform/data/**` and `*.csv` ignore the output. |

## Files allowed to change

The live sync may write these paths on local disk. Do not `git add` them until step 3. Step 1 already un-ignored the dataset and marked csv as Git LFS.

- `/workspace/data_platform/data/twitter/{dataset_id}/dataset.json`
- `/workspace/data_platform/data/twitter/{dataset_id}/raw/{timestamp}/posts.csv`
- `/workspace/data_platform/data/twitter/{dataset_id}/raw/{timestamp}/metadata.json`

`{dataset_id}` is the new id from step 1. `{timestamp}` is the UTC run folder from `lib/timestamp_utils.get_current_timestamp`, e.g. `2026_09_06-18:00:00`.

## Files forbidden to change

- `/workspace/data_platform/ingestion/sync_twitter.py`
- `/workspace/data_platform/ingestion/twitter_client.py`
- `/workspace/data_platform/ingestion/sync_checkpoint.py`
- `/workspace/data_platform/ingestion/sync_clients.py`
- `/workspace/data_platform/ingestion/configs/twitter/mirrorview.yaml`
- `/workspace/data_platform/ingestion/configs/twitter/mirrorview_2026-09-05.yaml` (already finished in step 1)
- `/workspace/.gitignore`
- `/workspace/.gitattributes`
- `/workspace/data_platform/preprocessing/**`
- `/workspace/data_platform/generate_features/**`
- `/workspace/data_platform/curate/**`
- `/workspace/CHANGELOG.md`
- Any tracked file outside the allowed list

## Decision (locked)

Run the live collection in this Cloud Agent environment. `X_BEARER_TOKEN` is already present in the process environment. A repo-root `.env` file is not required when the variable is already set.

Do not add a usage script to the repository. Record usage with the Python snippet below.

The collection costs about $40 at $0.005 per post for 8,000 posts. Do not start this step until that spend is accepted.

## Contracts to lock

`X_BEARER_TOKEN` must be set. `GET https://api.x.com/2/usage/tweets` must return HTTP 200 before the sync starts.

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

The command prints `http_status=200`, `project_id=2061451038012448768`, and a `project_usage` integer. Save that integer as the before value.

Run the sync from the repo root:

```bash
PYTHONPATH=. uv run python data_platform/ingestion/sync_twitter.py \
  --config data_platform/ingestion/configs/twitter/mirrorview_2026-09-05.yaml
```

Stdout includes this line.

```text
sync_records: wrote 8000 rows to /workspace/data_platform/data/twitter/{dataset_id}/raw/{timestamp} (status=completed)
```

A documented 7-day window shortfall may print a `wrote` count below 8000 with `status=completed`. Step 3 must record that shortfall.

If the process stops before `completed`, resume the same raw folder.

```bash
PYTHONPATH=. uv run python data_platform/ingestion/sync_twitter.py \
  --config data_platform/ingestion/configs/twitter/mirrorview_2026-09-05.yaml \
  --run-dir {timestamp}
```

The same raw folder continues, and the print line shows the new total. Do not start a second dataset id.

Do not pass `--run-dir` on the first start.

## Tests that must pass

There is no live X test in CI. Do not add one.

After the sync print line appears, the raw folder must exist:

```bash
python - <<'PY'
from pathlib import Path
import json, yaml
cfg = yaml.safe_load(Path("data_platform/ingestion/configs/twitter/mirrorview_2026-09-05.yaml").read_text())
dataset_id = cfg["dataset_id"]
raw_root = Path("data_platform/data/twitter") / dataset_id / "raw"
runs = sorted(p for p in raw_root.iterdir() if p.is_dir())
assert runs, f"no raw runs under {raw_root}"
run_dir = runs[-1]
meta = json.loads((run_dir / "metadata.json").read_text())
posts = run_dir / "posts.csv"
assert posts.is_file(), posts
assert meta["dataset_id"] == dataset_id
assert meta["sync_status"] in {"completed", "in_progress"}
print(f"run_dir={run_dir}")
print(f"sync_status={meta['sync_status']}")
print(f"row_count={meta['row_count']}")
PY
```

The command prints `run_dir`, `sync_status`, and `row_count`. Step 3 fails the run if `sync_status` is still `in_progress` at the end.

## Pass / fail

The step passes when usage was recorded before the sync, the CLI wrote `posts.csv` and `metadata.json` under the new dataset id, and the process ended at `completed` or is ready to resume with `--run-dir`.

The step fails when any item in the list below is true.

- ingest Python files changed
- a new dataset id was created by mistake
- `posts.csv` is missing
- `.gitignore` or `.gitattributes` from step 1 were reverted
