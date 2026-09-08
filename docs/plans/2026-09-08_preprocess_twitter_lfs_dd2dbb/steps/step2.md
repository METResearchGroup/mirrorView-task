# Step 2: Run preprocess and commit Git LFS files

## Scope

- **Caller:** `data_platform/preprocessing/preprocess_twitter.py` `main`, which calls `preprocess_records`.
- **Task:** Run that CLI once with local storage, then commit preprocessed `posts.csv` through Git LFS and `metadata.json` as an ordinary git file. Record `preprocessed_run`, `row_count`, and derived `campaign_id`.
- **Out of scope:** Changing preprocess Python, ingest, features, curate, S3 upload, converting csv to parquet, changing `dataset.json` format, labeling posts, adding pytest.

Stdout includes:

```text
preprocess_records: kept {kept} of {input_count} (skipped {skipped} already in a prior preprocessed run, skipped {skipped_stimuli} already used as stimuli) -> {output_dir}
```

`{output_dir}` is `data_platform/data/twitter/twitter_5901767a-e609-46fc-9a17-742516b548f2/preprocessed/{preprocessed_run}/`.

## Files to inspect (read-only)

- `/workspace/data_platform/preprocessing/preprocess_twitter.py` (`--dataset-id` only. Do not edit.)
- `/workspace/data_platform/preprocessing/runner.py` (print line and `metadata.json` shape. Do not edit.)
- `/workspace/data_platform/data/twitter/twitter_5901767a-e609-46fc-9a17-742516b548f2/dataset.json`
- `/workspace/data_platform/data/twitter/twitter_5901767a-e609-46fc-9a17-742516b548f2/raw/2026_09_08-01:37:50/`
- `/workspace/.gitattributes` (already marks this dataset csv as Git LFS. Do not edit.)

## Files allowed to change

- `/workspace/data_platform/data/twitter/twitter_5901767a-e609-46fc-9a17-742516b548f2/dataset.json` only if preprocess rewrites it and format stays `csv`
- `/workspace/data_platform/data/twitter/twitter_5901767a-e609-46fc-9a17-742516b548f2/preprocessed/{preprocessed_run}/posts.csv`
- `/workspace/data_platform/data/twitter/twitter_5901767a-e609-46fc-9a17-742516b548f2/preprocessed/{preprocessed_run}/metadata.json`
- `/workspace/CHANGELOG.md`

`{preprocessed_run}` is created at runtime. Do not invent it.

## Files forbidden to change

- `/workspace/data_platform/preprocessing/**`
- `/workspace/data_platform/ingestion/**`
- `/workspace/data_platform/generate_features/**`
- `/workspace/data_platform/curate/**`
- `/workspace/data_platform/ingestion/configs/twitter/mirrorview_2026-09-07.yaml`
- `/workspace/.gitignore`
- `/workspace/.gitattributes`
- `/workspace/data_platform/data/twitter/twitter_fba4ddb2-fcf7-4a13-a7cc-0d98db44b547/**`
- `/workspace/docs/plans/2026-09-07_twitter_sync_preprocess_llm_curate_4a9cd5/**`
- `/workspace/docs/plans/2026-09-07_generate_twitter_llm_features_e3c91a/**`
- Any file under `/workspace/tests/`
- Any file outside the allowed list

## Locked contracts

```bash
export DATA_PLATFORM_STORAGE_BACKEND=local
PYTHONPATH=. uv run python data_platform/preprocessing/preprocess_twitter.py \
  --dataset-id twitter_5901767a-e609-46fc-9a17-742516b548f2
```

Do not pass a preprocess YAML. Do not pass `--config`.

`dataset.json` format stays `csv`. Preprocessed records filename is `posts.csv`.

`metadata.json` must include `dataset_id`, `preprocess_timestamp`, and `row_counts.output`. `preprocess_timestamp` equals the run folder name.

Campaign id for later children:

```text
twitter_{preprocess_timestamp with '-' -> '_' and ':' removed}_llm_features_v1
```

Row count is `row_counts.output`. It may be below the raw row count because validators, prior-preprocessed skips, and previously used stimuli drop rows. That lower count is the campaign size. Do not force 6374.

Git LFS must store preprocessed `posts.csv`. `metadata.json` is an ordinary git file.

Do not upload to S3.

## Given / when / then (Phase 4, no new pytest)

```text
given the completed raw run and local storage
when PYTHONPATH=. uv run python data_platform/preprocessing/preprocess_twitter.py --dataset-id twitter_5901767a-e609-46fc-9a17-742516b548f2
then stdout includes preprocess_records: kept {kept} of {input_count} ... -> {output_dir}
and exit code is 0

given that preprocessed run
when dataset.json, metadata.json, and posts.csv are checked
then format is csv
and preprocess_timestamp equals the run folder name
and csv row count equals row_counts.output
and every text cell is non-empty
and git check-attr filter on posts.csv prints filter: lfs
```

## Exact commands and expected output

Run preprocess from the repo root with `PYTHONPATH=.` and local storage.

```bash
export DATA_PLATFORM_STORAGE_BACKEND=local
PYTHONPATH=. uv run python data_platform/preprocessing/preprocess_twitter.py \
  --dataset-id twitter_5901767a-e609-46fc-9a17-742516b548f2
```

Expected stdout matches `preprocess_records: kept {kept} of {input_count} ... -> {output_dir}` and exit 0.

Then:

```bash
python - <<'PY'
from pathlib import Path
import csv, json
dataset_id = "twitter_5901767a-e609-46fc-9a17-742516b548f2"
root = Path("data_platform/data/twitter") / dataset_id
dataset = json.loads((root / "dataset.json").read_text())
assert dataset.get("format") == "csv", dataset
pre_root = root / "preprocessed"
runs = sorted(p for p in pre_root.iterdir() if p.is_dir())
assert runs, f"no preprocessed runs under {pre_root}"
run_dir = runs[-1]
meta = json.loads((run_dir / "metadata.json").read_text())
assert meta["dataset_id"] == dataset_id
assert meta["preprocess_timestamp"] == run_dir.name
row_count = int(meta["row_counts"]["output"])
assert row_count > 0
posts = run_dir / "posts.csv"
assert posts.is_file()
with posts.open(newline="", encoding="utf-8") as handle:
    rows = list(csv.DictReader(handle))
assert len(rows) == row_count, (len(rows), row_count)
assert all(row.get("text") for row in rows)
campaign_id = (
    "twitter_"
    + run_dir.name.replace("-", "_").replace(":", "")
    + "_llm_features_v1"
)
print(f"preprocessed_run={run_dir.name}")
print(f"row_count={row_count}")
print(f"campaign_id={campaign_id}")
print("format=csv")
PY
```

Expected: prints `preprocessed_run`, `row_count`, derived `campaign_id`, and `format=csv`.

```bash
git add \
  data_platform/data/twitter/twitter_5901767a-e609-46fc-9a17-742516b548f2/dataset.json \
  data_platform/data/twitter/twitter_5901767a-e609-46fc-9a17-742516b548f2/preprocessed/{preprocessed_run}/posts.csv \
  data_platform/data/twitter/twitter_5901767a-e609-46fc-9a17-742516b548f2/preprocessed/{preprocessed_run}/metadata.json
git check-attr filter -- data_platform/data/twitter/twitter_5901767a-e609-46fc-9a17-742516b548f2/preprocessed/{preprocessed_run}/posts.csv
git lfs ls-files | grep twitter_5901767a-e609-46fc-9a17-742516b548f2/preprocessed
```

Expected: `filter: lfs` for preprocessed `posts.csv`.

The implementation pull request body must include `preprocessed_run`, `row_count`, derived `campaign_id`, `format=csv`, `Fixes #253`, and `Part of #251`.

Do not add pytest.

## Pass / fail

The step passes when preprocess writes `posts.csv` and `metadata.json` under the new dataset, format stays `csv`, `posts.csv` is Git LFS, and the pull request records run timestamp, row count, and derived campaign id.

The step fails when any item below is true.

- preprocess Python changed
- `dataset.json` format is not `csv`
- `posts.csv` is not Git LFS
- S3 upload ran
- a new pytest file was added
- row count was forced to 6374
