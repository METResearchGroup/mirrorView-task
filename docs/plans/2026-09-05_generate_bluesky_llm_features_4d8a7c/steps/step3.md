# Step 3: Make S3 the default pipeline backend and remove current Bluesky LFS artifacts

## Goal

After Step 1 objects and Step 2 S3 reads are verified, make S3 the production storage backend for the data platform. Remove the pinned Bluesky parquet files from Git LFS tracking without rewriting repository history. Keep JSON manifests (`dataset.json`, run `metadata.json`, and the Step 1 migration inventory) in git as ordinary text files.

## Dependencies

- **Step 1 merged:** `s3_migration_inventory.json` exists and all 53 objects are in S3.
- **Step 2 merged:** `StorageManager` can read and write through `S3ObjectStore` with env-driven backend selection.
- AWS credentials for verification smokes.

This step does not run feature generation, does not add lifecycle rules (Step 16), and does not touch Reddit LFS.

## Main caller and implementation slice

**Main caller:** `data_platform/utils/object_store.py` `resolve_object_store`.

**Implementation slice for this PR:** change the default backend from `local` to `s3` when `DATA_PLATFORM_STORAGE_BACKEND` is unset; update `.gitattributes` and `.gitignore` so only the pinned Bluesky JSON manifests stay tracked; `git rm --cached` the 25 Bluesky parquet blobs (24 raw + 1 preprocessed) while leaving historical commits untouched; add `data_platform/data/bluesky/bluesky_7e2c4a91-3b5f-4d8e-a6c1-0f9b8d2e5a73/.gitkeep` or equivalent documentation in `dataset.json` comments is not allowed — use a short `README` only if needed under the allowed list.

## Files to inspect (read-only)

| Path | Why |
|------|-----|
| `/workspace/data_platform/utils/object_store.py` | Backend resolution from Step 2 |
| `/workspace/data_platform/utils/storage.py` | `DATA_ROOT` and manager entry points |
| `/workspace/data_platform/data/bluesky/bluesky_7e2c4a91-3b5f-4d8e-a6c1-0f9b8d2e5a73/s3_migration_inventory.json` | Post-removal verification source of truth |
| `/workspace/.gitattributes` | Bluesky and Reddit LFS rules |
| `/workspace/.gitignore` | Pinned dataset un-ignore exceptions |
| `/workspace/data_platform/scripts/verify_bluesky_s3_migration.py` | Reuse for post-cutover check |
| `/workspace/docs/runbooks/DATA_INGESTION_PIPELINE_ARCHITECTURE.md` | Document that production reads S3 (optional one-line note only if this file is explicitly added to allowed list — otherwise skip) |

## Files allowed to change

- `/workspace/data_platform/utils/object_store.py` (default backend flip only)
- `/workspace/.gitattributes` (remove Bluesky pinned-dataset parquet LFS rule only)
- `/workspace/.gitignore` (stop un-ignoring Bluesky parquet paths; keep JSON manifest exceptions)
- Git index only for:
  - removal from tracking of `data_platform/data/bluesky/bluesky_7e2c4a91-3b5f-4d8e-a6c1-0f9b8d2e5a73/raw/**/*.parquet`
  - removal from tracking of `data_platform/data/bluesky/bluesky_7e2c4a91-3b5f-4d8e-a6c1-0f9b8d2e5a73/preprocessed/**/*.parquet`
- Retain in git as normal files:
  - `data_platform/data/bluesky/bluesky_7e2c4a91-3b5f-4d8e-a6c1-0f9b8d2e5a73/dataset.json`
  - `data_platform/data/bluesky/bluesky_7e2c4a91-3b5f-4d8e-a6c1-0f9b8d2e5a73/raw/2026_09_01-00:00:00/metadata.json`
  - `data_platform/data/bluesky/bluesky_7e2c4a91-3b5f-4d8e-a6c1-0f9b8d2e5a73/preprocessed/2026_09_03-23:51:30/metadata.json`
  - `data_platform/data/bluesky/bluesky_7e2c4a91-3b5f-4d8e-a6c1-0f9b8d2e5a73/s3_migration_inventory.json`

Temporary smoke evidence under `experiments/bluesky_s3_default_backend_smoke_2026_09_05/` may be committed for review and must be deleted before merge.

## Files forbidden to change

- `/workspace/data_platform/scripts/migrate_bluesky_lfs_to_s3.py`
- `/workspace/data_platform/ingestion/data_dumps/bluesky/data/**` (dump LFS stays)
- `/workspace/data_platform/data/reddit/**`
- `/workspace/.gitattributes` lines for Reddit or dump parquet (only remove the Bluesky pipeline rule)
- `/workspace/data_platform/generate_features/**`
- `/workspace/data_platform/preprocessing/**`
- `/workspace/data_platform/ingestion/sync_bluesky.py`
- `/workspace/CHANGELOG.md`
- Any file under `/workspace/tests/`
- Any git history rewrite (`git filter-repo`, `git lfs migrate export`, force push)
- Any file outside the allowed list

## Locked contracts

| Item | Value |
|------|-------|
| Production default backend | `s3` when `DATA_PLATFORM_STORAGE_BACKEND` is unset |
| Local override | `DATA_PLATFORM_STORAGE_BACKEND=local` for development |
| Bucket | `mirrorview-experimental-artifacts` |
| Region | `us-east-2` |
| S3 key prefix | `data_platform/data/` |
| Parquet removed from git | Only under `data_platform/data/bluesky/bluesky_7e2c4a91-3b5f-4d8e-a6c1-0f9b8d2e5a73/` (25 parquet files) |
| JSON kept in git | `dataset.json`, both `metadata.json` files, `s3_migration_inventory.json` |
| Dump LFS untouched | `data_platform/ingestion/data_dumps/bluesky/data/parquet/**` remains LFS |
| Reddit LFS untouched | All `data_platform/data/reddit/**` rules and files unchanged |
| History | No force push, no LFS history rewrite, no `git filter-repo` |
| Removal mechanism | `git rm --cached` on parquet paths only; working-tree copies may remain ignored locally |
| `.gitattributes` change | Delete line `data_platform/data/bluesky/bluesky_7e2c4a91-3b5f-4d8e-a6c1-0f9b8d2e5a73/**/*.parquet filter=lfs diff=lfs merge=lfs -text` |
| Verification | `git lfs ls-files` must not list any path under the pinned Bluesky dataset after this PR |

## Ordered implementation work

1. Flip `resolve_object_store()` default to `s3` while preserving explicit `local` override.
2. Update `.gitignore` so JSON manifests under the pinned dataset remain tracked but parquet paths are ignored.
3. Remove the Bluesky pipeline LFS rule from `.gitattributes`.
4. Run `git rm --cached` for all 25 parquet files under the pinned dataset.
5. Confirm JSON manifests and inventory remain staged as normal git files.
6. Run live smokes: default-backend S3 read, migration inventory verification, and `git lfs ls-files` grep returns empty for pinned dataset.
7. Delete temporary smoke directory before merge.

## Live smoke and basic check commands

Export AWS credentials:

```bash
export AWS_ACCESS_KEY_ID="$LAB_AWS_ACCESS_KEY_ID"
export AWS_SECRET_ACCESS_KEY="$LAB_AWS_ACCESS_KEY_SECRET"
```

**Default backend is S3** — unset env var:

```bash
unset DATA_PLATFORM_STORAGE_BACKEND
PYTHONPATH=. uv run python - <<'PY'
from data_platform.utils.storage import BlueskyStorageManager, StorageStage
storage = BlueskyStorageManager(StorageStage.PREPROCESSED, "bluesky_7e2c4a91-3b5f-4d8e-a6c1-0f9b8d2e5a73")
df = storage.load_records(latest=True)
assert len(df) == 200000
print("default s3 backend ok", len(df))
PY
```

Expected stdout: `default s3 backend ok 200000` and exit code 0.

**Local override still works** for developers with LFS blobs pulled:

```bash
DATA_PLATFORM_STORAGE_BACKEND=local \
PYTHONPATH=. uv run python - <<'PY'
from data_platform.utils.storage import BlueskyStorageManager, StorageStage
from data_platform.utils.object_store import resolve_object_store
assert resolve_object_store().__class__.__name__ == "LocalObjectStore"
print("local override ok")
PY
```

Expected stdout: `local override ok`.

**Migration inventory still valid:**

```bash
PYTHONPATH=. uv run python data_platform/scripts/verify_bluesky_s3_migration.py
```

Expected stdout: `OK: 53/53 objects present with matching sha256`.

**No Bluesky pipeline parquet in LFS index:**

```bash
git lfs ls-files | grep "data_platform/data/bluesky/bluesky_7e2c4a91" || echo "no bluesky pipeline lfs"
```

Expected stdout: `no bluesky pipeline lfs`.

**JSON manifests still tracked:**

```bash
git ls-files "data_platform/data/bluesky/bluesky_7e2c4a91-3b5f-4d8e-a6c1-0f9b8d2e5a73/*.json"
git ls-files "data_platform/data/bluesky/bluesky_7e2c4a91-3b5f-4d8e-a6c1-0f9b8d2e5a73/**/metadata.json"
git ls-files "data_platform/data/bluesky/bluesky_7e2c4a91-3b5f-4d8e-a6c1-0f9b8d2e5a73/s3_migration_inventory.json"
```

Expected: paths printed for `dataset.json`, both `metadata.json` files, and `s3_migration_inventory.json`.

**Dump and Reddit LFS unchanged:**

```bash
git lfs ls-files | grep -E "data_dumps/bluesky|data/reddit" | wc -l
```

Expected: a positive count (currently 27: 24 dump parquet + 3 Reddit parquet). Exact number may vary if Reddit changes elsewhere; fail only if this count drops.

## Acceptance criteria

- Unset `DATA_PLATFORM_STORAGE_BACKEND` reads pinned preprocessed data from S3 successfully.
- Twenty-five Bluesky pipeline parquet files are no longer tracked by git or Git LFS.
- JSON manifests and `s3_migration_inventory.json` remain committed as normal files.
- Reddit LFS and Bluesky dump LFS rules are untouched.
- No git history rewrite.
- `verify_bluesky_s3_migration.py` still passes.

## Failure conditions

- Any pinned Bluesky parquet remains in `git lfs ls-files`.
- `dataset.json` or run `metadata.json` files are removed from git.
- Reddit or dump LFS rules are deleted or modified incorrectly.
- Default backend remains `local`.
- S3 keys or bucket change from locked values.
- Git history is rewritten or force-pushed.
- Pipeline code starts requiring local parquet copies in CI without documenting `DATA_PLATFORM_STORAGE_BACKEND=local` override.

## PR artifact and commit rules

- One independently mergeable PR.
- Separate commits recommended: (1) default backend flip, (2) gitignore/gitattributes and `git rm --cached`.
- Include in the PR description the explicit list of 25 removed parquet paths and confirmation that dump LFS is unchanged.
- Temporary smoke artifacts under `experiments/bluesky_s3_default_backend_smoke_2026_09_05/` may be committed for review; delete before merge.
- Do not add or run automated tests.
- Do not edit `plan.md` or other step specs.
- PR title suggestion: `Default data platform storage to S3 and drop Bluesky pipeline LFS`.
