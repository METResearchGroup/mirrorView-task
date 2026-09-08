# Step 2: Run the command and write RESULTS.md

## Scope

- **Caller:** the same `run.py` `main` from Step 1.
- **Task:** Export AWS credentials, run the filter command, confirm local and S3 parquet, copy logs to `/opt/cursor/artifacts/`, and commit `RESULTS.md` with cleanup counts and both crosstab tables filled from the live run.
- **Out of scope:** pytest, editing product curate files, changing the combined source object, editing the experiment README, rewriting Step 1 modules except docstring fixes required by `write-docstring`.

## Files to inspect (read-only)

- `/workspace/experiments/filter_posts_used_for_stimulus_dataset_2026_09_08/run.py`
- `/workspace/experiments/filter_posts_used_for_stimulus_dataset_2026_09_08/README.md`
- `/workspace/experiments/combine_data_into_stimulus_set_2026_09_08/RESULTS.md`
- `/workspace/docs/plans/2026-09-08_filter_posts_stimulus_c4f821/steps/step1.md`

## Files allowed to change

- `/workspace/experiments/filter_posts_used_for_stimulus_dataset_2026_09_08/RESULTS.md` (written by the live command, then committed)
- `/workspace/CHANGELOG.md` after the live S3 object exists

## Files forbidden to change

- `/workspace/experiments/filter_posts_used_for_stimulus_dataset_2026_09_08/README.md`
- `/workspace/data_platform/curate/**`
- `/workspace/tests/**`
- `/workspace/experiments/combine_data_into_stimulus_set_2026_09_08/**`
- The combined source S3 object
- `/workspace/docs/plans/2026-09-08_filter_posts_stimulus_c4f821/**`

## Live commands

```bash
export AWS_ACCESS_KEY_ID="$LAB_AWS_ACCESS_KEY_ID"
export AWS_SECRET_ACCESS_KEY="$LAB_AWS_ACCESS_KEY_SECRET"

PYTHONPATH=. uv run python experiments/filter_posts_used_for_stimulus_dataset_2026_09_08/run.py
```

Expected stdout includes `candidate_rows=55573`, `cleaned_rows=54472`, `sampled_rows=9562`, a local path under `experiments/filter_posts_used_for_stimulus_dataset_2026_09_08/dataset.parquet`, `s3_uri=s3://mirrorview-experimental-artifacts/experiments/filter_posts_used_for_stimulus_dataset_2026_09_08/dataset.parquet`, `dataset_sha256=`, and two JSON tables.

```bash
PYTHONPATH=. uv run python - <<'PY'
import hashlib
from pathlib import Path
import pyarrow.parquet as pq
from data_platform.generate_features.s3_feature_campaign import CampaignObjectStore

local = Path("experiments/filter_posts_used_for_stimulus_dataset_2026_09_08/dataset.parquet")
store = CampaignObjectStore("mirrorview-experimental-artifacts")
key = "experiments/filter_posts_used_for_stimulus_dataset_2026_09_08/dataset.parquet"
stored = store.get(key)
assert stored is not None
want = [
    "integration",
    "source_dataset_id",
    "source_curated_run",
    "record_id",
    "source_record_id",
    "platform_id",
    "author_handle",
    "text",
    "created_at",
    "sync_timestamp",
    "news_or_opinion_category",
    "is_political",
    "is_likely_spam",
    "is_self_contained",
    "is_structurally_complete",
    "political_stance",
    "llm_toxicity_tier",
]
table = pq.read_table(local)
assert table.column_names == want, table.column_names
assert table.num_rows == 9562
assert hashlib.sha256(local.read_bytes()).hexdigest() == hashlib.sha256(stored.body).hexdigest()
print("filtered ok", table.num_rows, len(table.column_names))
PY
```

Expected: `filtered ok 9562 17`.

Copy the command stdout to `/opt/cursor/artifacts/filter_posts_stimulus_run.log`.

## Must pass

- Live command exits 0 on the first run.
- `sampled_rows=9562`.
- Sampled right-high count is 1062.
- Local SHA-256 equals S3 object SHA-256.
- `RESULTS.md` is committed.
- Combined source object SHA-256 is still `f24ad1fd8c3709ffbbba9fb5dc953dcaee2f11ad8916ae21612b7f25cb5ca3f0`.

## Must fail

- A second run of the same command, because `put_new` must raise `FileExistsError`.
