# Step 1: Copy current pipeline LFS artifacts to S3

## Goal

Upload every pinned Bluesky pipeline artifact and every required Bluesky source dump to `s3://mirrorview-experimental-artifacts/` using exact repo-relative object keys. Resolve Git LFS pointers to real bytes before upload. Record a SHA-256 hash for every uploaded object in a committed migration inventory. Leave all Git LFS pointers and tracked parquet files in the repository unchanged.

## Dependencies

See `docs/plans/2026-09-05_generate_bluesky_llm_features_4d8a7c/campaign_contract.md` for pinned identities used by later steps.

This step has no code dependencies on other epic steps. It may run in parallel with Steps 2 and 4. It does require:

- Git LFS installed and able to smudge the pinned Bluesky paths.
- AWS credentials with `s3:PutObject`, `s3:GetObject`, and `s3:HeadObject` on `mirrorview-experimental-artifacts`.
- In the Cloud Agent environment, `LAB_AWS_ACCESS_KEY_ID` and `LAB_AWS_ACCESS_KEY_SECRET` exported as `AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY` before any AWS or boto3 call.
- `uv sync` if boto3 is not already available.

Do not upload Reddit LFS objects, unrelated dump paths, or any file outside the locked scope below.

## Main caller and implementation slice

**Main caller:** `data_platform/scripts/migrate_bluesky_lfs_to_s3.py` `main`.

**Implementation slice for this PR:** enumerate the locked local paths, resolve each file to real bytes (pull LFS when needed), upload to the matching S3 key, compute SHA-256 for local and remote bytes, and write `data_platform/data/bluesky/bluesky_7e2c4a91-3b5f-4d8e-a6c1-0f9b8d2e5a73/s3_migration_inventory.json`. Do not change `StorageManager` or any pipeline read path in this step.

## Files to inspect (read-only)

| Path | Why |
|------|-----|
| `/workspace/docs/plans/2026-09-05_generate_bluesky_llm_features_4d8a7c/plan.md` | Locked dataset id, bucket, and pipeline root |
| `/workspace/.gitattributes` | Bluesky LFS rules for pipeline and dump parquet |
| `/workspace/.gitignore` | Pinned Bluesky dataset un-ignore rules |
| `/workspace/data_platform/data/bluesky/bluesky_7e2c4a91-3b5f-4d8e-a6c1-0f9b8d2e5a73/dataset.json` | Dataset manifest that stays in git |
| `/workspace/data_platform/data/bluesky/bluesky_7e2c4a91-3b5f-4d8e-a6c1-0f9b8d2e5a73/raw/2026_09_01-00:00:00/metadata.json` | Raw run metadata |
| `/workspace/data_platform/data/bluesky/bluesky_7e2c4a91-3b5f-4d8e-a6c1-0f9b8d2e5a73/preprocessed/2026_09_03-23:51:30/metadata.json` | Pinned preprocessed run metadata |
| `/workspace/data_platform/ingestion/data_dumps/bluesky/data/summary_statistics.json` | Dump summary metadata |
| `/workspace/lib/aws/s3.py` | Existing `S3` helper and default region `us-east-2` |
| `/workspace/lib/constants.py` | `REPO_ROOT` |
| `/workspace/data_platform/ingestion/data_dumps/bluesky/publish_dump_to_raw.py` | Locked dataset id and raw run timestamp |
| `/workspace/AGENTS.md` | `PYTHONPATH=.` and AWS credential export pattern |

## Files allowed to change

- `/workspace/data_platform/scripts/migrate_bluesky_lfs_to_s3.py` (new)
- `/workspace/data_platform/scripts/verify_bluesky_s3_migration.py` (new, smoke verifier used by this step only)
- `/workspace/data_platform/data/bluesky/bluesky_7e2c4a91-3b5f-4d8e-a6c1-0f9b8d2e5a73/s3_migration_inventory.json` (new, permanent report)

Temporary smoke evidence under `experiments/bluesky_s3_migration_smoke_2026_09_05/` may be committed during review and must be deleted before merge.

Do not edit files under `/workspace/docs/plans/2026-09-05_generate_bluesky_llm_features_4d8a7c/` during implementation.

## Files forbidden to change

- `/workspace/data_platform/utils/storage.py`
- `/workspace/lib/aws/s3.py` (reuse as-is; extend only if the migration script cannot call it without modification; prefer wrapping in the new script)
- `/workspace/.gitattributes`
- `/workspace/.gitignore`
- `/workspace/data_platform/data/bluesky/bluesky_7e2c4a91-3b5f-4d8e-a6c1-0f9b8d2e5a73/dataset.json`
- `/workspace/data_platform/data/bluesky/bluesky_7e2c4a91-3b5f-4d8e-a6c1-0f9b8d2e5a73/raw/**`
- `/workspace/data_platform/data/bluesky/bluesky_7e2c4a91-3b5f-4d8e-a6c1-0f9b8d2e5a73/preprocessed/**`
- `/workspace/data_platform/ingestion/data_dumps/bluesky/data/**`
- `/workspace/data_platform/data/reddit/**`
- `/workspace/CHANGELOG.md`
- Any test file under `/workspace/tests/`
- Any file outside the allowed list

## Locked contracts

| Item | Value |
|------|-------|
| S3 bucket | `mirrorview-experimental-artifacts` |
| AWS region | `us-east-2` |
| Dataset id | `bluesky_7e2c4a91-3b5f-4d8e-a6c1-0f9b8d2e5a73` |
| Pinned raw run | `2026_09_01-00:00:00` |
| Pinned preprocessed run | `2026_09_03-23:51:30` |
| Pipeline S3 prefix | `data_platform/data/` (no duplicated `data_platform` segment in keys) |
| Key rule | Repo-relative path with forward slashes. Example: local `data_platform/data/bluesky/.../posts.parquet` → key `data_platform/data/bluesky/.../posts.parquet` |
| Dump key rule | Repo-relative path. Example: local `data_platform/ingestion/data_dumps/bluesky/data/parquet/date=2026-09-01/hour=00/{hash}.parquet` → same key under the bucket |
| Upload scope . pipeline | `data_platform/data/bluesky/bluesky_7e2c4a91-3b5f-4d8e-a6c1-0f9b8d2e5a73/dataset.json`, `raw/2026_09_01-00:00:00/metadata.json`, all `raw/2026_09_01-00:00:00/date=2026-09-01/hour=*/**.parquet` (24 files), `preprocessed/2026_09_03-23:51:30/metadata.json`, `preprocessed/2026_09_03-23:51:30/posts.parquet` |
| Upload scope . source dumps | `data_platform/ingestion/data_dumps/bluesky/data/parquet/date=2026-09-01/hour=*/**.parquet` (24 files) and `data_platform/ingestion/data_dumps/bluesky/data/summary_statistics.json` |
| Expected object count | 53 (28 pipeline files + 25 dump files; raw and dump parquet share LFS oids but are separate S3 keys) |
| Hash algorithm | SHA-256 lowercase hex of full object bytes. Never use S3 ETag as a content hash. |
| LFS retention | Do not `git rm`, rewrite history, or replace parquet pointers in git |
| Inventory path | `data_platform/data/bluesky/bluesky_7e2c4a91-3b5f-4d8e-a6c1-0f9b8d2e5a73/s3_migration_inventory.json` |
| Inventory JSON shape | `{"bucket":"mirrorview-experimental-artifacts","region":"us-east-2","dataset_id":"bluesky_7e2c4a91-3b5f-4d8e-a6c1-0f9b8d2e5a73","uploaded_at":"<UTC from lib.timestamp_utils.get_current_timestamp>","object_count":53,"objects":[{"repo_relative_path":"...","s3_key":"...","bytes":N,"sha256":"..."}]}` sorted by `repo_relative_path` |
| Pointer rejection | If a scoped file still begins with `version https://git-lfs.github.com/spec/v1`, abort the upload for that file after `git lfs pull` for the scoped include paths |

## Ordered implementation work

1. Add `migrate_bluesky_lfs_to_s3.py` with a frozen list of the 53 repo-relative paths above.
2. Before upload, run `git lfs pull` for `data_platform/data/bluesky/bluesky_7e2c4a91-3b5f-4d8e-a6c1-0f9b8d2e5a73/**` and `data_platform/ingestion/data_dumps/bluesky/data/parquet/**`.
3. For each path, read bytes from disk, reject LFS pointer text, compute SHA-256, upload with `Content-Type` `application/json` for `.json` and `application/octet-stream` for `.parquet`.
4. After each upload, `HeadObject` and optionally re-download to confirm the remote SHA-256 matches local.
5. Write the inventory JSON under the pinned dataset directory.
6. Add `verify_bluesky_s3_migration.py` that reads the inventory and checks every listed key exists with matching SHA-256 (re-download and hash bytes; never accept ETag as a content hash).
7. Run the live smoke commands below. Commit the scripts and permanent inventory. Delete any temporary smoke directory before merge.

## Live smoke and basic check commands

From the repo root. Export AWS credentials first:

```bash
export AWS_ACCESS_KEY_ID="$LAB_AWS_ACCESS_KEY_ID"
export AWS_SECRET_ACCESS_KEY="$LAB_AWS_ACCESS_KEY_SECRET"
aws sts get-caller-identity
```

Expected: JSON with `"Arn"` containing the lab IAM user and exit code 0.

Pull LFS blobs for scoped paths:

```bash
git lfs pull --include "data_platform/data/bluesky/bluesky_7e2c4a91-3b5f-4d8e-a6c1-0f9b8d2e5a73/**"
git lfs pull --include "data_platform/ingestion/data_dumps/bluesky/data/parquet/**"
```

Expected: exit code 0. A spot-check file is larger than 200 bytes and is not an LFS pointer:

```bash
head -c 40 data_platform/data/bluesky/bluesky_7e2c4a91-3b5f-4d8e-a6c1-0f9b8d2e5a73/preprocessed/2026_09_03-23:51:30/posts.parquet | xxd | head -1
```

Expected: bytes `PAR1` magic at the start (parquet), not the ASCII text `version https://git-lfs`.

Run the migration:

```bash
PYTHONPATH=. uv run python data_platform/scripts/migrate_bluesky_lfs_to_s3.py
```

Expected stdout ends with a line like `uploaded 53 objects to s3://mirrorview-experimental-artifacts/` and exit code 0.

Verify with the companion script:

```bash
PYTHONPATH=. uv run python data_platform/scripts/verify_bluesky_s3_migration.py
```

Expected stdout: `OK: 53/53 objects present with matching sha256` and exit code 0.

Spot-check one pipeline key and one dump key with the AWS CLI:

```bash
aws s3api head-object \
  --bucket mirrorview-experimental-artifacts \
  --key data_platform/data/bluesky/bluesky_7e2c4a91-3b5f-4d8e-a6c1-0f9b8d2e5a73/preprocessed/2026_09_03-23:51:30/posts.parquet \
  --region us-east-2

aws s3api head-object \
  --bucket mirrorview-experimental-artifacts \
  --key data_platform/ingestion/data_dumps/bluesky/data/parquet/date=2026-09-01/hour=00/87e175daae2e2a8367e353ab2018088747e1f1deaa9b052889d9fd276297b2ef.parquet \
  --region us-east-2
```

Expected: both return HTTP 200 metadata with non-zero `ContentLength`.

Confirm LFS pointers remain in git:

```bash
git lfs ls-files | grep "bluesky_7e2c4a91" | wc -l
```

Expected: `25` (24 raw parquet + 1 preprocessed parquet under the pinned dataset).

Confirm inventory committed:

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

Expected: `inventory ok` plus timestamp and exit code 0.

## Acceptance criteria

- All 53 scoped objects exist in `mirrorview-experimental-artifacts` at repo-relative keys with no duplicated `data_platform` prefix.
- Every inventory row has a matching local and remote SHA-256.
- `s3_migration_inventory.json` is committed under the pinned dataset directory.
- All Bluesky parquet files remain Git LFS pointers in the working tree; no Reddit or unrelated LFS paths were uploaded.
- No pipeline storage code changed.

## Failure conditions

- Verification accepts ETag instead of SHA-256 for any object.
- Any scoped file uploads as an LFS pointer (133-byte text file).
- Object count is not exactly 53.
- Any S3 key starts with `data_platform/data_platform/`.
- Reddit paths or non-Bluesky LFS files appear in the inventory.
- Git LFS pointers for the pinned Bluesky dataset are removed or rewritten.
- `StorageManager` or default pipeline read behavior changes in this PR.

## PR artifact and commit rules

- One independently mergeable PR for this step only.
- Commit the migration scripts and permanent `s3_migration_inventory.json` in logical commits (script first, inventory after successful upload).
- Temporary smoke logs or sample downloads under `experiments/bluesky_s3_migration_smoke_2026_09_05/` may be committed for review; delete that directory in the final commit before merge.
- Do not add or run automated tests.
- Do not edit `plan.md` or other step specs in the implementation PR.
- PR title suggestion: `Copy pinned Bluesky LFS artifacts to S3 with hash inventory`.
