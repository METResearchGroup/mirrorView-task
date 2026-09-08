# Step 2: Preprocess the new dated Twitter collection and store it in Git LFS

## Goal

Run the existing Twitter preprocess entry point on dataset `twitter_5901767a-e609-46fc-9a17-742516b548f2`, then commit preprocessed `posts.csv` through Git LFS and `metadata.json` as an ordinary git file.

## Dependencies

- **Step 1 merged** on the GitHub stack: dated ingest YAML, git ignore exceptions, Git LFS csv rule, completed raw run under the locked dataset id.

## Caller / unit of work

The main caller is `data_platform/preprocessing/preprocess_twitter.py` `main`, which calls `preprocess_records`. There is no Twitter preprocess YAML.

Stdout includes:

```text
preprocess_records: kept {kept} of {input_count} (skipped {skipped} already in a prior preprocessed run, skipped {skipped_stimuli} already used as stimuli) -> {output_dir}
```

`{output_dir}` is `data_platform/data/twitter/twitter_5901767a-e609-46fc-9a17-742516b548f2/preprocessed/{preprocessed_run}/`.

This pull request runs that CLI once and commits the preprocessed files. Record `{preprocessed_run}` and `{row_count}` in the pull request body. Step 3 copies those values into the campaign YAML.

**Out of scope:** changing preprocess Python, ingest, features, curate, S3 upload, converting csv to parquet, changing `dataset.json` format, labeling posts.

## Files to inspect (read-only)

| Path | Why |
|------|-----|
| `/workspace/docs/plans/2026-09-07_twitter_sync_preprocess_llm_curate_4a9cd5/campaign_contract.md` | How to derive campaign id after this step. |
| `/workspace/docs/plans/2026-09-07_twitter_sync_preprocess_llm_curate_4a9cd5/steps/step1.md` | Raw run that must already exist. |
| `/workspace/data_platform/ingestion/configs/twitter/mirrorview_2026-09-07.yaml` | Confirms dataset id. |
| `/workspace/data_platform/preprocessing/preprocess_twitter.py` | `--dataset-id` only. Do not edit. |
| `/workspace/data_platform/preprocessing/runner.py` | Print line and `metadata.json` shape. |
| `/workspace/data_platform/data/twitter/twitter_5901767a-e609-46fc-9a17-742516b548f2/dataset.json` | Format must stay `csv`. |
| `/workspace/data_platform/data/twitter/twitter_5901767a-e609-46fc-9a17-742516b548f2/raw/{timestamp}/` | Step 1 raw run. |
| `/workspace/.gitignore` | Step 1 already un-ignores this dataset including csv. |
| `/workspace/.gitattributes` | Step 1 already marks this dataset csv as Git LFS. |

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
- `/workspace/docs/plans/2026-09-07_generate_twitter_llm_features_e3c91a/**`
- `/workspace/tests/**`
- Any file outside the allowed list

## Locked contracts

```bash
PYTHONPATH=. uv run python data_platform/preprocessing/preprocess_twitter.py \
  --dataset-id twitter_5901767a-e609-46fc-9a17-742516b548f2
```

Do not pass a preprocess YAML. Do not pass `--config`.

`dataset.json` `format` stays `csv`. Preprocessed records filename is `posts.csv`.

`metadata.json` must include `dataset_id`, `preprocess_timestamp`, and `row_counts.output`. `preprocess_timestamp` equals the run folder name.

Campaign id for Step 3:

```text
twitter_{preprocess_timestamp with '-' -> '_' and ':' removed}_llm_features_v1
```

Row count is `row_counts.output`. It may be below the raw row count because validators, prior-preprocessed skips, and previously used stimuli drop rows. That lower count is the campaign size. Do not force 6374.

Git LFS must store preprocessed `posts.csv`. `metadata.json` is an ordinary git file.

## Exact commands and expected output

Confirm the Step 1 raw run is present and `completed` before preprocess.

Run preprocess from the repo root with `PYTHONPATH=.`.

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

The implementation pull request body must include `preprocessed_run`, `row_count`, derived `campaign_id`, and `format=csv`.

Do not add pytest. Do not run the ingest YAML tests unless you touched ingest YAML (you must not).

## Pass / fail

The step passes when preprocess writes `posts.csv` and `metadata.json` under the new dataset, format stays `csv`, `posts.csv` is Git LFS, and the pull request records run timestamp, row count, and derived campaign id.

The step fails when any item below is true.

- preprocess Python changed
- `dataset.json` format is not `csv`
- files were written under the 2026-09-05 dataset
- S3 upload ran
- campaign YAML was added in this pull request
- `posts.csv` is not Git LFS
- a new pytest file was added

## PR artifact and commit rules

- One independently mergeable PR stacked on Step 1.
- Logical commits: preprocessed csv and metadata, changelog if used.
- PR title suggestion: `Preprocess the new dated Twitter collection and store it in Git LFS`.
