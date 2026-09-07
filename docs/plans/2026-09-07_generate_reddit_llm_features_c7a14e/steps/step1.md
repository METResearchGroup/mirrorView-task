# Step 1: Copy the pinned Reddit preprocessed comments parquet to S3

## Goal

Upload the single pinned Reddit preprocessed comments parquet to `s3://mirrorview-experimental-artifacts/` using the exact repo-relative object key. Resolve the Git LFS pointer to real bytes before upload. Record a SHA-256 hash for the uploaded object in a committed inventory file. Leave the Git LFS pointer and tracked parquet file in the repository unchanged. Do not upload raw runs, dumps, or `dataset.json`.

## Dependencies

Pinned identities for later steps:

| Field | Value |
|-------|-------|
| Dataset id | `reddit_3d8a2c41-9b17-4e6f-a5d0-8c1b2e4f6079` |
| Pinned preprocessed run | `2026_09_03-23:39:28` |
| Preprocessed row count | `400000` |
| Campaign id (later steps) | `reddit_2026_09_03_233928_llm_features_v1` |

This step has no code dependencies on other epic steps. It may run in parallel with Step 2. It does require:

- Git LFS installed and able to smudge the pinned preprocessed parquet path.
- AWS credentials with `s3:PutObject`, `s3:GetObject`, and `s3:HeadObject` on `mirrorview-experimental-artifacts`.
- In the Cloud Agent environment, `LAB_AWS_ACCESS_KEY_ID` and `LAB_AWS_ACCESS_KEY_SECRET` exported as `AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY` before any AWS or boto3 call.
- `uv sync` if boto3 is not already available.

Do not upload Bluesky LFS objects, Reddit raw parquet, or any file outside the locked scope below.

## Main caller and implementation scope

**Main caller:** `data_platform/scripts/migrate_reddit_preprocessed_to_s3.py` `main`.

**Verifier:** `data_platform/scripts/verify_reddit_preprocessed_s3.py` `main`.

**Implementation scope for this PR:** read the one locked local path, pull LFS when needed, reject pointer text, upload to the matching S3 key, compute SHA-256 for local and remote bytes, and write `data_platform/data/reddit/reddit_3d8a2c41-9b17-4e6f-a5d0-8c1b2e4f6079/s3_preprocessed_inventory.json`. Do not change `StorageManager` or any pipeline read path in this step.

## Files to inspect (read-only)

| Path | Why |
|------|-----|
| `/workspace/data_platform/data/reddit/reddit_3d8a2c41-9b17-4e6f-a5d0-8c1b2e4f6079/dataset.json` | Dataset manifest that stays in git |
| `/workspace/data_platform/data/reddit/reddit_3d8a2c41-9b17-4e6f-a5d0-8c1b2e4f6079/preprocessed/2026_09_03-23:39:28/metadata.json` | Pinned preprocessed run metadata and row count |
| `/workspace/.gitattributes` | Reddit LFS rules for parquet under the pinned dataset |
| `/workspace/lib/aws/s3.py` | Existing `S3` helper and default region `us-east-2` |
| `/workspace/lib/constants.py` | `REPO_ROOT` |
| `/workspace/data_platform/scripts/migrate_bluesky_lfs_to_s3.py` | Reference migration pattern from the Bluesky epic |
| `/workspace/AGENTS.md` | `PYTHONPATH=.` and AWS credential export pattern |

## Files allowed to change

- `/workspace/data_platform/scripts/migrate_reddit_preprocessed_to_s3.py` (new)
- `/workspace/data_platform/scripts/verify_reddit_preprocessed_s3.py` (new, smoke verifier used by this step only)
- `/workspace/data_platform/data/reddit/reddit_3d8a2c41-9b17-4e6f-a5d0-8c1b2e4f6079/s3_preprocessed_inventory.json` (new, permanent report)

Temporary smoke evidence under `experiments/reddit_s3_preprocessed_smoke_2026_09_07/` may be committed during review and must be deleted before merge.

Do not edit files under `/workspace/docs/plans/2026-09-07_generate_reddit_llm_features_c7a14e/` during implementation except this step file when correcting the spec.

## Files forbidden to change

- `/workspace/data_platform/utils/storage.py`
- `/workspace/lib/aws/s3.py` (reuse as-is; extend only if the migration script cannot call it without modification; prefer wrapping in the new script)
- `/workspace/.gitattributes`
- `/workspace/.gitignore`
- `/workspace/data_platform/data/reddit/reddit_3d8a2c41-9b17-4e6f-a5d0-8c1b2e4f6079/dataset.json`
- `/workspace/data_platform/data/reddit/reddit_3d8a2c41-9b17-4e6f-a5d0-8c1b2e4f6079/raw/**`
- `/workspace/data_platform/data/reddit/reddit_3d8a2c41-9b17-4e6f-a5d0-8c1b2e4f6079/preprocessed/**` (do not rewrite the local parquet or metadata)
- `/workspace/data_platform/data/bluesky/**`
- `/workspace/data_platform/ingestion/data_dumps/**`
- `/workspace/CHANGELOG.md`
- Any test file under `/workspace/tests/`
- Any file outside the allowed list

## Locked contracts

| Item | Value |
|------|-------|
| S3 bucket | `mirrorview-experimental-artifacts` |
| AWS region | `us-east-2` |
| Dataset id | `reddit_3d8a2c41-9b17-4e6f-a5d0-8c1b2e4f6079` |
| Pinned preprocessed run | `2026_09_03-23:39:28` |
| Pipeline S3 prefix | `data_platform/data/` (no duplicated `data_platform` segment in keys) |
| Key rule | Repo-relative path with forward slashes. Local `data_platform/data/reddit/.../comments.parquet` maps to the same key under the bucket |
| Upload scope | `data_platform/data/reddit/reddit_3d8a2c41-9b17-4e6f-a5d0-8c1b2e4f6079/preprocessed/2026_09_03-23:39:28/comments.parquet` only |
| Expected object count | `1` |
| Hash algorithm | SHA-256 lowercase hex of full object bytes. Never use S3 ETag as a content hash. |
| LFS retention | Do not `git rm`, rewrite history, or replace the parquet pointer in git |
| Inventory path | `data_platform/data/reddit/reddit_3d8a2c41-9b17-4e6f-a5d0-8c1b2e4f6079/s3_preprocessed_inventory.json` |
| Inventory JSON shape | `{"bucket":"mirrorview-experimental-artifacts","region":"us-east-2","dataset_id":"reddit_3d8a2c41-9b17-4e6f-a5d0-8c1b2e4f6079","preprocessed_run":"2026_09_03-23:39:28","uploaded_at":"<UTC from lib.timestamp_utils.get_current_timestamp>","object_count":1,"objects":[{"repo_relative_path":"...","s3_key":"...","bytes":N,"sha256":"..."}]}` |
| Pointer rejection | If the scoped file still begins with `version https://git-lfs.github.com/spec/v1`, abort the upload for that file after `git lfs pull` for the scoped include path |
| Excluded paths | `dataset.json` (already in git), all `raw/**`, all dump paths, all Bluesky paths |

Primary S3 object after upload:

`s3://mirrorview-experimental-artifacts/data_platform/data/reddit/reddit_3d8a2c41-9b17-4e6f-a5d0-8c1b2e4f6079/preprocessed/2026_09_03-23:39:28/comments.parquet`

## Ordered implementation work

1. Add `migrate_reddit_preprocessed_to_s3.py` with the single frozen repo-relative path above.
2. Before upload, run `git lfs pull` for `data_platform/data/reddit/reddit_3d8a2c41-9b17-4e6f-a5d0-8c1b2e4f6079/preprocessed/2026_09_03-23:39:28/comments.parquet`.
3. Read bytes from disk, reject LFS pointer text, compute SHA-256, upload with `Content-Type` `application/octet-stream`.
4. After upload, `HeadObject` and optionally re-download to confirm the remote SHA-256 matches local.
5. Write the inventory JSON under the pinned dataset directory.
6. Add `verify_reddit_preprocessed_s3.py` that reads the inventory and checks the listed key exists with matching SHA-256 (re-download and hash bytes; never accept ETag as a content hash).
7. Run the live smoke commands below. Commit the scripts and permanent inventory. Delete any temporary smoke directory before merge.

## Live smoke and basic check commands

From the repo root. Export AWS credentials first:

```bash
export AWS_ACCESS_KEY_ID="$LAB_AWS_ACCESS_KEY_ID"
export AWS_SECRET_ACCESS_KEY="$LAB_AWS_ACCESS_KEY_SECRET"
aws sts get-caller-identity
```

Expected: JSON with `"Arn"` containing the lab IAM user and exit code 0.

Pull LFS blob for the scoped path:

```bash
git lfs pull --include "data_platform/data/reddit/reddit_3d8a2c41-9b17-4e6f-a5d0-8c1b2e4f6079/preprocessed/2026_09_03-23:39:28/comments.parquet"
```

Expected: exit code 0. The file is larger than 200 bytes and is not an LFS pointer:

```bash
python3 -c "
from pathlib import Path
p = Path('data_platform/data/reddit/reddit_3d8a2c41-9b17-4e6f-a5d0-8c1b2e4f6079/preprocessed/2026_09_03-23:39:28/comments.parquet')
head = p.read_bytes()[:4]
assert head == b'PAR1', head
print('parquet magic ok', p.stat().st_size)
"
```

Expected: `parquet magic ok` plus a byte size well above 200.

Run the migration:

```bash
PYTHONPATH=. uv run python data_platform/scripts/migrate_reddit_preprocessed_to_s3.py
```

Expected stdout ends with a line like `uploaded 1 object to s3://mirrorview-experimental-artifacts/` and exit code 0.

Verify with the companion script:

```bash
PYTHONPATH=. uv run python data_platform/scripts/verify_reddit_preprocessed_s3.py
```

Expected stdout: `OK: 1/1 objects present with matching sha256` and exit code 0.

Spot-check the object with the AWS CLI:

```bash
aws s3api head-object \
  --bucket mirrorview-experimental-artifacts \
  --key data_platform/data/reddit/reddit_3d8a2c41-9b17-4e6f-a5d0-8c1b2e4f6079/preprocessed/2026_09_03-23:39:28/comments.parquet \
  --region us-east-2
```

Expected: HTTP 200 metadata with non-zero `ContentLength`.

Confirm LFS pointer remains in git:

```bash
git lfs ls-files | grep "reddit_3d8a2c41" | grep "comments.parquet"
```

Expected: one line for the preprocessed comments parquet.

Confirm inventory committed:

```bash
PYTHONPATH=. uv run python - <<'PY'
import json
from pathlib import Path
inv = json.loads(Path("data_platform/data/reddit/reddit_3d8a2c41-9b17-4e6f-a5d0-8c1b2e4f6079/s3_preprocessed_inventory.json").read_text())
assert inv["object_count"] == 1
assert len(inv["objects"]) == 1
assert inv["objects"][0]["s3_key"].startswith("data_platform/")
assert "data_platform/data_platform/" not in inv["objects"][0]["s3_key"]
assert inv["preprocessed_run"] == "2026_09_03-23:39:28"
print("inventory ok", inv["uploaded_at"])
PY
```

Expected: `inventory ok` plus timestamp and exit code 0.

## Acceptance criteria

- The scoped object exists in `mirrorview-experimental-artifacts` at the repo-relative key with no duplicated `data_platform` prefix.
- The inventory row has a matching local and remote SHA-256.
- `s3_preprocessed_inventory.json` is committed under the pinned dataset directory.
- The preprocessed comments parquet remains a Git LFS pointer in the working tree.
- No Bluesky or unrelated LFS paths were uploaded.
- No pipeline storage code changed.

## Failure conditions

- Verification accepts ETag instead of SHA-256 for the object.
- The scoped file uploads as an LFS pointer (133-byte text file).
- Object count is not exactly 1.
- The S3 key starts with `data_platform/data_platform/`.
- Bluesky paths, Reddit raw paths, or `dataset.json` appear in the inventory.
- Git LFS pointer for the pinned preprocessed parquet is removed or rewritten.
- `StorageManager` or default pipeline read behavior changes in this PR.
- Any automated test file is added or run.

## PR artifact and commit rules

- One independently mergeable PR for this step only.
- Commit the migration scripts and permanent `s3_preprocessed_inventory.json` in logical commits (script first, inventory after successful upload).
- Temporary smoke logs or sample downloads under `experiments/reddit_s3_preprocessed_smoke_2026_09_07/` may be committed for review; delete that directory in the final commit before merge.
- Do not add or run automated tests.
- Do not edit other step specs in the implementation PR.
- PR title suggestion: `Copy pinned Reddit preprocessed comments parquet to S3 with hash inventory`.

## GitHub issue body

Upload the pinned Reddit preprocessed comments parquet (`400000` rows, run `2026_09_03-23:39:28`) to `mirrorview-experimental-artifacts` so later campaign steps can read input from S3. Add migration and verify scripts, keep Git LFS unchanged, and commit `s3_preprocessed_inventory.json` with SHA-256 for the single object.

Plan step: `docs/plans/2026-09-07_generate_reddit_llm_features_c7a14e/steps/step1.md`

Done when:

- `comments.parquet` is on S3 at the repo-relative key with matching SHA-256 in the inventory.
- Git still tracks the parquet as LFS; no Bluesky or raw Reddit paths were uploaded.
- Smoke commands in the step file pass.

## Pull request description

# Copy pinned Reddit preprocessed comments parquet to S3

Fixes #<child>

Part of #<parent>

## Problem

The Reddit LLM feature campaign labels `400000` preprocessed comments from run `2026_09_03-23:39:28`, but that parquet lives only in Git LFS today. Campaign workers need the same bytes on `mirrorview-experimental-artifacts` without removing LFS from the repository.

## Solution

Add `migrate_reddit_preprocessed_to_s3.py` to upload the single pinned `comments.parquet` object and `verify_reddit_preprocessed_s3.py` to confirm the remote bytes match a local SHA-256. Commit `s3_preprocessed_inventory.json` under the pinned dataset directory. No pipeline read path changes.

## Purpose

Step 2 and Step 3 depend on S3-hosted preprocessed input. This PR limits upload scope to one parquet file so the migration stays small and reviewable. Changing `StorageManager`, uploading raw dumps, or touching Bluesky data is out of scope.

## How to run

```bash
export AWS_ACCESS_KEY_ID="$LAB_AWS_ACCESS_KEY_ID"
export AWS_SECRET_ACCESS_KEY="$LAB_AWS_ACCESS_KEY_SECRET"
git lfs pull --include "data_platform/data/reddit/reddit_3d8a2c41-9b17-4e6f-a5d0-8c1b2e4f6079/preprocessed/2026_09_03-23:39:28/comments.parquet"
PYTHONPATH=. uv run python data_platform/scripts/migrate_reddit_preprocessed_to_s3.py
PYTHONPATH=. uv run python data_platform/scripts/verify_reddit_preprocessed_s3.py
```

Expected: migration reports `uploaded 1 object`, verifier prints `OK: 1/1 objects present with matching sha256`, and `s3_preprocessed_inventory.json` lists one object with a 64-character SHA-256 hex digest.
