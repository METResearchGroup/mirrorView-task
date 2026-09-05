# Step 3: Run preprocess on the dump dataset and store the sampled output in Git LFS

## Goal

Pull the copied dump parquet blobs, run Bluesky preprocess with the dump YAML, and commit the preprocessed parquet through Git LFS. Do not change mapping, sampling, or YAML contracts from Steps 1 and 2.

## Caller / unit of work

**Main caller:** `data_platform/preprocessing/preprocess_bluesky.py` `main` with `--config data_platform/preprocessing/configs/bluesky/jetstream_dump.yaml`.

**Task:** produce a completed preprocessed run under `data_platform/data/bluesky/bluesky_7e2c4a91-3b5f-4d8e-a6c1-0f9b8d2e5a73/preprocessed/{timestamp}/` with at most 200,000 rows, tracked by Git LFS.

**Out of scope:** Changing Step 1 or Step 2 code unless the live run hits a contract bug. Feature generation. Curation. Keyword ingest. Re-querying Athena. `CHANGELOG.md` during the run (changelog is owned by the later PR-writing step).

## Files to inspect (read-only)

| Path | Why |
|------|-----|
| `/workspace/data_platform/preprocessing/configs/bluesky/jetstream_dump.yaml` | Dataset id and sample settings |
| `/workspace/data_platform/data/bluesky/bluesky_7e2c4a91-3b5f-4d8e-a6c1-0f9b8d2e5a73/raw/2026_09_01-00:00:00/` | Copied LFS pointers from Step 1 |
| `/workspace/data_platform/preprocessing/preprocess_bluesky.py` | `--config` CLI from Step 2 |
| `/workspace/.gitattributes` | Dump-dataset parquet already uses Git LFS |
| `/workspace/AGENTS.md` | `PYTHONPATH=. uv run python ...` |

## Files allowed to change

- `/workspace/data_platform/data/bluesky/bluesky_7e2c4a91-3b5f-4d8e-a6c1-0f9b8d2e5a73/preprocessed/**` (new run dir written by preprocess)

Do not edit the plan package during implementation.

If the live run hits a contract bug in Step 2 code, fix only the broken helper and add a regression test in `/workspace/tests/data_platform/ingestion/test_bluesky_dump_preprocess.py`. Do not redesign sampling or YAML keys.

## Files forbidden to change

- `/workspace/data_platform/preprocessing/configs/bluesky/jetstream_dump.yaml`
- `/workspace/data_platform/ingestion/data_dumps/bluesky/data/parquet/**`
- `/workspace/data_platform/ingestion/sync_bluesky.py`
- `/workspace/data_platform/generate_features/**`
- `/workspace/data_platform/curate/**`
- `/workspace/CHANGELOG.md`
- Any file outside the allowed list, except git commits of this work and a regression fix described above

## Commands

From the repo root.

Pull dump parquet blobs for the copied raw run (same LFS oids as the dump folder):

```bash
git lfs pull --include "data_platform/data/bluesky/bluesky_7e2c4a91-3b5f-4d8e-a6c1-0f9b8d2e5a73/raw/**"
```

If that include path is empty because the blobs are only stored on the dump path, pull the dump path instead, then copy is unnecessary because oids are shared:

```bash
git lfs pull --include "data_platform/ingestion/data_dumps/bluesky/data/parquet/**"
```

Expected: each `hour=00` through `hour=23` parquet under the raw run dir is a real parquet file larger than the 133-byte pointer, or Git LFS smudge resolves it on read.

Install Python deps if needed:

```bash
uv sync
```

Run preprocess:

```bash
PYTHONPATH=. uv run python data_platform/preprocessing/preprocess_bluesky.py \
  --config data_platform/preprocessing/configs/bluesky/jetstream_dump.yaml
```

Expected stdout includes `preprocess_records: kept ` followed by a count that is at most 200000, then ` -> ` and a path under `data_platform/data/bluesky/bluesky_7e2c4a91-3b5f-4d8e-a6c1-0f9b8d2e5a73/preprocessed/`.

Confirm the written files:

```bash
python - <<'PY'
from pathlib import Path
import json
import pandas as pd
root = Path("data_platform/data/bluesky/bluesky_7e2c4a91-3b5f-4d8e-a6c1-0f9b8d2e5a73/preprocessed")
run = max(p for p in root.iterdir() if p.is_dir())
meta = json.loads((run / "metadata.json").read_text())
posts = pd.read_parquet(run / "posts.parquet")
assert meta["dataset_id"] == "bluesky_7e2c4a91-3b5f-4d8e-a6c1-0f9b8d2e5a73"
assert meta["sample_size"] == 200000
assert meta["sample_seed"] == 20260901
assert meta["row_counts"]["sampled"] == len(posts)
assert len(posts) <= 200000
assert "uri" in posts.columns
assert "did" not in posts.columns
print(run)
print(len(posts), meta["row_counts"])
PY
```

Expected: prints the preprocessed run path, a row count `<= 200000`, and metadata row counts. Exit code 0.

`git add` the preprocessed run. Confirm LFS pointers:

```bash
git lfs ls-files | grep "data_platform/data/bluesky/bluesky_7e2c4a91-3b5f-4d8e-a6c1-0f9b8d2e5a73/preprocessed"
```

Expected: `posts.parquet` is listed.

Re-run unit tests after the live run:

```bash
PYTHONPATH=. uv run pytest tests/data_platform/ingestion/test_bluesky_dump_preprocess.py tests/data_platform/preprocessing/test_preprocess_bluesky.py -q
```

Expected: exit 0.

## Pass / fail

Pass:

- Preprocessed run exists, `sync_status` is absent or not `in_progress`, `metadata.json` records sample size 200000 and seed 20260901.
- `posts.parquet` has at most 200,000 rows, validates as preprocessed Bluesky posts (`uri`, `record_id`, `author_handle`, `text`, `source_record_id`; no `did`).
- That parquet is committed as a Git LFS pointer.
- Step 2 unit tests still pass.

Fail:

- Preprocess writes every surviving dump row without sampling.
- Output is CSV instead of parquet.
- Athena is queried again.
- Keyword ingest datasets under `data_platform/data/` are committed.
