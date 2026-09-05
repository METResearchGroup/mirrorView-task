# Step 2: Add first-class S3 storage support to the data pipeline

## Goal

Introduce a configurable object-store backend for pipeline data so callers can read and write through either local disk or S3. Preserve today's local-disk behavior as the explicit development default. Reject Git LFS pointer text, path traversal, missing content hashes on S3 writes, and accidental overwrites of existing S3 objects.

## Dependencies

- **Step 1 merged:** pinned Bluesky objects exist in `s3://mirrorview-experimental-artifacts/` and `s3_migration_inventory.json` lists their keys and SHA-256 values.
- AWS credentials available the same way as Step 1.
- `uv sync` for boto3 and pandas.

This step does not remove Git LFS, does not change the production default backend (that is Step 3), and does not tag intermediate shards (that is Step 5).

## Main caller and implementation slice

**Main caller:** `data_platform/utils/storage.py` `StorageManager.load_records`.

**Implementation slice for this PR:** add `data_platform/utils/object_store.py` with `LocalObjectStore` and `S3ObjectStore`, wire `StorageManager` to resolve paths through the selected backend, and make `load_records(..., latest=True)` read the pinned preprocessed `posts.parquet` from S3 when `DATA_PLATFORM_STORAGE_BACKEND=s3`. Local backend remains the default when the env var is unset.

## Files to inspect (read-only)

| Path | Why |
|------|-----|
| `/workspace/data_platform/utils/storage.py` | Current `StorageManager`, `DATA_ROOT`, read/write helpers |
| `/workspace/data_platform/utils/dataset.py` | `dataset_root`, manifest loading |
| `/workspace/lib/aws/s3.py` | Existing boto3 wrapper |
| `/workspace/data_platform/data/bluesky/bluesky_7e2c4a91-3b5f-4d8e-a6c1-0f9b8d2e5a73/s3_migration_inventory.json` | Verified S3 keys and hashes from Step 1 |
| `/workspace/data_platform/data/bluesky/bluesky_7e2c4a91-3b5f-4d8e-a6c1-0f9b8d2e5a73/preprocessed/2026_09_03-23:51:30/metadata.json` | Pinned run for smoke read |
| `/workspace/data_platform/generate_features/platform_cli.py` | How feature CLIs construct `StorageManager` |
| `/workspace/data_platform/preprocessing/preprocess_bluesky.py` | Preprocess write path still local in this step |
| `/workspace/data_platform/ingestion/sync_bluesky.py` | Raw sync still local in this step |
| `/workspace/tests/data_platform/utils/test_storage.py` | Existing local storage expectations (read only; do not add tests in this PR) |
| `/workspace/AGENTS.md` | `PYTHONPATH=.` convention |

## Files allowed to change

- `/workspace/data_platform/utils/object_store.py` (new)
- `/workspace/data_platform/utils/storage.py`
- `/workspace/lib/aws/s3.py` (only if required for conditional PUT, ranged read, or tagging hooks used by `S3ObjectStore`; keep changes minimal)

Temporary smoke artifacts under `experiments/bluesky_s3_storage_smoke_2026_09_05/` may be committed for review and must be deleted before merge.

Do not edit plan package files during implementation.

## Files forbidden to change

- `/workspace/.gitattributes`
- `/workspace/.gitignore`
- `/workspace/data_platform/data/bluesky/bluesky_7e2c4a91-3b5f-4d8e-a6c1-0f9b8d2e5a73/s3_migration_inventory.json` (read for verification only)
- `/workspace/data_platform/data/bluesky/bluesky_7e2c4a91-3b5f-4d8e-a6c1-0f9b8d2e5a73/**/*.parquet` (git-tracked LFS)
- `/workspace/data_platform/scripts/migrate_bluesky_lfs_to_s3.py`
- `/workspace/data_platform/generate_features/**` (beyond what storage imports require — prefer zero feature changes)
- `/workspace/data_platform/preprocessing/**`
- `/workspace/data_platform/ingestion/**`
- `/workspace/data_platform/data/reddit/**`
- `/workspace/CHANGELOG.md`
- Any file under `/workspace/tests/`
- Any file outside the allowed list

## Locked contracts

| Item | Value |
|------|-------|
| Bucket | `mirrorview-experimental-artifacts` |
| Region | `us-east-2` |
| Pipeline key prefix | `data_platform/data/` |
| Backend env var | `DATA_PLATFORM_STORAGE_BACKEND` with allowed values `local` (default) and `s3` |
| Bucket env var | `DATA_PLATFORM_S3_BUCKET` defaulting to `mirrorview-experimental-artifacts` |
| Key construction | `data_platform/data/{platform}/{dataset_id}/{stage}/{run_name}/{filename}` mirrors `StorageManager.root_dir` layout |
| Path safety | Reject `..`, absolute paths, backslashes, and keys outside `data_platform/data/` |
| LFS pointer detection | First line exactly `version https://git-lfs.github.com/spec/v1` → raise `ValueError` with message containing `git-lfs pointer` |
| S3 overwrite policy | `put_bytes` and `put_file` require `allow_overwrite=False` by default; existing object with same key raises `FileExistsError` |
| S3 write metadata | Every S3 upload must include `sha256` in a sidecar field recorded in memory and returned to callers; use SHA-256 of body bytes |
| Hash on read | After S3 download, verify bytes against inventory or caller-supplied expected hash when provided |
| Default backend | `local` when env var unset — production default flip happens in Step 3 |
| Public API stability | `BlueskyStorageManager`, `StorageStage`, and existing method names remain; backend selection is internal or env-driven |
| Pinned smoke dataset | `bluesky_7e2c4a91-3b5f-4d8e-a6c1-0f9b8d2e5a73` preprocessed run `2026_09_03-23:51:30` |

`object_store.py` must expose at minimum:

- `class LocalObjectStore` — filesystem operations under `DATA_ROOT`
- `class S3ObjectStore` — wraps `lib.aws.s3.S3` with the locked policies above
- `def resolve_object_store() -> ObjectStore` — reads env vars and returns the backend

## Ordered implementation work

1. Add `object_store.py` with the locked interfaces and safety checks.
2. Extend `lib/aws/s3.py` only if `S3ObjectStore` needs `head_object`, conditional `put_object`, or `delete_object` helpers not already present.
3. Refactor `StorageManager` path helpers to build repo-relative keys without duplicating `data_platform`.
4. Route `load_records`, `write_records`, `append_records`, `write_dataframe`, `write_run_metadata`, and `load_run_metadata` through the object store while keeping local semantics unchanged when backend is `local`.
5. Add a small smoke entry point or `if __name__ == "__main__"` block in `object_store.py` is forbidden; use the live command below instead.
6. Run live smoke commands with `DATA_PLATFORM_STORAGE_BACKEND=s3` and confirm row count 200000 for the pinned preprocessed parquet.
7. Run the same smoke with backend unset and confirm local reads still work.
8. Delete temporary smoke artifacts before merge.

## Live smoke and basic check commands

Export AWS credentials:

```bash
export AWS_ACCESS_KEY_ID="$LAB_AWS_ACCESS_KEY_ID"
export AWS_SECRET_ACCESS_KEY="$LAB_AWS_ACCESS_KEY_SECRET"
```

**S3 read smoke** — load pinned preprocessed posts from S3:

```bash
DATA_PLATFORM_STORAGE_BACKEND=s3 \
DATA_PLATFORM_S3_BUCKET=mirrorview-experimental-artifacts \
PYTHONPATH=. uv run python - <<'PY'
from data_platform.utils.storage import BlueskyStorageManager, StorageStage
storage = BlueskyStorageManager(StorageStage.PREPROCESSED, "bluesky_7e2c4a91-3b5f-4d8e-a6c1-0f9b8d2e5a73")
run_dir = storage.root_dir / "2026_09_03-23:51:30"
df = storage.load_records(run_dir)
assert len(df) == 200000
assert "source_record_id" in df.columns
print("s3 load ok", len(df))
PY
```

Expected stdout: `s3 load ok 200000` and exit code 0.

**Local read smoke** — default backend still uses disk:

```bash
PYTHONPATH=. uv run python - <<'PY'
from data_platform.utils.storage import BlueskyStorageManager, StorageStage
storage = BlueskyStorageManager(StorageStage.PREPROCESSED, "bluesky_7e2c4a91-3b5f-4d8e-a6c1-0f9b8d2e5a73")
df = storage.load_records(latest=True)
print("local load ok", len(df))
PY
```

Expected stdout: `local load ok 200000` when LFS blobs are present locally; if only pointers exist locally, the command may fail until `git lfs pull`, which is acceptable for local dev and does not block the S3 smoke above.

**LFS pointer rejection smoke** — write attempt on pointer bytes must fail fast:

```bash
PYTHONPATH=. uv run python - <<'PY'
from pathlib import Path
from data_platform.utils.object_store import S3ObjectStore
store = S3ObjectStore(bucket="mirrorview-experimental-artifacts", prefix="data_platform/data")
pointer = Path("data_platform/data/bluesky/bluesky_7e2c4a91-3b5f-4d8e-a6c1-0f9b8d2e5a73/raw/2026_09_01-00:00:00/date=2026-09-01/hour=00/87e175daae2e2a8367e353ab2018088747e1f1deaa9b052889d9fd276297b2ef.parquet")
raw = pointer.read_bytes()
try:
    store.put_bytes("bluesky/smoke/pointer.parquet", raw)
except ValueError as e:
    assert "git-lfs pointer" in str(e)
    print("pointer rejected ok")
else:
    raise SystemExit("expected ValueError")
PY
```

Expected stdout: `pointer rejected ok`. Run only when the hour-00 file is still a pointer (before `git lfs pull` on that path).

**Overwrite rejection smoke** — re-upload pinned preprocessed key without `allow_overwrite`:

```bash
DATA_PLATFORM_STORAGE_BACKEND=s3 \
PYTHONPATH=. uv run python - <<'PY'
from data_platform.utils.object_store import S3ObjectStore
store = S3ObjectStore(bucket="mirrorview-experimental-artifacts", prefix="data_platform/data")
key = "bluesky/bluesky_7e2c4a91-3b5f-4d8e-a6c1-0f9b8d2e5a73/preprocessed/2026_09_03-23:51:30/posts.parquet"
body = store.get_bytes(key)
try:
    store.put_bytes(key, body, allow_overwrite=False)
except FileExistsError:
    print("overwrite rejected ok")
else:
    raise SystemExit("expected FileExistsError")
PY
```

Expected stdout: `overwrite rejected ok`.

## Acceptance criteria

- `StorageManager.load_records` reads the pinned 200,000-row preprocessed parquet from S3 when `DATA_PLATFORM_STORAGE_BACKEND=s3`.
- Default backend without env var remains local and does not change existing local path layout.
- S3 writes reject overwrites by default and record SHA-256 for uploaded bytes.
- LFS pointer bytes are rejected on S3 upload.
- No Git LFS or `.gitattributes` changes.
- No automated tests added or run.

## Failure conditions

- S3 keys include a duplicated `data_platform` segment.
- Backend defaults to `s3` in this PR (that belongs to Step 3).
- Reading S3 returns LFS pointer text or wrong row count for the pinned preprocessed file.
- Overwrite of an existing production object succeeds without an explicit `allow_overwrite=True`.
- Reddit storage paths or unrelated buckets are referenced.
- Feature-generation behavior changes beyond using the shared storage layer.

## PR artifact and commit rules

- One independently mergeable PR.
- Commit `object_store.py` and `storage.py` changes together; keep `lib/aws/s3.py` edits in a separate commit only if they are non-trivial.
- Temporary smoke outputs under `experiments/bluesky_s3_storage_smoke_2026_09_05/` may be committed for review; remove before merge.
- Do not add pytest files or run pytest.
- Do not edit other step specs or `plan.md`.
- PR title suggestion: `Add configurable S3 object store for data platform storage`.
