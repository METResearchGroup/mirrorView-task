# Step 1: Add package-relative path helpers and file-name constants

## Goal

Land `data_platform/constants.py` and a path helper that resolves and validates paths relative to `data_platform/`. Production storage and stage CLIs stay on the old API. This PR only adds unused (except by its tests) building blocks.

## Caller / unit of work

**Main caller:** tests under `tests/data_platform/utils/test_paths.py` (and constants assertions in that file or `tests/data_platform/utils/test_constants.py`).

```bash
cd /Users/mark/src/work/mirrorview-wt
PYTHONPATH=. uv run pytest tests/data_platform/utils/test_paths.py -q
```

Expected: exit 0; all new tests pass.

**In scope:** Constants for full file names; `PACKAGE_ROOT`; resolve/validate/relativize helpers; unit tests including traversal rejection.

**Out of scope:** Any change to `StorageManager`, ingest, preprocess, features, curation, runbooks, or existing tests.

## Decision (locked)

- File names in constants are full names, not stems: `posts.csv`, `comments.csv`, `metadata.json`.
- Paths passed to the helper are relative to `data_platform/` (example: `data/bluesky/<id>/raw/<ts>/posts.csv`).
- Resolve against `PACKAGE_ROOT`. Reject absolute inputs, `..` segments, and any resolved path that is not inside `PACKAGE_ROOT`.
- Do not read `dataset.json` for format. Do not compose suffixes.

## Files to inspect (read-only)

| Path | Why |
|------|-----|
| `/Users/mark/src/work/mirrorview-wt/docs/plans/2026-09-01_explicit_pipeline_paths_ebe7ae/plan.md` | Parent plan |
| `/Users/mark/src/work/mirrorview-wt/data_platform/utils/storage.py` | Current `DATA_ROOT` and `METADATA_FILENAME` (do not change this step) |
| `/Users/mark/src/work/mirrorview-wt/data_platform/utils/dataset.py` | Current `_DATA_ROOT` (do not change this step) |
| `/Users/mark/src/work/mirrorview-wt/lib/constants.py` | Do not put data-platform file names here |

## Files allowed to change

- Create `/Users/mark/src/work/mirrorview-wt/data_platform/constants.py`
- Create `/Users/mark/src/work/mirrorview-wt/data_platform/utils/paths.py`
- Create `/Users/mark/src/work/mirrorview-wt/tests/data_platform/utils/test_paths.py`
- Optionally create `/Users/mark/src/work/mirrorview-wt/tests/data_platform/utils/test_constants.py` if constants assertions are split out

## Files forbidden to change

- `/Users/mark/src/work/mirrorview-wt/data_platform/utils/storage.py`
- `/Users/mark/src/work/mirrorview-wt/data_platform/utils/dataset.py`
- `/Users/mark/src/work/mirrorview-wt/lib/constants.py`
- All ingest, preprocess, feature, curate, and runbook files
- Existing tests other than the new files above

## Contracts

`data_platform/constants.py`:

- `PACKAGE_ROOT`: `Path` of the `data_platform/` directory (`Path(__file__).resolve().parent`).
- `POSTS_FILE = "posts.csv"`
- `COMMENTS_FILE = "comments.csv"`
- `METADATA_FILE = "metadata.json"`

`data_platform/utils/paths.py`:

- `resolve_package_path(relative: str | Path) -> Path`: join `PACKAGE_ROOT` with `relative`, `resolve()`, return the absolute path. Raise `ValueError` if `relative` is absolute, if any path part is `..`, or if the resolved path is not inside `PACKAGE_ROOT` (`is_relative_to`).
- `to_package_relative(path: Path) -> str`: `path.resolve().relative_to(PACKAGE_ROOT)` as a POSIX string (`as_posix()`). Raise `ValueError` if `path` is not inside `PACKAGE_ROOT`.

Do not accept a `package_root=` override on the public helpers. Tests monkeypatch `data_platform.constants.PACKAGE_ROOT` (and the same name if `paths.py` imported it by value — import the module attribute so the patch applies).

## Tests (write first; they must fail until helpers exist)

Happy path: monkeypatch `PACKAGE_ROOT` to a `tmp_path`. `resolve_package_path("data/bluesky/x/raw/ts/posts.csv")` equals `tmp_path / "data/bluesky/x/raw/ts/posts.csv"`. Create that file (or just the parent); `to_package_relative` of the resolved path equals `data/bluesky/x/raw/ts/posts.csv`.

Failures that must raise `ValueError`:

- Absolute `relative` (e.g. `/etc/passwd`)
- `relative` containing `..` (e.g. `data/../secrets`)
- `to_package_relative` on a path outside the patched root

Constants tests: `POSTS_FILE == "posts.csv"`, `COMMENTS_FILE == "comments.csv"`, `METADATA_FILE == "metadata.json"`. `PACKAGE_ROOT` in an unpatched process ends with `data_platform`.

## Must pass

```bash
PYTHONPATH=. uv run pytest tests/data_platform/utils/test_paths.py -q
```

Exit 0.

## Must still pass (no regressions)

```bash
PYTHONPATH=. uv run pytest tests/data_platform -q
```

Exit 0. Same failures as before this step, none new.

## Must not happen

- Production callers import the new helpers yet.
- `POSTS_FILE` includes a parquet variant.
- Helper restems or reads `dataset.json`.
