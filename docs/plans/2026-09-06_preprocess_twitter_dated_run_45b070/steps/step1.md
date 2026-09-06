# Step 1: Pull the raw csv and run Twitter preprocess

## Goal

Pull the raw Git LFS csv from pull request 213, then run Twitter preprocess on that dataset. Write one completed preprocessed run. Do not commit in this step.

## Caller / unit of work

**Main caller:** `data_platform/preprocessing/preprocess_twitter.py` `main` with `--dataset-id twitter_fba4ddb2-fcf7-4a13-a7cc-0d98db44b547`.

**Task:** `git lfs pull` the raw `posts.csv`, then `preprocess_records` loads that completed raw run, adds standardized columns, drops already-preprocessed ids and study-stimuli ids, collapses duplicate tweet ids, applies Twitter text transforms and validators, and writes `preprocessed/<timestamp>/posts.csv` plus `metadata.json`.

**Out of scope:** Committing files. Changing preprocess or ingest Python. Adding a preprocess YAML. Sampling. Feature generation. Curation. S3. Re-running Twitter sync. `CHANGELOG.md`.

## Files to inspect (read-only)

| Path | Why |
|------|-----|
| `/workspace/docs/plans/2026-09-06_preprocess_twitter_dated_run_45b070/plan.md` | Parent plan |
| `/workspace/data_platform/data/twitter/twitter_fba4ddb2-fcf7-4a13-a7cc-0d98db44b547/dataset.json` | `format` is `csv`. Dataset id is `twitter_fba4ddb2-fcf7-4a13-a7cc-0d98db44b547` |
| `/workspace/data_platform/data/twitter/twitter_fba4ddb2-fcf7-4a13-a7cc-0d98db44b547/raw/2026_09_06-19:05:35/posts.csv` | Raw Git LFS csv. Unique `tweet_id` count is 6901 |
| `/workspace/data_platform/data/twitter/twitter_fba4ddb2-fcf7-4a13-a7cc-0d98db44b547/raw/2026_09_06-19:05:35/metadata.json` | `sync_status` is `completed`. `row_count` is 6901 |
| `/workspace/data_platform/ingestion/configs/twitter/mirrorview_2026-09-05.yaml` | Ingest YAML that names this dataset. Do not edit |
| `/workspace/data_platform/preprocessing/preprocess_twitter.py` | CLI is `--dataset-id` only. No `--config` |
| `/workspace/data_platform/preprocessing/runner.py` | `preprocess_records` and `export_preprocessed_records` |
| `/workspace/data_platform/utils/storage.py` | `TwitterStorageManager` writes `posts.csv` when dataset format is csv |
| `/workspace/.gitattributes` | `data_platform/data/twitter/twitter_fba4ddb2-fcf7-4a13-a7cc-0d98db44b547/**/*.csv` already uses Git LFS |
| `/workspace/.gitignore` | Dataset path and `**/*.csv` are already un-ignored |
| `/workspace/AGENTS.md` | Prefix commands with `PYTHONPATH=.` |

## Files allowed to change

- `/workspace/data_platform/data/twitter/twitter_fba4ddb2-fcf7-4a13-a7cc-0d98db44b547/preprocessed/**` (new run directory written by preprocess)

Do not rewrite plan files during implementation.

If the live run hits a contract bug in preprocess, stop and report it. Do not patch validators, sampling, or ingest in this step.

## Files forbidden to change

- `/workspace/data_platform/preprocessing/preprocess_twitter.py`
- `/workspace/data_platform/preprocessing/runner.py`
- `/workspace/data_platform/preprocessing/validators/**`
- `/workspace/data_platform/ingestion/sync_twitter.py`
- `/workspace/data_platform/ingestion/configs/twitter/mirrorview_2026-09-05.yaml`
- `/workspace/data_platform/data/twitter/twitter_fba4ddb2-fcf7-4a13-a7cc-0d98db44b547/dataset.json`
- `/workspace/data_platform/data/twitter/twitter_fba4ddb2-fcf7-4a13-a7cc-0d98db44b547/raw/**`
- `/workspace/data_platform/preprocessing/configs/**`
- `/workspace/.gitattributes`
- `/workspace/.gitignore`
- `/workspace/CHANGELOG.md`
- `/workspace/docs/runbooks/DATA_INGESTION_PIPELINE_ARCHITECTURE.md`
- Any file outside the allowed list

## Decision (locked)

Use the real dated dataset, not fixtures. Pull the raw Git LFS csv before preprocess, matching dump preprocess pull requests 164 and 162.

```bash
git lfs pull --include "data_platform/data/twitter/twitter_fba4ddb2-fcf7-4a13-a7cc-0d98db44b547/raw/**/*.csv"
```

Expected: `data_platform/data/twitter/twitter_fba4ddb2-fcf7-4a13-a7cc-0d98db44b547/raw/2026_09_06-19:05:35/posts.csv` is a real csv larger than a 130-byte Git LFS pointer.

Confirm the pointer is gone:

```bash
python - <<'PY'
from pathlib import Path
p = Path("data_platform/data/twitter/twitter_fba4ddb2-fcf7-4a13-a7cc-0d98db44b547/raw/2026_09_06-19:05:35/posts.csv")
data = p.read_bytes()
assert not data.startswith(b"version https://git-lfs.github.com/spec/v1"), data[:80]
assert data.startswith(b"tweet_id,"), data[:80]
print(p, "bytes", len(data))
PY
```

Expected: prints the path and a byte size, then exits 0.

Then:

```bash
PYTHONPATH=. uv run python data_platform/preprocessing/preprocess_twitter.py \
  --dataset-id twitter_fba4ddb2-fcf7-4a13-a7cc-0d98db44b547
```

Expected stdout:

```text
preprocess_records: kept <N> of <M> (skipped 0 already in a prior preprocessed run, skipped <S> already used as stimuli) -> data_platform/data/twitter/twitter_fba4ddb2-fcf7-4a13-a7cc-0d98db44b547/preprocessed/<timestamp>
```

`<N>` is at most 6901. `<S>` may be greater than 0. There is no prior preprocessed run, so the already-preprocessed skip count is 0.

Do not hand-edit the preprocessed csv. If preprocess fails, stop. Do not write a stub output.

## Tests that must pass

No new unit tests in this step. After the live run:

```bash
PYTHONPATH=. uv run pytest tests/data_platform/preprocessing/test_preprocess_twitter.py -q
```

Expected: exit 0.

Confirm the artifact:

```bash
PYTHONPATH=. uv run python - <<'PY'
from pathlib import Path
import json
import pandas as pd
from data_platform.models.sync import PreprocessedTwitterPostModel

root = Path("data_platform/data/twitter/twitter_fba4ddb2-fcf7-4a13-a7cc-0d98db44b547/preprocessed")
runs = sorted(p for p in root.iterdir() if p.is_dir())
assert runs, "missing preprocessed run"
run = runs[-1]
posts_path = run / "posts.csv"
assert posts_path.is_file()
assert not (run / "posts.parquet").exists()
meta = json.loads((run / "metadata.json").read_text())
posts = pd.read_csv(posts_path, keep_default_na=False, dtype={"tweet_id": "string", "author_id": "string", "author_handle": "string", "source_record_id": "string"})
assert meta["dataset_id"] == "twitter_fba4ddb2-fcf7-4a13-a7cc-0d98db44b547"
assert meta["source_raw_runs"] == ["raw/2026_09_06-19:05:35"]
assert meta["row_counts"]["output"] == len(posts)
assert len(posts) <= 6901
assert posts["tweet_id"].nunique() == len(posts)
for row in posts.to_dict(orient="records"):
    PreprocessedTwitterPostModel.model_validate(row)
print(run)
print(meta["row_counts"])
print(meta["source_raw_runs"])
print("kept", len(posts))
PY
```

Expected: prints the run path, row counts, the one source raw run, and the kept count, then exits 0.

## Pass / fail

Pass when:

- The raw csv is a real file, not a Git LFS pointer.
- A new preprocessed run exists with `posts.csv` and `metadata.json`.
- Output is csv, not parquet.
- `source_raw_runs` is exactly `["raw/2026_09_06-19:05:35"]`.
- Output row count equals the csv row count and is at most 6901.
- Every row validates as `PreprocessedTwitterPostModel`.
- `test_preprocess_twitter.py` exits 0.

Fail if:

- Preprocess is skipped and files are copied by hand.
- Output is parquet.
- A second Twitter sync is run.
- Ingest or preprocess Python is edited.
- Sampling is added.
