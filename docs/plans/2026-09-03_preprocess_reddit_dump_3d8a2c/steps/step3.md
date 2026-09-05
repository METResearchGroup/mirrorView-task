# Step 3: Write the dump dataset's preprocessed parquet with Git LFS

## Goal

Run Reddit preprocess on the promoted dump dataset and commit the sampled preprocessed parquet through Git LFS.

## Caller / unit of work

**Main caller:** `data_platform/preprocessing/preprocess_reddit.py` `main` with `--config data_platform/ingestion/data_dumps/reddit/pushshift_dump.yaml`.

**Task:** pull the dump parquet LFS objects if needed, run preprocess, confirm the new preprocessed run is parquet, and commit that parquet plus its metadata through Git LFS.

**Out of scope:** Changing validators. Re-promoting raw files. Bluesky dump preprocess. Editing agent-owned README files. `CHANGELOG.md` during implementation.

## Files to inspect (read-only)

| Path | Why |
|------|-----|
| `/workspace/docs/plans/2026-09-03_preprocess_reddit_dump_3d8a2c/plan.md` | Parent plan |
| `/workspace/docs/plans/2026-09-03_preprocess_reddit_dump_3d8a2c/steps/step1.md` | Dataset id and raw run names that must already exist |
| `/workspace/docs/plans/2026-09-03_preprocess_reddit_dump_3d8a2c/steps/step2.md` | Sample size 200,000 per raw run |
| `/workspace/data_platform/preprocessing/preprocess_reddit.py` | Config CLI from step 2 |
| `/workspace/.gitattributes` | LFS rule from step 1 already covers this dataset's parquet files |
| `/workspace/.gitignore` | Dataset exception from step 1 must already un-ignore preprocessed files |

## Files allowed to change

- `/workspace/data_platform/data/reddit/reddit_3d8a2c41-9b17-4e6f-a5d0-8c1b2e4f6079/preprocessed/**`

Do not rewrite plan files during implementation.

## Files forbidden to change

- `/workspace/data_platform/preprocessing/README.md`
- `/workspace/data_platform/ingestion/data_dumps/reddit/README.md`
- `/workspace/docs/runbooks/HOW_TO_GET_POSTS_FOR_STIMULI_DATASET.md`
- `/workspace/data_platform/ingestion/configs/reddit/**`
- `/workspace/CHANGELOG.md`
- Any production Python module unless a blocker in the real run proves a step 2 contract was missed. If that happens, fix the contract in a follow-up commit on this branch and say so in the commit message.

## Decision (locked)

Use the real dump dataset, not fixtures. Pull Git LFS objects for the two promoted raw parquet files before running preprocess.

```bash
git lfs pull --include "data_platform/ingestion/data_dumps/reddit/filtered/*.parquet,data_platform/data/reddit/reddit_3d8a2c41-9b17-4e6f-a5d0-8c1b2e4f6079/raw/**/*.parquet"
```

Then:

```bash
PYTHONPATH=. uv run python data_platform/preprocessing/preprocess_reddit.py \
  --config data_platform/ingestion/data_dumps/reddit/pushshift_dump.yaml
```

Expected stdout includes a keep count and a path under `data_platform/data/reddit/reddit_3d8a2c41-9b17-4e6f-a5d0-8c1b2e4f6079/preprocessed/<timestamp>/`.

After the write:

1. The preprocessed records file is `comments.parquet`, not `comments.csv`.
2. `metadata.json` `row_counts.output` is <= 400000 (200,000 per source run).
3. `metadata.json` `source_raw_runs` lists both `raw/2025_05_01-00:00:00` and `raw/2025_06_01-00:00:00`.
4. `git lfs ls-files` lists the new preprocessed parquet.

Do not hand-edit the preprocessed parquet. If preprocess fails, fix code from step 2 rather than writing a stub output.

## Tests that must pass

No new unit tests in this step. Re-run:

```bash
PYTHONPATH=. uv run pytest tests/data_platform/preprocessing/test_preprocess_sample.py tests/data_platform/preprocessing/test_preprocess_reddit.py tests/data_platform/ingestion/test_promote_reddit_dump_to_raw.py -q
```

Expected: exit 0.

Confirm the artifact:

```bash
PYTHONPATH=. uv run python -c "
from pathlib import Path
import json
root = Path('data_platform/data/reddit/reddit_3d8a2c41-9b17-4e6f-a5d0-8c1b2e4f6079/preprocessed')
runs = sorted(p for p in root.iterdir() if p.is_dir())
assert runs, 'missing preprocessed run'
run = runs[-1]
assert (run / 'comments.parquet').is_file()
meta = json.loads((run / 'metadata.json').read_text())
print(run)
print(meta['row_counts'])
print(meta['source_raw_runs'])
assert meta['row_counts']['output'] <= 400000
assert meta['source_raw_runs'] == ['raw/2025_05_01-00:00:00', 'raw/2025_06_01-00:00:00']
"
```

Expected: prints the run path, row counts, and both source raw runs, then exits 0.

## Pass / fail

Pass when the dump dataset has a committed preprocessed `comments.parquet` in Git LFS, output row count is at most 400,000, and both month raw runs are listed as sources.

Fail if the output is csv, if it is gitignored, if it is a pointer-less 77MB blob committed as normal git, or if sampling was skipped and both full 500,000-row files were written after filters.
