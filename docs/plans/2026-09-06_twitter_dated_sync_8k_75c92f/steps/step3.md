# Step 3: Verify the raw run and commit the config plus raw files

## Goal

Check that the raw run has 8,000 rows, or a documented 7-day shortfall. Check that every `username` is empty, and that X usage increased by about the row count at Posts Read only. Then commit the dated config, the git ignore exceptions, the Git LFS csv rule, and the raw run files.

## Caller / unit of work

The main callers are the verification commands in this step, then `git add` of the dated config and the raw dataset files.

The task is to prove the sync met the issue 170 checks, and to publish the config and the raw run. Track `posts.csv` with Git LFS. Track `dataset.json` and `metadata.json` as ordinary git files.

Leave these out of scope. Do not run preprocess, features, or curate. Do not edit ingest Python. Do not edit `mirrorview.yaml`. Do not un-ignore other Twitter datasets. Do not upload to S3. Do not edit `docs/plans/` in the implementation pull request.

## Files to inspect (read-only)

| Path | Why |
|------|-----|
| `/workspace/docs/plans/2026-09-06_twitter_dated_sync_8k_75c92f/plan.md` | Parent plan. |
| `/workspace/docs/plans/2026-09-06_twitter_dated_sync_8k_75c92f/steps/step1.md` | Config contract. |
| `/workspace/docs/plans/2026-09-06_twitter_dated_sync_8k_75c92f/steps/step2.md` | Sync commands and the usage before value. |
| `/workspace/data_platform/ingestion/configs/twitter/mirrorview_2026-09-05.yaml` | Dated config to commit. |
| `/workspace/data_platform/data/twitter/{dataset_id}/dataset.json` | Dataset manifest to commit as an ordinary git file. |
| `/workspace/data_platform/data/twitter/{dataset_id}/raw/{timestamp}/metadata.json` | `row_count` and `sync_status`. Commit as an ordinary git file. |
| `/workspace/data_platform/data/twitter/{dataset_id}/raw/{timestamp}/posts.csv` | `username` column. Commit through Git LFS. |
| `/workspace/.gitignore` | Must already un-ignore this dataset, including `**/*.csv`. |
| `/workspace/.gitattributes` | Must already mark this dataset csv as Git LFS. |
| `/workspace/docs/runbooks/DATA_INGESTION_PIPELINE_ARCHITECTURE.md` | Exception for this dataset, added in step 1. |

## Files allowed to change

- `/workspace/data_platform/ingestion/configs/twitter/mirrorview_2026-09-05.yaml`
- `/workspace/.gitignore`
- `/workspace/.gitattributes`
- `/workspace/docs/runbooks/DATA_INGESTION_PIPELINE_ARCHITECTURE.md`
- `/workspace/data_platform/data/twitter/{dataset_id}/dataset.json`
- `/workspace/data_platform/data/twitter/{dataset_id}/raw/{timestamp}/metadata.json`
- `/workspace/data_platform/data/twitter/{dataset_id}/raw/{timestamp}/posts.csv`

`{dataset_id}` and `{timestamp}` come from step 1 and step 2. Do not add other raw runs.

## Files forbidden to change

- `/workspace/data_platform/ingestion/sync_twitter.py`
- `/workspace/data_platform/ingestion/twitter_client.py`
- `/workspace/data_platform/ingestion/configs/twitter/mirrorview.yaml`
- `/workspace/data_platform/preprocessing/**`
- `/workspace/data_platform/generate_features/**`
- `/workspace/data_platform/curate/**`
- `/workspace/docs/plans/**` in the implementation pull request
- `/workspace/CHANGELOG.md`
- Any file outside the allowed list, except git commits of the dated config and this dataset's raw files

## Decision (locked)

The implementation pull request adds the dated config, the git ignore exceptions, the Git LFS csv rule, `dataset.json`, `metadata.json`, and the Git LFS pointer for `posts.csv`. The planning files in this folder stay on the planning branch. Issue 170 said not to edit `docs/plans/**` while implementing the collection.

If `row_count` is below 8,000 because recent search only covers seven days, write the actual count and the reason in the implementation pull request body. A documented shortfall is a pass. An undocumented count below 8,000 is a fail.

Empty `username` is required. A non-empty username means user expansions came back, and User Read billing may have been charged.

## Contracts to lock

Load the dataset id from the dated config, then check the latest raw run:

```bash
python - <<'PY'
from pathlib import Path
import csv, json, yaml
cfg = yaml.safe_load(Path("data_platform/ingestion/configs/twitter/mirrorview_2026-09-05.yaml").read_text())
dataset_id = cfg["dataset_id"]
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
if row_count < 8000:
    print("shortfall=yes")
else:
    print("shortfall=no")
PY
```

`sync_status` is `completed` and `username_empty=yes`. Either `row_count=8000` with `shortfall=no`, or a lower `row_count` with `shortfall=yes`.

Record usage after the sync, using the same snippet as step 2. The command prints `http_status=200`. Subtract the step 2 before value. The increase should equal the row count, plus or minus a small number of extra Posts Read from pagination. The check fails if the increase is about three times the row count, because that pattern matches Posts Read plus User Read.

Git must stage the config and this dataset's raw files, and nothing else.

```bash
git add \
  data_platform/ingestion/configs/twitter/mirrorview_2026-09-05.yaml \
  .gitignore \
  .gitattributes \
  docs/runbooks/DATA_INGESTION_PIPELINE_ARCHITECTURE.md \
  data_platform/data/twitter/{dataset_id}/dataset.json \
  data_platform/data/twitter/{dataset_id}/raw/{timestamp}/metadata.json \
  data_platform/data/twitter/{dataset_id}/raw/{timestamp}/posts.csv
git status --short
git lfs ls-files
git check-attr filter -- data_platform/data/twitter/{dataset_id}/raw/{timestamp}/posts.csv
```

`git status --short` shows the dated config, git ignore, gitattributes, runbook, `dataset.json`, `metadata.json`, and `posts.csv`. It does not show other paths under `data_platform/data/`. `git lfs ls-files` lists `posts.csv`. `git check-attr` prints `filter: lfs` for `posts.csv`. `dataset.json` and `metadata.json` are not Git LFS files.

```bash
PYTHONPATH=. uv run pytest tests/data_platform/ingestion/test_ingest_yaml_keys.py -q
```

The command exits 0.

The implementation pull request body must include these lines.

```text
dataset_id
raw run path
row_count
username_empty=yes
project_usage before
project_usage after
usage increase
shortfall yes or no, and the reason if yes
```

## Tests that must pass

```bash
PYTHONPATH=. uv run pytest tests/data_platform/ingestion/test_ingest_yaml_keys.py -q
```

The command exits 0.

Do not add a live X test.

## Pass / fail

The step passes when `metadata.json` is `completed`, `username` is empty on every row, usage increased by about the row count, `posts.csv` is a Git LFS object, `dataset.json` and `metadata.json` are ordinary git files, and pytest above exits 0.

The step fails when any item in the list below is true.

- raw posts are missing from the commit
- `posts.csv` is not a Git LFS object
- `username` is non-empty
- `sync_status` is not `completed`
- usage increased by about three times the row count
- other Twitter datasets were un-ignored
- the implementation pull request edits ingest Python, `mirrorview.yaml`, or `docs/plans/`
