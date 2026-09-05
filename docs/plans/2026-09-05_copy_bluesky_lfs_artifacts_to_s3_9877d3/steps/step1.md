# Step 1: Add the migration script, the verify script, and the committed inventory

## Goal

Upload the 53 scoped Bluesky files to `s3://mirrorview-experimental-artifacts/` at repo-relative keys, confirm each upload with a SHA-256 comparison, and commit `s3_migration_inventory.json`. Leave every Git LFS pointer in the repository unchanged.

## Source of truth

The epic step spec is `docs/plans/2026-09-05_generate_bluesky_llm_features_4d8a7c/steps/step1.md`. Every locked value below is copied from it. If the two files disagree, the epic step spec wins and this file is wrong.

## Main caller

`data_platform/scripts/migrate_bluesky_lfs_to_s3.py` `main`.

Happy path through the caller: build the 53 paths, pull LFS blobs, then for each path read bytes, reject pointer text, hash, upload, re-download and compare, and finally write the inventory and print the summary line.

## Files to inspect (read-only)

| Path | Why |
|------|-----|
| `docs/plans/2026-09-05_generate_bluesky_llm_features_4d8a7c/steps/step1.md` | Locked scope, keys, inventory shape, smoke commands |
| `.gitattributes` | Confirms which Bluesky parquet paths are LFS |
| `lib/aws/s3.py` | `S3(bucket, region_name=...)`, `upload_bytes`, `get_bytes` |
| `lib/constants.py` | `REPO_ROOT` |
| `lib/timestamp_utils.py` | `get_current_timestamp` for `uploaded_at` |
| `data_platform/ingestion/data_dumps/bluesky/publish_dump_to_raw.py` | Existing script style, dataset id, raw run timestamp |
| `AGENTS.md` | `PYTHONPATH=.` and AWS credential export pattern |

## Files allowed to change

- `data_platform/scripts/migrate_bluesky_lfs_to_s3.py` (new)
- `data_platform/scripts/verify_bluesky_s3_migration.py` (new)
- `data_platform/data/bluesky/bluesky_7e2c4a91-3b5f-4d8e-a6c1-0f9b8d2e5a73/s3_migration_inventory.json` (new)

Smoke output goes into the PR description, not into a committed file. `CHANGELOG.md` is edited only in a separate commit after the PR is open.

## Files forbidden to change

- `data_platform/utils/storage.py`
- `lib/aws/s3.py`
- `.gitattributes`
- `.gitignore`
- `data_platform/data/bluesky/bluesky_7e2c4a91-3b5f-4d8e-a6c1-0f9b8d2e5a73/dataset.json`
- `data_platform/data/bluesky/bluesky_7e2c4a91-3b5f-4d8e-a6c1-0f9b8d2e5a73/raw/**`
- `data_platform/data/bluesky/bluesky_7e2c4a91-3b5f-4d8e-a6c1-0f9b8d2e5a73/preprocessed/**`
- `data_platform/ingestion/data_dumps/bluesky/data/**`
- `data_platform/data/reddit/**`
- Any file under `tests/`
- Any file under `docs/plans/2026-09-05_generate_bluesky_llm_features_4d8a7c/`

Never `git add` a Bluesky parquet file. After `git lfs pull`, `git status` may list the pulled parquet files as modified even though `git diff` is empty. Stage files by explicit path only.

## Locked values

| Item | Value |
|------|-------|
| Bucket | `mirrorview-experimental-artifacts` |
| Region | `us-east-2` |
| Dataset id | `bluesky_7e2c4a91-3b5f-4d8e-a6c1-0f9b8d2e5a73` |
| Raw run | `2026_09_01-00:00:00` |
| Preprocessed run | `2026_09_03-23:51:30` |
| Key rule | The S3 key equals the repo-relative path with forward slashes. No `data_platform/data_platform/` prefix. |
| Object count | 53 |
| Hash | SHA-256 lowercase hex of the full object bytes. Never use the S3 ETag. |
| Content types | `application/json` for `.json`, `application/octet-stream` for `.parquet` |
| Inventory path | `data_platform/data/bluesky/bluesky_7e2c4a91-3b5f-4d8e-a6c1-0f9b8d2e5a73/s3_migration_inventory.json` |
| Inventory shape | `{"bucket","region","dataset_id","uploaded_at","object_count","objects":[{"repo_relative_path","s3_key","bytes","sha256"}]}` with `objects` sorted by `repo_relative_path` |
| Pointer text | A file whose bytes start with `version https://git-lfs.github.com/spec/v1` is an LFS pointer and must not be uploaded |

## The 53 paths

Pipeline files (28) under `data_platform/data/bluesky/bluesky_7e2c4a91-3b5f-4d8e-a6c1-0f9b8d2e5a73/`:

- `dataset.json`
- `raw/2026_09_01-00:00:00/metadata.json`
- `raw/2026_09_01-00:00:00/date=2026-09-01/hour=NN/<hash>.parquet` for the 24 hours listed below
- `preprocessed/2026_09_03-23:51:30/metadata.json`
- `preprocessed/2026_09_03-23:51:30/posts.parquet`

Source dump files (25) under `data_platform/ingestion/data_dumps/bluesky/data/`:

- `parquet/date=2026-09-01/hour=NN/<hash>.parquet` for the same 24 hours
- `summary_statistics.json`

The 24 hourly parquet file names are identical in the raw run and the dump tree. The script stores them once as a frozen tuple of `hour=NN/<hash>.parquet` segments and builds both trees from that tuple. Take the exact segments from `git lfs ls-files | grep "data_dumps/bluesky"` at implementation time. Assert the final path list has exactly 53 entries and that every entry exists on disk before any upload.

## Contracts

`data_platform/scripts/migrate_bluesky_lfs_to_s3.py`

- Module constants: `BUCKET`, `REGION`, `DATASET_ID`, `RAW_RUN`, `PREPROCESSED_RUN`, `EXPECTED_OBJECT_COUNT = 53`, `LFS_POINTER_PREFIX`, `INVENTORY_PATH`, `LFS_INCLUDE_PATTERNS` (the two patterns from the smoke section), `HOURLY_PARQUET_SEGMENTS` (24 entries).
- `scoped_repo_relative_paths() -> list[str]` returns the 53 paths sorted.
- `run_git_lfs_pull(patterns: Sequence[str]) -> None` runs `git lfs pull --include <pattern>` once per pattern from `REPO_ROOT` and raises `subprocess.CalledProcessError` on failure.
- `read_scoped_bytes(repo_relative_path: str) -> bytes` reads the file under `REPO_ROOT` and raises `ValueError` when the bytes start with `LFS_POINTER_PREFIX`.
- `sha256_hex(data: bytes) -> str`.
- `content_type_for(repo_relative_path: str) -> str`.
- `upload_and_verify(s3: S3, repo_relative_path: str, data: bytes) -> dict` uploads to the key equal to the path, re-downloads the object, raises `RuntimeError` when the remote SHA-256 or length differs, and returns the inventory row.
- `write_inventory(rows: list[dict], path: Path) -> None` writes the JSON shape above with two-space indent and a trailing newline.
- `main() -> None` runs the caller path and prints `uploaded 53 objects to s3://mirrorview-experimental-artifacts/` as the last line.

`data_platform/scripts/verify_bluesky_s3_migration.py`

- Imports `BUCKET`, `REGION`, `EXPECTED_OBJECT_COUNT`, `INVENTORY_PATH`, and `sha256_hex` from the migration module.
- `verify_inventory(inventory: dict, s3: S3) -> list[str]` re-downloads every listed key and returns one message per mismatch or missing object. An empty list means every object matched.
- `main() -> None` loads the inventory, fails when `object_count` or `len(objects)` is not 53, prints `OK: 53/53 objects present with matching sha256` and exits 0 on success, or prints each problem and exits 1.

Both scripts use `S3(BUCKET, region_name=REGION)` from `lib/aws/s3.py` without modifying it. Neither script calls `HeadObject`, because the re-download check already covers existence, length, and content.

## Smoke checks (the executable spec)

There are no automated tests. The verify script is the executable spec, and the commands below are the acceptance run.

Given the 25 scoped parquet files are LFS pointers on disk, when `git lfs pull` runs for the two include patterns, then `posts.parquet` starts with the bytes `PAR1` and is 68,290,757 bytes.

Given the pulled files, when the migration script runs, then it uploads 53 objects, every remote SHA-256 equals the local SHA-256, the inventory has 53 sorted rows, and the last stdout line is `uploaded 53 objects to s3://mirrorview-experimental-artifacts/`.

Given the committed inventory, when the verify script runs, then it prints `OK: 53/53 objects present with matching sha256` and exits 0.

Given a scoped file that is still pointer text, when `read_scoped_bytes` reads it, then `ValueError` is raised and nothing is uploaded for that file. Check the pointer rejection by hand once with a pointer file under `/tmp`, not with a committed test.

## Ordered work

Each item is one commit.

1. Scaffold both scripts with stub bodies (`raise NotImplementedError`) and a wired `main` in each.
2. Fill in the contracts above (constants, signatures, docstrings), bodies still stubs.
3. Implement `verify_bluesky_s3_migration.py` in full. It is the executable check and fails before the migration runs because the inventory file does not exist yet.
4. Implement `scoped_repo_relative_paths` and `content_type_for`. Print the count and confirm 53.
5. Implement `run_git_lfs_pull`, `read_scoped_bytes`, and `sha256_hex`.
6. Implement `upload_and_verify`, `write_inventory`, and `main`.
7. Run the live smoke commands below and commit the inventory file.

## Live smoke commands

From the repo root. Export credentials first:

```bash
export AWS_ACCESS_KEY_ID="$LAB_AWS_ACCESS_KEY_ID"
export AWS_SECRET_ACCESS_KEY="$LAB_AWS_ACCESS_KEY_SECRET"
PYTHONPATH=. uv run python -c "import boto3; print(boto3.client('sts').get_caller_identity()['Arn'])"
```

Expected: an ARN for the lab IAM user, exit code 0. The `aws` CLI is not installed in the Cloud Agent environment, so boto3 replaces `aws sts get-caller-identity` and `aws s3api head-object` here.

```bash
git lfs pull --include "data_platform/data/bluesky/bluesky_7e2c4a91-3b5f-4d8e-a6c1-0f9b8d2e5a73/**"
git lfs pull --include "data_platform/ingestion/data_dumps/bluesky/data/parquet/**"
head -c 4 data_platform/data/bluesky/bluesky_7e2c4a91-3b5f-4d8e-a6c1-0f9b8d2e5a73/preprocessed/2026_09_03-23:51:30/posts.parquet | od -c | head -1
```

Expected: exit code 0 and the line `0000000   P   A   R   1`.

```bash
PYTHONPATH=. uv run python data_platform/scripts/migrate_bluesky_lfs_to_s3.py
```

Expected: last stdout line `uploaded 53 objects to s3://mirrorview-experimental-artifacts/`, exit code 0.

```bash
PYTHONPATH=. uv run python data_platform/scripts/verify_bluesky_s3_migration.py
```

Expected: `OK: 53/53 objects present with matching sha256`, exit code 0.

```bash
PYTHONPATH=. uv run python - <<'PY'
import boto3
s3 = boto3.client("s3", region_name="us-east-2")
for key in [
    "data_platform/data/bluesky/bluesky_7e2c4a91-3b5f-4d8e-a6c1-0f9b8d2e5a73/preprocessed/2026_09_03-23:51:30/posts.parquet",
    "data_platform/ingestion/data_dumps/bluesky/data/parquet/date=2026-09-01/hour=00/87e175daae2e2a8367e353ab2018088747e1f1deaa9b052889d9fd276297b2ef.parquet",
]:
    head = s3.head_object(Bucket="mirrorview-experimental-artifacts", Key=key)
    print(head["ResponseMetadata"]["HTTPStatusCode"], head["ContentLength"], key)
PY
```

Expected: two lines starting with `200` and a non-zero length.

```bash
git lfs ls-files | grep "bluesky_7e2c4a91" | wc -l
```

Expected: `25`.

```bash
PYTHONPATH=. uv run python - <<'PY'
import json
from pathlib import Path
inv = json.loads(Path("data_platform/data/bluesky/bluesky_7e2c4a91-3b5f-4d8e-a6c1-0f9b8d2e5a73/s3_migration_inventory.json").read_text())
assert inv["object_count"] == 53
assert len(inv["objects"]) == 53
assert inv["objects"][0]["s3_key"].startswith("data_platform/")
assert "data_platform/data_platform/" not in inv["objects"][0]["s3_key"]
print("inventory ok", inv["uploaded_at"])
PY
```

Expected: `inventory ok` plus a timestamp, exit code 0.

## Must pass

- 53 objects in S3 at repo-relative keys, none starting with `data_platform/data_platform/`.
- Every inventory row has matching local and remote SHA-256.
- The inventory file is committed under the pinned dataset directory.
- `git lfs ls-files | grep "bluesky_7e2c4a91" | wc -l` prints `25`.
- `git diff --stat origin/main -- lib/aws/s3.py data_platform/utils/storage.py .gitattributes .gitignore` prints nothing.

## Must fail

- Any script accepts an ETag as a content hash.
- Any 133-byte pointer file is uploaded.
- The object count is not 53.
- Any Reddit or non-Bluesky path appears in the inventory.
