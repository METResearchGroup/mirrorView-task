# Step 3: Smoke on Bedrock, then generate the full sample

## Scope

- **Caller:** the same `run.py` `main` from Step 2.
- **Task:** Export AWS credentials, run a 10-post smoke under `--run-id smoke`, confirm `part-00000.parquet` on S3, then run the full 10,200-post job with a timestamp `--run-id`, confirm parts plus `flips.parquet`, and commit `RESULTS.md`.
- **Out of scope:** pytest, editing product curate files, editing the filter-posts README, rewriting Step 1 modules except docstring fixes required by `write-docstring`, changing the pinned filtered source object.

## Files to inspect (read-only)

- `/workspace/experiments/generate_flips_2026_09_08/run.py`
- `/workspace/experiments/generate_flips_2026_09_08/README.md`
- `/workspace/docs/plans/2026-09-08_generate_flips_68b2b8/plan.md`
- `/workspace/docs/plans/2026-09-08_generate_flips_68b2b8/steps/step1.md`
- `/workspace/docs/plans/2026-09-08_generate_flips_68b2b8/steps/step2.md`

## Files allowed to change

- `/workspace/experiments/generate_flips_2026_09_08/RESULTS.md` (written from the live full run, then committed)
- `/workspace/CHANGELOG.md` after the live full `flips.parquet` exists

## Files forbidden to change

- `/workspace/experiments/filter_posts_used_for_stimulus_dataset_2026_09_08/README.md`
- `/workspace/experiments/scaled_mirrors_generation_2026_06_02/**`
- `/workspace/shared/flip_generation/**` except docstring fixes
- `/workspace/tests/**`
- `/workspace/docs/plans/2026-09-08_generate_flips_68b2b8/**`
- The filtered source S3 object `experiments/filter_posts_used_for_stimulus_dataset_2026_09_08/dataset.parquet`

## Smoke

Smoke writes only under `s3://mirrorview-experimental-artifacts/experiments/generate_flips_2026_09_08/smoke/`. Do not write smoke objects under a timestamp prefix. Do not delete objects under any other prefix.

```bash
export AWS_ACCESS_KEY_ID="$LAB_AWS_ACCESS_KEY_ID"
export AWS_SECRET_ACCESS_KEY="$LAB_AWS_ACCESS_KEY_SECRET"

PYTHONPATH=. uv run python experiments/generate_flips_2026_09_08/run.py --run-id smoke --max-posts 10
```

Expected stdout includes `run_prefix=experiments/generate_flips_2026_09_08/smoke/`, `part_count=1`, and `row_count=` plus `failed_count=` that sum to 10.

```bash
PYTHONPATH=. uv run python - <<'PY'
import json
from data_platform.generate_features.s3_feature_batches import parquet_rows
from data_platform.generate_features.s3_feature_campaign import CampaignObjectStore

store = CampaignObjectStore("mirrorview-experimental-artifacts")
prefix = "experiments/generate_flips_2026_09_08/smoke/"
part = store.get(f"{prefix}batches/part-00000.parquet")
assert part is not None
frame = parquet_rows(part.body)
assert list(frame.columns) == [
    "record_id",
    "original_text",
    "llm_toxicity_tier",
    "political_stance",
    "mirrored_text",
    "explanation",
    "label_timestamp",
], list(frame.columns)
errors = store.get(prefix + "errors.jsonl")
failed = set()
if errors is not None:
    failed = {
        json.loads(line)["source_record_id"]
        for line in errors.body.decode().splitlines()
        if line
    }
assert len(frame) + len(failed) == 10
assert (frame["mirrored_text"].astype(str).str.len() > 0).all()
part_keys = [k for k in store.list_keys(prefix + "batches/") if k.endswith(".parquet")]
assert len(part_keys) == 1
print("smoke ok", len(frame), "parts", len(part_keys))
PY
```

Expected: `smoke ok` with part count 1. If every smoke row failed, `part-00000.parquet` is absent and this check must fail; stop before the full run.

Re-run the same smoke command. Expected: `part_count=1`, no new part keys, `FileExistsError` must not appear (resume skips `put_new`).

If smoke `row_count` is 0, stop. Do not start the full run.

## Full run

The full job is 408 batches of 25 (10200 / 25). It can take hours. Use one `--run-id` and keep it if the process dies.

```bash
export AWS_ACCESS_KEY_ID="$LAB_AWS_ACCESS_KEY_ID"
export AWS_SECRET_ACCESS_KEY="$LAB_AWS_ACCESS_KEY_SECRET"

FULL_RUN_ID="$(PYTHONPATH=. uv run python -c 'from lib.timestamp_utils import get_current_timestamp; print(get_current_timestamp())')"
echo "$FULL_RUN_ID"

PYTHONPATH=. uv run python experiments/generate_flips_2026_09_08/run.py --run-id "$FULL_RUN_ID"
```

If the process is interrupted, rerun the same command with the printed `--run-id`. Existing parts must not be rewritten.

Expected stdout: `part_count=` equal to the number of parts that have at least one success row (408 if every chunk has a success; fewer if some chunks are all failures), `row_count=` plus `failed_count=` equal to 10200, `final_key=experiments/generate_flips_2026_09_08/{run_id}/flips.parquet`.

```bash
PYTHONPATH=. uv run python - <<'PY'
import json
from data_platform.generate_features.s3_feature_batches import parquet_rows
from data_platform.generate_features.s3_feature_campaign import CampaignObjectStore

store = CampaignObjectStore("mirrorview-experimental-artifacts")
# set PREFIX to the full run prefix from stdout
import os
prefix = os.environ["FLIP_RUN_PREFIX"]
final = store.get(prefix + "flips.parquet")
assert final is not None
frame = parquet_rows(final.body)
errors = store.get(prefix + "errors.jsonl")
failed = set()
if errors is not None:
    failed = {
        json.loads(line)["source_record_id"]
        for line in errors.body.decode().splitlines()
        if line
    }
assert len(frame) + len(failed) == 10200
assert not set(frame["record_id"].astype(str)) & failed
assert list(frame.columns) == [
    "record_id",
    "original_text",
    "llm_toxicity_tier",
    "political_stance",
    "mirrored_text",
    "explanation",
    "label_timestamp",
]
print("full ok", len(frame), len(failed))
PY
```

Run that check with `FLIP_RUN_PREFIX=experiments/generate_flips_2026_09_08/${FULL_RUN_ID}/`. Expected: `full ok 10200 0` or `full ok {n} {10200-n}`.

A second `put_new` of `flips.parquet` for that run must not happen on resume after the final file exists. Re-run the same full command. Expected: no new part keys, stdout `final_key=` still set, process exits 0.

Copy smoke stdout to `/opt/cursor/artifacts/generate_flips_smoke.log` when that directory exists. Copy full-run stdout to `/opt/cursor/artifacts/generate_flips_full.log` when that directory exists. If `/opt/cursor/artifacts/` is missing, skip the copy.

## RESULTS.md

Write `/workspace/experiments/generate_flips_2026_09_08/RESULTS.md` from the **full** run, not the smoke. Include:

- The smoke command and `row_count` / `failed_count`
- The full-run command and `FULL_RUN_ID`
- Pinned input URI, SHA-256, 10200 rows
- `part_count`, `row_count`, `failed_count`
- S3 URI of `flips.parquet` and its SHA-256
- A sentence that parts are immutable under `{run_prefix}batches/`

## CHANGELOG.md

After `flips.parquet` exists, add a changelog entry that shared flip generation writes incremental S3 parquet parts and that this experiment produced the 10,200-post flip set. Follow `/write-changelog`.

## Must pass

- Smoke: `row_count + failed_count = 10`, one part object, resume does not rewrite it.
- Full run: `row_count + failed_count = 10200`.
- `flips.parquet` column order matches the Step 1 contract.
- Filtered source object SHA-256 is still `9788331f898aa27352dcdf32a962b5722aecc1da61a4638b7bbd77a404415ab9`.
- `RESULTS.md` is committed.

## Must fail

- Starting the full run when smoke produced 0 mirrored rows.
- Writing smoke output under the full-run prefix.
- Overwriting the pinned filtered source object.
