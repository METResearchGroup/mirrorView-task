# Step 1: Add the dated config and Git tracking

## Scope

- **Caller:** `data_platform/ingestion/sync_twitter.py` `main` through `run_sync_cli` in `data_platform/ingestion/sync_checkpoint.py`. Step 1 does not run the caller. It only prepares the files the caller will load.
- **Task:** Copy the 2026-09-05 Mirrorview Twitter ingest config to a 2026-09-07 file with four dated field changes, un-ignore the locked dataset, mark its csv as Git LFS, and extend the runbook exception for live sync files.
- **Out of scope:** Live X API calls, preprocess, features, curate, S3, ingest Python, editing `mirrorview_2026-09-05.yaml` or `mirrorview.yaml`, un-ignoring other Twitter datasets, adding pytest.

## Files to inspect (read-only)

- `/workspace/data_platform/ingestion/configs/twitter/mirrorview_2026-09-05.yaml` (copy source. 73 keywords. Do not edit.)
- `/workspace/data_platform/ingestion/configs/twitter/mirrorview.yaml` (undated. Do not copy from this file. Do not edit.)
- `/workspace/data_platform/ingestion/sync_twitter.py` (caller. Do not edit.)
- `/workspace/tests/data_platform/ingestion/test_ingest_yaml_keys.py` (globs every ingest YAML. The new file must pass.)
- `/workspace/.gitignore` (copy the 2026-09-05 Twitter exception shape. Keep those exceptions.)
- `/workspace/.gitattributes` (copy the 2026-09-05 csv LFS rule. Keep that rule.)
- `/workspace/docs/runbooks/DATA_INGESTION_PIPELINE_ARCHITECTURE.md` (already allows `mirrorview_2026-09-05.yaml`.)

## Files allowed to change

- `/workspace/data_platform/ingestion/configs/twitter/mirrorview_2026-09-07.yaml`
- `/workspace/.gitignore`
- `/workspace/.gitattributes`
- `/workspace/docs/runbooks/DATA_INGESTION_PIPELINE_ARCHITECTURE.md`

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
- `/workspace/docs/plans/2026-09-07_twitter_sync_preprocess_llm_curate_4a9cd5/**`
- `/workspace/docs/plans/2026-09-07_generate_twitter_llm_features_e3c91a/**`
- Any file under `/workspace/tests/`
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

In `/workspace/docs/runbooks/DATA_INGESTION_PIPELINE_ARCHITECTURE.md`, keep the rule that live API sync files are not committed by default. Extend the existing 2026-09-05 Twitter exception sentence so `mirrorview_2026-09-07.yaml` is also allowed and its `posts.csv` files are stored with Git LFS. Keep the same sentence shape.

## Work

1. Copy `mirrorview_2026-09-05.yaml` to `mirrorview_2026-09-07.yaml`. Change only `dataset_id`, `name`, `description`, and `date`.
2. Append the three git ignore exceptions after the 2026-09-05 Twitter block.
3. Append the Git LFS csv rule.
4. Extend the runbook sentence that already names `mirrorview_2026-09-05.yaml`.

## Given / when / then (Phase 4, no new pytest)

```text
given the 2026-09-05 Mirrorview Twitter ingest YAML
when the 2026-09-07 YAML is written
then dataset_id is twitter_5901767a-e609-46fc-9a17-742516b548f2
and name is mirrorview_2026-09-07
and date is 2026-09-07
and keywords, max_posts, limit_per_task, lang, exclude, dedupe_policy, and record_types match the 2026-09-05 file

given the new ingest YAML
when PYTHONPATH=. uv run pytest tests/data_platform/ingestion/test_ingest_yaml_keys.py -q
then exit 0

given the new Git LFS rule
when git check-attr filter -- data_platform/data/twitter/twitter_5901767a-e609-46fc-9a17-742516b548f2/raw/placeholder/posts.csv
then the output contains filter: lfs
```

## Exact commands and expected output

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
git check-attr filter -- data_platform/data/twitter/twitter_5901767a-e609-46fc-9a17-742516b548f2/raw/placeholder/posts.csv
```

Expected: `filter: lfs`.

## Pass / fail

The step passes when the dated config exists with the locked identity, keywords match the 2026-09-05 file, the YAML key test exits 0, Git LFS matching prints `filter: lfs` for a placeholder csv under the new dataset, and the 2026-09-05 git exceptions remain.

The step fails when any item below is true.

- the dataset id was regenerated
- `mirrorview_2026-09-05.yaml` or ingest Python changed
- keywords, `max_posts`, or `limit_per_task` changed
- other Twitter datasets were un-ignored
- Git LFS matching does not print `filter: lfs`
- a new pytest file was added
