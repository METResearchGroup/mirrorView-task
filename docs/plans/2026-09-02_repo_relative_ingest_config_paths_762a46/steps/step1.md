# Step 1: Share one repo-relative path helper

## Goal

Store the ingest YAML location as one repo-relative POSIX path in both run metadata and the dataset manifest. Add one shared helper and point both writers at it.

## Caller / unit of work

**Main caller:** `data_platform/ingestion/sync_checkpoint.py` `build_base_sync_metadata`, which writes `ingestion_config` into new-run metadata. `ensure_dataset_manifest` is the second writer of the same field.

**Task:** convert an absolute config path under the repo into a POSIX string relative to the repo root, then write that string from both callers.

**Out of scope:** YAML key renames. Twitter record-type checks. Bluesky `author_filter`. Package-relative helpers in `data_platform/utils/paths.py`. Sibling epic children. `CHANGELOG.md` during implementation.

## Decision (locked)

Do not reuse `to_package_relative` in `/workspace/data_platform/utils/paths.py`. The package helper is relative to `PACKAGE_ROOT`, so it would store `ingestion/configs/bluesky/mirrorview.yaml` instead of `data_platform/ingestion/configs/bluesky/mirrorview.yaml`. Existing manifests and `/workspace/tests/data_platform/utils/test_dataset.py` already use the repo-relative form that includes `data_platform/`.

Do not add a generic "relative to any root" helper, a new module, a Path subclass, or a custom exception type.

Put the helper in `/workspace/data_platform/utils/config_paths.py` next to `resolve_config_path`. `resolve_config_path` already turns a config argument into an absolute path using a repo-root base directory. The new helper is the reverse conversion for stored metadata.

Name the function `to_repo_relative`. Take the path and the repo root as arguments, matching `resolve_config_path(config, base_dir)` in the same file. Callers pass `REPO_ROOT` from `/workspace/lib/constants.py`. Raise `ValueError`, matching `to_package_relative`.

Use `.as_posix()` so the stored string uses forward slashes on every platform.

## Files to inspect (read-only)

| Path | Why |
|------|-----|
| `/workspace/docs/plans/2026-09-02_repo_relative_ingest_config_paths_762a46/plan.md` | Parent plan |
| `/workspace/data_platform/ingestion/sync_checkpoint.py` | `build_base_sync_metadata` uses `config_path.name`. `ensure_dataset_manifest` uses `str(config_path.relative_to(REPO_ROOT))`. |
| `/workspace/data_platform/utils/config_paths.py` | Home for `resolve_config_path`. Add the helper here. |
| `/workspace/data_platform/utils/paths.py` | `to_package_relative` is the rejection and POSIX style to copy, not the helper to call. |
| `/workspace/data_platform/utils/dataset.py` | `write_dataset_manifest` stores the `ingestion_config` string it is given. Do not change its signature. |
| `/workspace/lib/constants.py` | `REPO_ROOT` |
| `/workspace/tests/data_platform/ingestion/test_sync_checkpoint.py` | Caller tests for metadata and manifest writers |
| `/workspace/tests/data_platform/utils/test_dataset.py` | Persist the helper output through `write_dataset_manifest` |
| `/workspace/tests/data_platform/utils/test_config_paths.py` | Helper unit tests |
| `/workspace/tests/data_platform/conftest.py` | `data_root` fixture |
| `/workspace/data_platform/ingestion/configs/bluesky/mirrorview.yaml` | Same basename as the Twitter and Reddit files |
| `/workspace/data_platform/ingestion/configs/twitter/mirrorview.yaml` | Same basename, different platform directory |

## Files allowed to change

- `/workspace/data_platform/utils/config_paths.py`
- `/workspace/data_platform/ingestion/sync_checkpoint.py`
- `/workspace/tests/data_platform/utils/test_config_paths.py`
- `/workspace/tests/data_platform/ingestion/test_sync_checkpoint.py`
- `/workspace/tests/data_platform/utils/test_dataset.py`

Plan files under `/workspace/docs/plans/2026-09-02_repo_relative_ingest_config_paths_762a46/` are already committed on this branch. Do not rewrite them during implementation.

## Files forbidden to change

- `/workspace/data_platform/utils/paths.py`
- `/workspace/data_platform/utils/dataset.py`
- `/workspace/data_platform/ingestion/sync_bluesky.py`
- `/workspace/data_platform/ingestion/sync_reddit.py`
- `/workspace/data_platform/ingestion/sync_twitter.py`
- `/workspace/data_platform/ingestion/configs/**`
- `/workspace/CHANGELOG.md` during implementation
- Any file outside the allowed list, except git commits of this work

## Contracts to lock

`/workspace/data_platform/utils/config_paths.py`:

```text
to_repo_relative(path: str | Path, repo_root: Path) -> str
  Convert an absolute path under repo_root into a POSIX string relative to repo_root
  (forward slashes, no leading slash).
  The target file does not need to exist.
  Raise ValueError if path is not absolute.
  Raise ValueError if the resolved path is not inside repo_root.
  to_repo_relative(repo_root, repo_root) returns ".".
```

Call sites in `/workspace/data_platform/ingestion/sync_checkpoint.py`:

```text
build_base_sync_metadata
  metadata["ingestion_config"] = to_repo_relative(config_path, REPO_ROOT)

ensure_dataset_manifest
  write_dataset_manifest(..., ingestion_config=to_repo_relative(config_path, REPO_ROOT), ...)
```

Do not keep `config_path.name` in run metadata. Do not keep `str(config_path.relative_to(REPO_ROOT))` at the manifest writer.

Do not rename the `ingestion_config` JSON key. Do not change other metadata fields.

## Test design

Pseudocode then real tests. One test class per new or changed public function. Follow `/workspace/.cursor/skills/implement-plan-and-open-pr/UNIT_TESTING_STANDARDS.md`. Prefer `pytest.raises(ValueError)`. Use `result` and `expected`.

Helper tests in `/workspace/tests/data_platform/utils/test_config_paths.py`, class `TestToRepoRelative`.

Caller tests in `/workspace/tests/data_platform/ingestion/test_sync_checkpoint.py`, classes `TestBuildBaseSyncMetadata` and `TestEnsureDatasetManifest`. Update the existing `test_build_base_sync_metadata_includes_tasks` so it passes an absolute config path under `REPO_ROOT`.

Dataset tests in `/workspace/tests/data_platform/utils/test_dataset.py`: persist the helper's output through `write_dataset_manifest` and assert the stored `ingestion_config` string.

```text
given absolute_path = tmp_repo / "data_platform/ingestion/configs/bluesky/mirrorview.yaml"
and repo_root = tmp_repo
when to_repo_relative(absolute_path, repo_root)
then result == "data_platform/ingestion/configs/bluesky/mirrorview.yaml"
and result has no backslash
and result does not start with "/"

given bluesky = REPO_ROOT / "data_platform/ingestion/configs/bluesky/mirrorview.yaml"
and twitter = REPO_ROOT / "data_platform/ingestion/configs/twitter/mirrorview.yaml"
when to_repo_relative(bluesky, REPO_ROOT) and to_repo_relative(twitter, REPO_ROOT)
then the two results differ
and both end with "mirrorview.yaml"

given repo_root itself as path
when to_repo_relative(repo_root, repo_root)
then result == "."

given relative string "data_platform/ingestion/configs/bluesky/mirrorview.yaml"
when to_repo_relative(relative, repo_root)
then raise ValueError

given absolute_path outside repo_root
when to_repo_relative(outside, repo_root)
then raise ValueError

given an absolute bluesky mirrorview.yaml under REPO_ROOT
when build_base_sync_metadata(..., config_path, ...)
then metadata["ingestion_config"] == "data_platform/ingestion/configs/bluesky/mirrorview.yaml"

given the same basename on the Twitter config
when build_base_sync_metadata(..., twitter_config_path, ...)
then metadata["ingestion_config"] == "data_platform/ingestion/configs/twitter/mirrorview.yaml"
and that value is not equal to the Bluesky value

given data_root and a missing dataset.json
when ensure_dataset_manifest(..., bluesky config_path)
then load_dataset_manifest stores ingestion_config
     "data_platform/ingestion/configs/bluesky/mirrorview.yaml"

given write_dataset_manifest with to_repo_relative output for the Bluesky config
when load_dataset_manifest
then loaded["ingestion_config"] equals that POSIX repo-relative string
```

## Implementation notes

Follow implement-from-spec phases in this packet. One Git commit per phase and per unit of work. Full auto. Do not stop for contract approval.

Phase 2 scaffold: add `to_repo_relative` with `raise NotImplementedError`. Do not change the two writers yet.

Phase 3 contracts: signature and numpy docstring only. Body stays a stub.

Phase 4: write the failing tests from the scenarios above. Update the existing `test_build_base_sync_metadata_includes_tasks` to pass an absolute path under `REPO_ROOT` so it still exercises the public function after the writers change.

Phase 5 units of work, in this order:

1. `to_repo_relative` in `/workspace/data_platform/utils/config_paths.py`
2. `build_base_sync_metadata` writes `to_repo_relative(config_path, REPO_ROOT)`
3. `ensure_dataset_manifest` writes `to_repo_relative(config_path, REPO_ROOT)`

Numpy-style docstring on `to_repo_relative`. Keep the existing module docstring on `config_paths.py`.

## Must pass

```bash
cd /workspace
PYTHONPATH=. uv run pytest tests/data_platform/ingestion/test_sync_checkpoint.py tests/data_platform/utils/test_dataset.py -q
```

Expected: exit 0.

```bash
cd /workspace
PYTHONPATH=. uv run pytest tests/data_platform/utils/test_config_paths.py -q
```

Expected: exit 0.

```bash
cd /workspace
PYTHONPATH=. uv run pytest tests/data_platform/ingestion -q
```

Expected: exit 0, or only failures that already existed on this branch before this step. No new failures from this step.

## Must fail / not happen

- Run metadata storing only `config_path.name`.
- Manifest writer keeping `str(config_path.relative_to(REPO_ROOT))` instead of the shared helper.
- Calling `to_package_relative` for these two writers.
- Helper returning backslashes or a string that starts with `/`.
- Helper accepting a non-absolute path.
- Edits to Twitter record-type checks, Bluesky `author_filter`, YAML keys, or raw ids.
- Bundling sibling epic children.
