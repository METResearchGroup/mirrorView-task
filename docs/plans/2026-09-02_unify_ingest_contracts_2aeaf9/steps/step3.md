# Step 3: Store repo-relative ingest config paths in manifests

## Goal

`build_base_sync_metadata` writes `ingestion_config` as `config_path.name` (basename). `ensure_dataset_manifest` already writes `config_path.relative_to(REPO_ROOT)`. Two configs named `mirrorview.yaml` on different platforms then look identical in run metadata.

## Caller / unit of work

**Main caller:** `data_platform/ingestion/sync_checkpoint.py` → `build_base_sync_metadata` and `ensure_dataset_manifest`.

**Slice:** new runs stamp the same repo-relative POSIX path in run `metadata.json` and `dataset.json`.

**Out of scope:** Migrating existing on-disk metadata. Output format. YAML key renames.

## Decision (locked)

- Helper `ingestion_config_repo_path(config_path: Path) -> str` in `sync_checkpoint.py`: `config_path.resolve().relative_to(REPO_ROOT).as_posix()`. Raise `ValueError` if the file is outside the repo.
- `build_base_sync_metadata` uses that helper instead of `config_path.name`.
- `ensure_dataset_manifest` uses the same helper (replace the inline `relative_to`).
- Do not rewrite old run directories. Resume continues to accept whatever string is already in metadata.

## Files to inspect (read-only)

| Path | Why |
|------|-----|
| `data_platform/ingestion/sync_checkpoint.py` | `build_base_sync_metadata` `ingestion_config`; `ensure_dataset_manifest` |
| `data_platform/utils/dataset.py` | Manifest schema `ingestion_config` |
| `lib/constants.py` | `REPO_ROOT` |
| `tests/data_platform/ingestion/test_sync_checkpoint.py` | Metadata builder tests |
| `tests/data_platform/utils/test_dataset.py` | Manifest writer already uses repo-relative examples |

## Files allowed to change

- `data_platform/ingestion/sync_checkpoint.py`
- `tests/data_platform/ingestion/test_sync_checkpoint.py`
- `CHANGELOG.md`

## Files forbidden to change

- Platform `sync_*.py` except via the shared helper they already call
- `data_platform/utils/dataset.py` unless a test-only import is required (prefer not)
- YAML configs
- Preprocess / features / curate

## Contracts

```text
ingestion_config_repo_path(config_path: Path) -> str
  POSIX path relative to REPO_ROOT, e.g.
  "data_platform/ingestion/configs/bluesky/mirrorview.yaml"
  Raise ValueError if config_path.resolve() is not inside REPO_ROOT.

build_base_sync_metadata[...]["ingestion_config"] == ingestion_config_repo_path(config_path)
ensure_dataset_manifest passes the same string to write_dataset_manifest(..., ingestion_config=...)
```

## Tests (write first)

`TestIngestionConfigRepoPath` and update `TestBuildBaseSyncMetadata` (or equivalent) so expected `ingestion_config` is the relative path, not the basename.

- given a path under repo `data_platform/ingestion/configs/twitter/default.yaml`, result is that POSIX relative string.
- given `/tmp/outside.yaml`, `ValueError`.

If existing checkpoint tests assert `config_path.name`, change the expected value to the relative path.

## Must pass

```bash
PYTHONPATH=. uv run pytest tests/data_platform/ingestion/test_sync_checkpoint.py tests/data_platform/utils/test_dataset.py -q
```

Exit 0.

## Must not happen

- Storing absolute paths.
- Backslashes in the stored string.
- Requiring operators to rewrite old `metadata.json`.
