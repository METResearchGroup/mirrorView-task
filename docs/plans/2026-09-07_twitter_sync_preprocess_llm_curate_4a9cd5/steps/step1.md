# Step 1: Add dated Twitter ingest config and run recent-search sync for 2026-09-07

## Goal

Add `data_platform/ingestion/configs/twitter/mirrorview_2026-09-07.yaml` as a copy of the 2026-09-05 Mirrorview ingest config, un-ignore the locked new dataset, mark its csv as Git LFS, run live recent search, and commit the raw run.

## Dependencies

None. Later steps use dataset id `twitter_5901767a-e609-46fc-9a17-742516b548f2`.

Requires `X_BEARER_TOKEN` in the process environment. A repo-root `.env` file is not required when the variable is already set.

## Caller / unit of work

The main caller is `data_platform/ingestion/sync_twitter.py` `main`. It loads `--config` through `run_sync_cli` in `data_platform/ingestion/sync_checkpoint.py` and passes the path to `sync_records`.

`sync_records` writes `dataset.json` and starts or resumes a raw run under `data_platform/data/twitter/twitter_5901767a-e609-46fc-9a17-742516b548f2/raw/{timestamp}/`. It prints `sync_records: wrote {n} rows to {output_dir} (status={sync_status})`.

This pull request writes the dated config, git ignore exceptions, Git LFS csv rule, runbook exception, then runs that CLI and commits the raw files. Twitter has no `new-run` subcommand. One command starts or resumes.

**Out of scope:** preprocess, features, curate, S3 upload, changing ingest Python, editing `mirrorview_2026-09-05.yaml` or `mirrorview.yaml`, un-ignoring other Twitter datasets, adding files under `docs/plans/2026-09-07_generate_twitter_llm_features_e3c91a/`, generating a new dataset id.

## Files to inspect (read-only)

| Path | Why |
|------|-----|
| `/workspace/docs/plans/2026-09-07_twitter_sync_preprocess_llm_curate_4a9cd5/plan.md` | Parent plan. |
| `/workspace/docs/plans/2026-09-07_twitter_sync_preprocess_llm_curate_4a9cd5/campaign_contract.md` | Locked dataset id and ingest fields. |
| `/workspace/data_platform/ingestion/configs/twitter/mirrorview_2026-09-05.yaml` | Copy source. 73 keywords. `max_posts: 8000`. `limit_per_task: 110`. Dataset id `twitter_fba4ddb2-fcf7-4a13-a7cc-0d98db44b547`. Do not edit. |
| `/workspace/data_platform/ingestion/configs/twitter/mirrorview.yaml` | Undated config. Do not copy from this file. Do not edit. |
| `/workspace/data_platform/ingestion/sync_twitter.py` | Print line and `--run-dir` resume. Do not edit. |
| `/workspace/data_platform/ingestion/twitter_client.py` | No user expansions. `username` is empty. Do not edit. |
| `/workspace/data_platform/utils/dataset.py` | `validate_dataset_id` requires `twitter_` plus a lowercase UUID with hyphens. |
| `/workspace/tests/data_platform/ingestion/test_ingest_yaml_keys.py` | Globs every ingest YAML. The new file must pass. |
| `/workspace/.gitignore` | Copy the 2026-09-05 Twitter exception shape. Keep those exceptions. |
| `/workspace/.gitattributes` | Copy the 2026-09-05 csv LFS rule. Keep that rule. |
| `/workspace/docs/runbooks/DATA_INGESTION_PIPELINE_ARCHITECTURE.md` | Already allows `mirrorview_2026-09-05.yaml`. Add the 2026-09-07 dataset the same way. |

## Files allowed to change

- `/workspace/data_platform/ingestion/configs/twitter/mirrorview_2026-09-07.yaml`
- `/workspace/.gitignore`
- `/workspace/.gitattributes`
- `/workspace/docs/runbooks/DATA_INGESTION_PIPELINE_ARCHITECTURE.md`
- `/workspace/data_platform/data/twitter/twitter_5901767a-e609-46fc-9a17-742516b548f2/dataset.json`
- `/workspace/data_platform/data/twitter/twitter_5901767a-e609-46fc-9a17-742516b548f2/raw/{timestamp}/posts.csv`
- `/workspace/data_platform/data/twitter/twitter_5901767a-e609-46fc-9a17-742516b548f2/raw/{timestamp}/metadata.json`
- `/workspace/CHANGELOG.md`

`{timestamp}` is the UTC run folder from `lib/timestamp_utils.get_current_timestamp`.

Plan package files under `/workspace/docs/plans/2026-09-07_twitter_sync_preprocess_llm_curate_4a9cd5/` may already be on a planning branch. Do not rewrite them during implementation.

## Files forbidden to change

- `/workspace/data_platform/ingestion/configs/twitter/mirrorview_2026-09-05.yaml`
- `/workspace/data_platform/ingestion/configs/twitter/mirrorview.yaml`
- `/workspace/data_platform/ingestion/sync_twitter.py`
- `/workspace/data_platform/ingestion/twitter_client.py`
- `/workspace/data_platform/ingestion/sync_checkpoint.py`
- `/workspace/data_platform/ingestion/sync_clients.py`
- `/workspace/data_platform/data/twitter/twitter_fba4ddb2-fcf7-4a13-a7cc-0d98db44b547/**`
- `/workspace/data_platform/preprocessing/**`
- `/workspace/data_platform/generate_features/**`
- `/workspace/data_platform/curate/**`
- `/workspace/docs/plans/2026-09-07_generate_twitter_llm_features_e3c91a/**`
- Any file outside the allowed list, except git commits of this work

## Locked contracts

Use dataset id `twitter_5901767a-e609-46fc-9a17-742516b548f2`. Do not call `uuid.uuid4()`.

`/workspace/data_platform/ingestion/configs/twitter/mirrorview_2026-09-07.yaml` must be a copy of `mirrorview_2026-09-05.yaml` except these fields:

```text
dataset_id: twitter_5901767a-e609-46fc-9a17-742516b548f2
name: mirrorview_2026-09-07
description: Mirrorview topic keyword collection across Twitter (dated run 2026-09-07)
date: "2026-09-07"
```

Keep `max_posts: 8000`, `limit_per_task: 110`, the same 73 keywords in the same order, `dedupe_policy: [prior_runs_same_dataset]`, `lang: en`, `exclude: [reply, retweet, quote]`, and `record_types: [twitter.tweet]`.

Do not add unread keys that `tests/data_platform/ingestion/test_ingest_yaml_keys.py` forbids.

Append these git ignore exceptions next to the 2026-09-05 Twitter exceptions. Do not remove the existing Bluesky, Reddit, or 2026-09-05 Twitter exceptions.

```text
!data_platform/data/twitter/twitter_5901767a-e609-46fc-9a17-742516b548f2/
!data_platform/data/twitter/twitter_5901767a-e609-46fc-9a17-742516b548f2/**
!data_platform/data/twitter/twitter_5901767a-e609-46fc-9a17-742516b548f2/**/*.csv
```

Append this Git LFS rule. Do not change existing LFS lines.

```text
data_platform/data/twitter/twitter_5901767a-e609-46fc-9a17-742516b548f2/**/*.csv filter=lfs diff=lfs merge=lfs -text
```

In `/workspace/docs/runbooks/DATA_INGESTION_PIPELINE_ARCHITECTURE.md`, keep the rule that live API sync files are not committed by default. Extend the existing 2026-09-05 Twitter exception sentence so `mirrorview_2026-09-07.yaml` is also allowed and its `posts.csv` files are stored with Git LFS.

Empty `username` is required. Cost ceiling is about $40 at $0.005 Posts Read for 8,000 posts. A documented 7-day recent-search shortfall below 8,000 is success.

## Exact commands and expected output

Confirm Git LFS matching before the sync writes files:

```bash
git check-attr filter -- data_platform/data/twitter/twitter_5901767a-e609-46fc-9a17-742516b548f2/raw/placeholder/posts.csv
```

Expected: `filter: lfs`.

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

Record usage after the sync with the same snippet. Subtract the before value. The increase should equal the row count, plus or minus a small number of extra Posts Read from pagination. Fail if the increase is about three times the row count (Posts Read plus User Read).

Config identity checks:

```bash
python - <<'PY'
from pathlib import Path
import yaml
src = yaml.safe_load(Path("data_platform/ingestion/configs/twitter/mirrorview_2026-09-05.yaml").read_text())
new = yaml.safe_load(Path("data_platform/ingestion/configs/twitter/mirrorview_2026-09-07.yaml").read_text())
assert new["name"] == "mirrorview_2026-09-07"
assert new["date"] == "2026-09-07"
assert new["dataset_id"] == "twitter_5901767a-e609-46fc-9a17-742516b548f2"
assert new["ingestion_params"]["max_posts"] == 8000
assert new["ingestion_params"]["limit_per_task"] == 110
assert new["ingestion_params"]["keywords"] == src["ingestion_params"]["keywords"]
assert new["ingestion_params"]["dedupe_policy"] == src["ingestion_params"]["dedupe_policy"]
assert new["ingestion_params"]["lang"] == src["ingestion_params"]["lang"]
assert new["ingestion_params"]["exclude"] == src["ingestion_params"]["exclude"]
assert new["record_types"] == src["record_types"]
print("step1 config checks passed")
PY
```

Expected: `step1 config checks passed`.

```bash
PYTHONPATH=. uv run pytest tests/data_platform/ingestion/test_ingest_yaml_keys.py -q
```

Expected: exit 0. Do not add the new filename to any hardcoded allow-list. The glob already covers it. Do not add a live X test.

```bash
git add \
  data_platform/ingestion/configs/twitter/mirrorview_2026-09-07.yaml \
  .gitignore \
  .gitattributes \
  docs/runbooks/DATA_INGESTION_PIPELINE_ARCHITECTURE.md \
  data_platform/data/twitter/twitter_5901767a-e609-46fc-9a17-742516b548f2/dataset.json \
  data_platform/data/twitter/twitter_5901767a-e609-46fc-9a17-742516b548f2/raw/{timestamp}/metadata.json \
  data_platform/data/twitter/twitter_5901767a-e609-46fc-9a17-742516b548f2/raw/{timestamp}/posts.csv
git status --short
git lfs ls-files | grep twitter_5901767a-e609-46fc-9a17-742516b548f2
git check-attr filter -- data_platform/data/twitter/twitter_5901767a-e609-46fc-9a17-742516b548f2/raw/{timestamp}/posts.csv
```

Expected: `git check-attr` prints `filter: lfs`. `git lfs ls-files` lists the new `posts.csv`. `dataset.json` and `metadata.json` are ordinary git files.

The implementation pull request body must include: dataset id, raw run path, row_count, `username_empty=yes`, project_usage before, project_usage after, usage increase, shortfall yes or no and the reason if yes.

## Pass / fail

The step passes when the dated config exists with the locked id, keywords match the 2026-09-05 file, `test_ingest_yaml_keys.py` exits 0, the raw run is `completed`, every `username` is empty, usage increased by about the row count, `posts.csv` is Git LFS, and a shortfall below 8,000 is documented if it happens.

The step fails when any item below is true.

- the dataset id was regenerated or reused
- `mirrorview_2026-09-05.yaml` or ingest Python changed
- keywords, `max_posts`, or `limit_per_task` changed
- other Twitter datasets were un-ignored
- `posts.csv` is not Git LFS
- `username` is non-empty
- usage increased by about three times the row count
- `sync_status` is not `completed`
- preprocess, features, or S3 upload ran

## PR artifact and commit rules

- One independently mergeable PR for this step only.
- Logical commits: dated YAML plus git tracking, live sync raw files, changelog if used.
- PR title suggestion: `Add dated Twitter ingest config and run recent-search sync for 2026-09-07`.
