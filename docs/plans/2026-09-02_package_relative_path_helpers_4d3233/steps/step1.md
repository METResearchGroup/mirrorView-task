# Step 1: Land constants, path helpers, and their tests

## Goal

Add `data_platform/constants.py` and `data_platform/utils/paths.py` so later explicit-path work can resolve and round-trip paths relative to the data-platform package. Production storage and stage CLIs stay on the old API. Tests in `tests/data_platform/utils/test_paths.py` are the only caller.

## Caller / unit of work

**Main caller:** unit tests in `/workspace/tests/data_platform/utils/test_paths.py` importing constants and calling `resolve_package_path` then `to_package_relative`.

**Slice:** constants exist; a relative path resolves under the package; invalid relative inputs raise; an absolute path under the package converts back to a POSIX relative string.

**Out of scope:** `data_platform/utils/storage.py` API; ingest, preprocess, curate, and feature-generation CLIs; slimming metadata; sibling issues #82 to #85; editing `tests/data_platform/constants.py` (that file is a test fixture module, not production constants).

## Decision (locked)

Put the helper at `/workspace/data_platform/utils/paths.py` because the issue's required test path is `/workspace/tests/data_platform/utils/test_paths.py`, which matches the existing `data_platform/utils/` plus `tests/data_platform/utils/` pairing (see `/workspace/data_platform/utils/config_paths.py` and `/workspace/tests/data_platform/utils/test_config_paths.py`).

Keep two functions. Do not add a separate validate-only helper, a custom exception type, or a Path subclass. Raise `ValueError` to match existing package validation in `/workspace/data_platform/utils/dataset.py`.

Do not require the target file to exist. Later writers will resolve paths before creating files.

`PACKAGE_ROOT` is the directory that contains `/workspace/data_platform/constants.py` (`Path(__file__).resolve().parent`), not the repo root and not `data_platform/data/`. Current `DATA_ROOT` in `/workspace/data_platform/utils/storage.py` stays as it is.

## Files to inspect (read-only)

| Path | Why |
|------|-----|
| `/workspace/docs/plans/2026-09-02_package_relative_path_helpers_4d3233/plan.md` | Parent plan |
| `/workspace/data_platform/utils/storage.py` | Current `DATA_ROOT`, `METADATA_FILENAME`, and `posts.csv` / `comments.csv` literals. Do not change this file. |
| `/workspace/data_platform/utils/dataset.py` | Current `_DATA_ROOT` and `ValueError` validation style. Do not change this file. |
| `/workspace/data_platform/utils/config_paths.py` | Nearby path helper style. It allows absolute YAML paths relative to repo root, so it is not the model for this helper. |
| `/workspace/lib/constants.py` | Existing `Path(__file__).parent` root constant style. |
| `/workspace/tests/data_platform/utils/test_config_paths.py` | Test layout next to utils helpers. |
| `/workspace/tests/data_platform/constants.py` | Fixture module. Do not confuse with production constants. Do not edit. |

## Files allowed to change

- Create `/workspace/data_platform/constants.py`
- Create `/workspace/data_platform/utils/paths.py`
- Create `/workspace/tests/data_platform/utils/test_paths.py`
- `/workspace/CHANGELOG.md` (after the PR exists, via write-changelog)

Plan files under `/workspace/docs/plans/2026-09-02_package_relative_path_helpers_4d3233/` are already committed on this branch. Do not rewrite them during implementation.

## Files forbidden to change

- `/workspace/data_platform/utils/storage.py`
- `/workspace/data_platform/utils/dataset.py`
- `/workspace/data_platform/utils/config_paths.py`
- `/workspace/data_platform/ingestion/**`
- `/workspace/data_platform/preprocessing/**`
- `/workspace/data_platform/curate/**`
- `/workspace/data_platform/generate_features/**`
- `/workspace/tests/data_platform/constants.py`
- `/workspace/docs/runbooks/**`

## Contracts to lock

`/workspace/data_platform/constants.py`:

```text
PACKAGE_ROOT: Path
  Path(__file__).resolve().parent
  the data_platform package directory

POSTS_FILENAME: str = "posts.csv"
COMMENTS_FILENAME: str = "comments.csv"
METADATA_FILENAME: str = "metadata.json"
```

Use these exact names. Values are the full file names, including the suffix. Do not add stem-only constants (`posts`, `comments`) and do not add parquet aliases.

`/workspace/data_platform/utils/paths.py`:

```text
resolve_package_path(relative_path: str | Path) -> Path
  Join relative_path onto PACKAGE_ROOT and return a resolved Path.
  The target file does not need to exist.
  Raise ValueError if relative_path is absolute.
  Raise ValueError if any path part is "..".
  Raise ValueError if the resolved path is not inside PACKAGE_ROOT.

to_package_relative(path: str | Path) -> str
  Convert an absolute path under PACKAGE_ROOT into a POSIX string relative to PACKAGE_ROOT
  (forward slashes, no leading slash).
  Raise ValueError if path is not absolute.
  Raise ValueError if the resolved path is not inside PACKAGE_ROOT.
```

Round-trip invariant for a valid relative input that stays under the package:

```text
to_package_relative(resolve_package_path(relative_path)) == Path(relative_path).as_posix()
```

Empty string is invalid for `resolve_package_path` (raise `ValueError`). A lone `.` is valid and resolves to `PACKAGE_ROOT`. `to_package_relative(PACKAGE_ROOT)` returns `"."`.

Do not change `StorageManager`, `DATA_ROOT`, or the `METADATA_FILENAME` copy inside `/workspace/data_platform/utils/storage.py`.

## Test design

Pseudocode then real tests. One test class per public function, named `TestResolvePackagePath` and `TestToPackageRelative`, plus `TestPackageConstants` for the constants. Follow `/workspace/.cursor/skills/implement-plan-and-open-pr/UNIT_TESTING_STANDARDS.md`. Prefer `pytest.raises(ValueError)`.

given relative_path "data/bluesky/example/posts.csv"
when resolve_package_path(relative_path)
then result == PACKAGE_ROOT / "data" / "bluesky" / "example" / "posts.csv"
and result == result.resolve()

given relative_path Path("data/x/posts.csv")
when resolve_package_path(relative_path)
then result is PACKAGE_ROOT joined with those parts (Path input is accepted)

given relative_path "."
when resolve_package_path(".")
then result == PACKAGE_ROOT

given relative_path ""
when resolve_package_path("")
then raise ValueError

given an absolute path such as Path("/tmp/posts.csv")
when resolve_package_path(absolute)
then raise ValueError

given relative_path "data/../secrets.txt"
when resolve_package_path(relative_path)
then raise ValueError
and do not return a path even though it would stay under PACKAGE_ROOT after normalize

given relative_path "../README.md"
when resolve_package_path(relative_path)
then raise ValueError

given absolute_path PACKAGE_ROOT / "data" / "posts.csv"
when to_package_relative(absolute_path)
then result == "data/posts.csv"

given absolute_path PACKAGE_ROOT
when to_package_relative(PACKAGE_ROOT)
then result == "."

given relative string "data/posts.csv"
when to_package_relative("data/posts.csv")
then raise ValueError

given absolute_path /tmp/outside.csv (or another path outside PACKAGE_ROOT)
when to_package_relative(absolute_path)
then raise ValueError

given relative_path "data/run/posts.csv"
when to_package_relative(resolve_package_path(relative_path))
then result == "data/run/posts.csv"

given the constants module
then POSTS_FILENAME == "posts.csv"
and COMMENTS_FILENAME == "comments.csv"
and METADATA_FILENAME == "metadata.json"
and PACKAGE_ROOT == Path of data_platform/constants.py .parent
and PACKAGE_ROOT.name == "data_platform"

## Implementation notes

Follow implement-from-spec phases in this packet. One Git commit per phase and per unit of work.

Phase 2 scaffold: create the two production modules and the test module with imports and stub bodies (`raise NotImplementedError`). No validation logic yet.

Phase 3 contracts: signatures and constants only. Bodies stay stubs.

Phase 4: write the failing tests from the scenarios above.

Phase 5 units of work, in this order:

1. Constants in `/workspace/data_platform/constants.py`
2. `resolve_package_path`
3. `to_package_relative`

Do not import the new helpers from storage or CLIs.

Numpy-style docstrings on the public functions and a module docstring on each new production file. The module docstring may include `PYTHONPATH=. uv run pytest tests/data_platform/utils/test_paths.py -q` as the relevant run command.

## Must pass

```bash
cd /workspace
PYTHONPATH=. uv run pytest tests/data_platform/utils/test_paths.py -q
```

Expected: exit 0.

```bash
cd /workspace
PYTHONPATH=. uv run pytest tests/data_platform -q
```

Expected: exit 0, or only failures that already existed on `main` before this branch. No new failures from this step.

## Must fail / not happen

- Any edit to `/workspace/data_platform/utils/storage.py` or stage CLIs.
- Helpers accepting absolute paths in `resolve_package_path`.
- Helpers accepting a `..` part in `resolve_package_path`.
- `to_package_relative` returning backslashes or a string that starts with `/`.
- `PACKAGE_ROOT` pointing at the repo root or at `data_platform/data`.
- Adding stem-only file-name constants or parquet filename constants.
- Editing `/workspace/tests/data_platform/constants.py`.
