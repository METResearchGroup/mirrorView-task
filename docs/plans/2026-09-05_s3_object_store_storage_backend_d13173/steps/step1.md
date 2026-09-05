# Step 1: Add the object store module, extend the S3 helper, and route storage reads and writes through it

## Goal

Give `StorageManager` a second storage backend. With `DATA_PLATFORM_STORAGE_BACKEND=s3`, records and run metadata are read from and written to `s3://mirrorview-experimental-artifacts/data_platform/data/...` at the same relative paths the local layout uses. With the variable unset, everything stays on local disk exactly as today.

## Source of truth

The epic step spec is `docs/plans/2026-09-05_generate_bluesky_llm_features_4d8a7c/steps/step2.md`. Every locked value below is copied from it. If the two files disagree, the epic step spec wins and this file is wrong.

## Main caller

`data_platform/utils/storage.py` `StorageManager.load_records`.

Happy path through the caller: resolve the run directory, join the records filename, turn that path into a key relative to `data_platform/data`, ask the selected object store for the bytes, and parse the bytes into a dataframe.

## Files to inspect (read-only)

| Path | Why |
|------|-----|
| `docs/plans/2026-09-05_generate_bluesky_llm_features_4d8a7c/steps/step2.md` | Locked contracts, smoke commands, forbidden files |
| `docs/plans/2026-09-05_generate_bluesky_llm_features_4d8a7c/campaign_contract.md` | Bucket, prefix, and hash rules shared by later steps |
| `data_platform/utils/dataset.py` | `_DATA_ROOT`, `dataset_root`, manifest loading |
| `data_platform/data/bluesky/bluesky_7e2c4a91-3b5f-4d8e-a6c1-0f9b8d2e5a73/s3_migration_inventory.json` | SHA-256 of the pinned `posts.parquet` for the read hash check in the overwrite smoke |
| `data_platform/data/bluesky/bluesky_7e2c4a91-3b5f-4d8e-a6c1-0f9b8d2e5a73/preprocessed/2026_09_03-23:51:30/metadata.json` | Pinned run and row count |
| `data_platform/generate_features/platform_cli.py` | How feature CLIs construct `StorageManager` and use `root_dir` as a local `Path` |
| `data_platform/generate_features/engines/base.py` | `append_records` is called with `run_dir or feature_storage.root_dir` |
| `data_platform/ingestion/sync_checkpoint.py` | `write_run_metadata_atomic` is called repeatedly on the same run |
| `tests/data_platform/conftest.py` | The `data_root` fixture replaces `storage.DATA_ROOT` at test time |
| `tests/data_platform/utils/test_storage.py` | Existing local behavior that must keep passing |
| `AGENTS.md` | `PYTHONPATH=.` and AWS credential export pattern |

## Files allowed to change

- `data_platform/utils/object_store.py` (new)
- `data_platform/utils/storage.py`
- `lib/aws/s3.py` (only the conditional put, metadata on upload, and an existence check)

`CHANGELOG.md` is edited only in a separate commit after the PR is open. No smoke artifacts are committed; smoke output goes into the PR description.

## Files forbidden to change

- `.gitattributes`
- `.gitignore`
- `data_platform/data/bluesky/bluesky_7e2c4a91-3b5f-4d8e-a6c1-0f9b8d2e5a73/s3_migration_inventory.json`
- `data_platform/data/bluesky/bluesky_7e2c4a91-3b5f-4d8e-a6c1-0f9b8d2e5a73/**/*.parquet`
- `data_platform/scripts/migrate_bluesky_lfs_to_s3.py`
- `data_platform/generate_features/**`
- `data_platform/preprocessing/**`
- `data_platform/ingestion/**`
- `data_platform/data/reddit/**`
- Any file under `tests/`
- Any file under `docs/plans/2026-09-05_generate_bluesky_llm_features_4d8a7c/`
- Any file under `docs/plans/2026-09-05_copy_bluesky_lfs_artifacts_to_s3_9877d3/`

Never `git add` a Bluesky parquet file. `git status` lists the pulled parquet files as modified even though `git diff` is empty. Stage files by explicit path only.

## Locked values

| Item | Value |
|------|-------|
| Bucket | `mirrorview-experimental-artifacts` |
| Region | `us-east-2` |
| Key prefix | `data_platform/data` |
| Backend env var | `DATA_PLATFORM_STORAGE_BACKEND`, allowed values `local` (default when unset) and `s3`; any other value raises `ValueError` |
| Bucket env var | `DATA_PLATFORM_S3_BUCKET`, default `mirrorview-experimental-artifacts` |
| Key rule | A store key is the path relative to `data_platform/data`, e.g. `bluesky/{dataset_id}/{stage}/{run_name}/{filename}`. The full S3 key is `data_platform/data/` plus the store key. A key never contains `data_platform` twice. |
| Path safety | Reject an empty key, a key that starts with `/`, a key that contains a backslash, and a key with a `.` or `..` segment. Reject a key that starts with `data_platform/`, because the prefix already contains it. |
| LFS pointer | Bytes whose first line is exactly `version https://git-lfs.github.com/spec/v1` are a pointer. The S3 store raises `ValueError` with a message containing `git-lfs pointer` on upload and on download. |
| Overwrite policy | `put_bytes` and `put_file` default to `allow_overwrite=False`. When the key already exists in S3, raise `FileExistsError`. Use S3 conditional put (`If-None-Match: *`) so the check and the write are one request. |
| Upload hash | Every S3 upload stores `sha256` (lowercase hex of the body bytes) in S3 object metadata and returns that digest. Never treat the S3 ETag as a content hash. |
| Read hash | `get_bytes` accepts an optional expected SHA-256. When given, a mismatch raises `ValueError`. When not given, the bytes are returned after the pointer check only. |
| Pinned smoke object | `bluesky/bluesky_7e2c4a91-3b5f-4d8e-a6c1-0f9b8d2e5a73/preprocessed/2026_09_03-23:51:30/posts.parquet`, 200,000 rows, SHA-256 `3d267201de22378e2d5e1a2c9eb4eae4ab3bc174aca5a134233caa54df3578fe` |
| Public API | `StorageManager`, `BlueskyStorageManager`, `RedditStorageManager`, `TwitterStorageManager`, `StorageStage`, and every existing method name and signature stay. `root_dir`, `latest_run_dir`, and `create_new_run_dir` keep returning local `Path` objects. |

## Contracts

`data_platform/utils/object_store.py` exposes:

- `LFS_POINTER_FIRST_LINE = b"version https://git-lfs.github.com/spec/v1"`
- `S3_KEY_PREFIX = "data_platform/data"`
- `DEFAULT_S3_BUCKET = "mirrorview-experimental-artifacts"`
- `STORAGE_BACKEND_ENV_VAR = "DATA_PLATFORM_STORAGE_BACKEND"`
- `S3_BUCKET_ENV_VAR = "DATA_PLATFORM_S3_BUCKET"`
- `def validate_key(key: str) -> str` applies the path safety rules and returns the key unchanged.
- `def is_lfs_pointer(body: bytes) -> bool`
- `def sha256_hex(body: bytes) -> str`
- `class ObjectStore(Protocol)` with `exists(key) -> bool`, `get_bytes(key, *, expected_sha256: str | None = None) -> bytes`, `put_bytes(key, body, *, allow_overwrite: bool = False) -> str`, and `put_file(local_path, key, *, allow_overwrite: bool = False) -> str`. Both put methods return the SHA-256 of the body. `get_bytes` raises `FileNotFoundError` when the key is missing.
- `class LocalObjectStore(root: Path)` resolves `root / key`. Writes create parent directories, write to a temporary file in the same directory, then replace, so a partial write never leaves a half-written file. `put_bytes` with `allow_overwrite=False` raises `FileExistsError` when the file exists. Local reads do not check for pointer text, so local behavior stays as it is today.
- `class S3ObjectStore(bucket: str, prefix: str = S3_KEY_PREFIX, *, region_name: str = "us-east-2")` wraps `lib.aws.s3.S3`. The constructor raises `ValueError` when the normalized prefix is not `data_platform/data`.
- `def resolve_object_store(*, local_root: Path) -> ObjectStore` reads the two environment variables and returns the matching store.

`lib/aws/s3.py` gains:

- `upload_bytes(key, body, *, content_type=None, metadata: dict[str, str] | None = None, if_none_match: str | None = None)`. The two new keyword arguments are passed to `put_object` as `Metadata` and `IfNoneMatch` only when set.
- `object_exists(key) -> bool`, which calls `head_object` and returns `False` when S3 answers 404.

`data_platform/utils/storage.py` changes:

- `StorageManager.__init__` sets `self._store = resolve_object_store(local_root=DATA_ROOT)`.
- `StorageManager._key_for(path: Path) -> str` returns `path.relative_to(DATA_ROOT).as_posix()` and raises `ValueError` when the path is not under `DATA_ROOT`.
- `load_records`, `load_run_metadata`, and `TwitterStorageManager.load_records` read bytes through `self._store.get_bytes` and parse them with pandas or `json.loads`. A missing key raises `FileNotFoundError` with the same message text as today.
- `write_records` and `write_dataframe` serialize to bytes and call `put_bytes(key, body, allow_overwrite=False)`. Both methods create the records file for a run, so a second write to the same path now raises `FileExistsError` on both backends. No caller in the repository or in the test suite writes the same records file twice with these methods.
- `append_records`, `write_run_metadata`, and `write_run_metadata_atomic` call `put_bytes(key, body, allow_overwrite=True)`, because replacing the object is their purpose.
- `all_runs_complete`, `latest_run_dir`, `create_new_run_dir`, `load_seen_ids_from_disk`, `load_seen_ids_from_all_runs`, and `require_all_runs_complete` keep using the local filesystem. The "latest run" lookup therefore still needs the run directory to exist locally when the backend is `s3`. Step 3 of the epic owns the production backend flip and the S3-side run listing.

## Check design

No pytest files are added. The scenarios below are the executable spec, and each maps to one live command in the next section.

```text
given DATA_PLATFORM_STORAGE_BACKEND=s3 and the pinned preprocessed run dir path
when BlueskyStorageManager(PREPROCESSED, dataset).load_records(run_dir)
then the dataframe has 200000 rows and a source_record_id column

given the env var is unset and the LFS blob is present locally
when BlueskyStorageManager(PREPROCESSED, dataset).load_records(latest=True)
then the dataframe has 200000 rows and no S3 call happens

given the git pointer text of the hour-00 raw parquet
when S3ObjectStore.put_bytes("bluesky/smoke/pointer.parquet", pointer_bytes)
then ValueError is raised, its message contains "git-lfs pointer", and nothing is uploaded

given the pinned posts.parquet key already exists in S3
when S3ObjectStore.put_bytes(key, body) with the default allow_overwrite
then FileExistsError is raised and the object is unchanged

given the pinned posts.parquet key and its inventory SHA-256
when S3ObjectStore.get_bytes(key, expected_sha256=inventory_hash)
then the bytes are returned; with a wrong hash, ValueError is raised

given a key such as "../etc/passwd", "/abs", "a\\b", or "data_platform/data/x"
when validate_key(key)
then ValueError is raised
```

## Ordered implementation work

1. Scaffold `data_platform/utils/object_store.py` with the module constants, the protocol, both classes, and `resolve_object_store`, all with `NotImplementedError` bodies. Import it from `storage.py`. Commit.
2. Fill in the signatures listed under Contracts. Commit.
3. Implement `lib/aws/s3.py` `object_exists` and the `metadata` and `if_none_match` arguments on `upload_bytes`. Commit.
4. Implement `validate_key`, `is_lfs_pointer`, `sha256_hex`, and `LocalObjectStore`. Commit.
5. Implement `S3ObjectStore` and `resolve_object_store`. Commit.
6. Route `load_records`, `load_run_metadata`, and `TwitterStorageManager.load_records` through the store. Commit.
7. Route `write_records`, `write_dataframe`, `append_records`, `write_run_metadata`, and `write_run_metadata_atomic` through the store. Commit.
8. Run the live smoke commands below and the existing `uv run pytest` suite.

## Live smoke and basic check commands

Export AWS credentials first:

```bash
export AWS_ACCESS_KEY_ID="$LAB_AWS_ACCESS_KEY_ID"
export AWS_SECRET_ACCESS_KEY="$LAB_AWS_ACCESS_KEY_SECRET"
```

**S3 read smoke**

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

Expected stdout: `s3 load ok 200000`, exit code 0.

**Local read smoke**

```bash
PYTHONPATH=. uv run python - <<'PY'
from data_platform.utils.storage import BlueskyStorageManager, StorageStage
storage = BlueskyStorageManager(StorageStage.PREPROCESSED, "bluesky_7e2c4a91-3b5f-4d8e-a6c1-0f9b8d2e5a73")
df = storage.load_records(latest=True)
print("local load ok", len(df))
PY
```

Expected stdout: `local load ok 200000` when the LFS blob is present locally.

**LFS pointer rejection smoke**

The hour-00 raw parquet has already been pulled from LFS in this checkout, so the pointer text is read from the git object instead of the working tree. The bytes are the same pointer text the epic spec names.

```bash
PYTHONPATH=. uv run python - <<'PY'
import subprocess
from data_platform.utils.object_store import S3ObjectStore
store = S3ObjectStore(bucket="mirrorview-experimental-artifacts", prefix="data_platform/data")
path = "data_platform/data/bluesky/bluesky_7e2c4a91-3b5f-4d8e-a6c1-0f9b8d2e5a73/raw/2026_09_01-00:00:00/date=2026-09-01/hour=00/87e175daae2e2a8367e353ab2018088747e1f1deaa9b052889d9fd276297b2ef.parquet"
raw = subprocess.run(["git", "cat-file", "-p", f"HEAD:{path}"], check=True, capture_output=True).stdout
assert raw.startswith(b"version https://git-lfs.github.com/spec/v1")
try:
    store.put_bytes("bluesky/smoke/pointer.parquet", raw)
except ValueError as e:
    assert "git-lfs pointer" in str(e)
    print("pointer rejected ok")
else:
    raise SystemExit("expected ValueError")
assert not store.exists("bluesky/smoke/pointer.parquet")
print("no smoke object written")
PY
```

Expected stdout: `pointer rejected ok` then `no smoke object written`.

**Overwrite rejection smoke**

```bash
PYTHONPATH=. uv run python - <<'PY'
from data_platform.utils.object_store import S3ObjectStore, sha256_hex
store = S3ObjectStore(bucket="mirrorview-experimental-artifacts", prefix="data_platform/data")
key = "bluesky/bluesky_7e2c4a91-3b5f-4d8e-a6c1-0f9b8d2e5a73/preprocessed/2026_09_03-23:51:30/posts.parquet"
expected = "3d267201de22378e2d5e1a2c9eb4eae4ab3bc174aca5a134233caa54df3578fe"
body = store.get_bytes(key, expected_sha256=expected)
assert sha256_hex(body) == expected
try:
    store.put_bytes(key, body, allow_overwrite=False)
except FileExistsError:
    print("overwrite rejected ok")
else:
    raise SystemExit("expected FileExistsError")
PY
```

Expected stdout: `overwrite rejected ok`.

**Key safety and bad backend value check** (no AWS call)

```bash
PYTHONPATH=. uv run python - <<'PY'
import os
from pathlib import Path
from data_platform.utils.object_store import resolve_object_store, validate_key
bad = ["", "/abs/key", "a\\b", "../up", "x/./y", "data_platform/data/x"]
for key in bad:
    try:
        validate_key(key)
    except ValueError:
        continue
    raise SystemExit(f"expected ValueError for {key!r}")
os.environ["DATA_PLATFORM_STORAGE_BACKEND"] = "gcs"
try:
    resolve_object_store(local_root=Path("."))
except ValueError:
    print("key safety ok")
else:
    raise SystemExit("expected ValueError for backend gcs")
PY
```

Expected stdout: `key safety ok`.

**Regression check**

```bash
uv run pytest -q
```

Expected: the same pass count as the parent branch (631 passed) and no failures.

## Acceptance criteria

- The S3 read smoke prints `s3 load ok 200000`.
- The local read smoke prints `local load ok 200000` with the variable unset.
- The pointer smoke prints `pointer rejected ok` and `no smoke object written`.
- The overwrite smoke prints `overwrite rejected ok`.
- The key safety check prints `key safety ok`.
- `uv run pytest -q` passes with no new failures.
- No file under the forbidden list changed.

## Failure conditions

- Any S3 key contains `data_platform` twice.
- The backend defaults to `s3` when the variable is unset.
- Reading from S3 returns pointer text or the wrong row count.
- A put to an existing S3 key succeeds without `allow_overwrite=True`.
- An S3 upload has no `sha256` in its object metadata.
- Reddit paths or any other bucket are referenced.

## Commit rules

- One commit per ordered work item above. Keep the `lib/aws/s3.py` edit in its own commit.
- Stage files by explicit path. Never stage a parquet file.
- PR title: `Add configurable S3 object store for data platform storage`.
