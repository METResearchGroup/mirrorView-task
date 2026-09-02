# Step 1: Check Twitter record types before fetch

## Goal

Make `sync_twitter.sync_records` reject missing, empty, or unsupported `record_types` at CLI startup, matching Bluesky and Reddit, before `init_twitter_client` or `run_sync_tasks` runs.

## Caller / unit of work

**Main caller:** `data_platform/ingestion/sync_twitter.py` `sync_records`, reached from `main` through `run_sync_cli`.

**Task:** load YAML, confirm `record_types` includes the tweet type, then fetch.

**Out of scope:** `RECORD_TYPE_FILENAMES` and filename mapping (GitHub issue 106). Sibling issues 104 to 116. YAML key renames. Renaming raw tweet ids. Shared validators across platforms. Changing Bluesky or Reddit.

## Files to inspect (read-only)

| Path | Why |
|------|-----|
| `/workspace/data_platform/ingestion/sync_bluesky.py` | Pattern: `POSTS_RECORD_TYPE` and `ValueError(f"Unsupported record types for checkpoint sync: {record_types}")` when that type is not in `config["record_types"]` |
| `/workspace/data_platform/ingestion/sync_reddit.py` | Same error text when neither comments nor posts types are in the list |
| `/workspace/data_platform/ingestion/sync_twitter.py` | Current `sync_records` never reads `record_types` |
| `/workspace/data_platform/ingestion/configs/twitter/default.yaml` | YAML already lists `twitter.tweet` |
| `/workspace/data_platform/ingestion/sync_checkpoint.py` | `RECORD_TYPE_FILENAMES` must stay unchanged in this PR |
| `/workspace/tests/data_platform/ingestion/test_sync_twitter_checkpoint.py` | Existing Twitter tests; `_minimal_twitter_sync_config` already sets `record_types` |
| `/workspace/tests/data_platform/ingestion/test_ingest_yaml_keys.py` | Add a Twitter YAML assertion here |
| `/workspace/tests/data_platform/conftest.py` | `data_root` fixture for isolated storage |

## Files allowed to change

- `/workspace/data_platform/ingestion/sync_twitter.py`
- `/workspace/tests/data_platform/ingestion/test_sync_twitter_checkpoint.py`
- `/workspace/tests/data_platform/ingestion/test_ingest_yaml_keys.py`

Plan package files under `/workspace/docs/plans/2026-09-02_validate_twitter_record_types_e5b2cd/` may already be on the branch. Do not edit them during implementation.

## Files forbidden to change

- `/workspace/data_platform/ingestion/sync_bluesky.py`
- `/workspace/data_platform/ingestion/sync_reddit.py`
- `/workspace/data_platform/ingestion/sync_checkpoint.py`
- `/workspace/data_platform/ingestion/configs/**`
- `/workspace/CHANGELOG.md` during implementation (changelog is a later PR step)
- Any file outside the allowed list, except git commits of this work

## Contracts to lock

Add a module constant in `sync_twitter.py`:

```text
TWEETS_RECORD_TYPE = "twitter.tweet"
```

That string is the value Twitter ingest YAML already uses. Do not change YAML.

In `sync_records`, after `build_sync_tasks` and before `init_twitter_client`, match Bluesky:

```text
record_types: list[str] = config["record_types"]
if TWEETS_RECORD_TYPE not in record_types:
    raise ValueError(f"Unsupported record types for checkpoint sync: {record_types}")
```

Behavior:

- Missing `record_types` key: `KeyError` from `config["record_types"]` (same as Bluesky and Reddit).
- Empty list or list that does not contain `twitter.tweet`: `ValueError` with the message above.
- List that contains `twitter.tweet` plus extra types: allowed (same as Bluesky membership check).
- Do not call `init_twitter_client` or `run_sync_tasks` when the check fails.

Keep `sync_records(config_path: Path, *, run_dir_name: str | None = None) -> Path` unchanged as a signature.

Keep the check inline in `sync_records`. Do not add a shared helper module. Bluesky inlines the same membership test.

## Test design

Prefer the public `sync_records` API. One test class per function. Use `data_root`. Monkeypatch `load_config` with `_minimal_twitter_sync_config` (or a copy). Monkeypatch `ensure_dataset_manifest` as a no-op so tests do not need a config path under the repo root. Monkeypatch `init_twitter_client` and `run_sync_tasks` so failure cases prove fetch never starts, and the happy path does not hit the network.

Do not rewrite existing `run_sync_tasks` tests. Add a new class for `sync_records`. Add a new class in the YAML-keys file for Twitter ingest YAML.

```text
given config with record_types ["twitter.tweet"]
when sync_records(path)
then init_twitter_client is called
and run_sync_tasks is called

given config with record_types []
when sync_records(path)
then ValueError matching "Unsupported record types for checkpoint sync"
and init_twitter_client is not called
and run_sync_tasks is not called

given config with record_types ["twitter.user"]
when sync_records(path)
then ValueError matching "Unsupported record types for checkpoint sync"
and init_twitter_client is not called
and run_sync_tasks is not called

given config with no record_types key
when sync_records(path)
then KeyError
and init_twitter_client is not called
and run_sync_tasks is not called

given Twitter ingest YAML files under data_platform/ingestion/configs/twitter/
when each file is loaded
then record_types includes TWEETS_RECORD_TYPE
```

## Implementation notes (implement-from-spec)

Files already exist. Scaffold means adding `TWEETS_RECORD_TYPE` and a stub check in `sync_records` (`raise NotImplementedError` after reading `record_types`) so tests can fail for the right reason. Do not put the real membership test in until Phase 5.

Phase order, one Git commit per phase that changes the repo, and one commit per Phase 5 unit:

1. Phase 1 scope. Confirm caller, file tree, and out-of-scope. No product-code commit if nothing on disk changes.
2. Phase 2 scaffold. Add `TWEETS_RECORD_TYPE = "twitter.tweet"`. In `sync_records`, after `build_sync_tasks`, read `config["record_types"]` then `raise NotImplementedError`. Do not create the Twitter client yet on that path.
3. Phase 3 contracts. Confirm the constant name and value and the `sync_records` signature. Bodies stay stubs. Full auto. Do not wait for approval.
4. Phase 4 test design. Add the tests from the pseudocode. They must fail for `NotImplementedError` or wrong result on the happy path and empty/wrong-type paths, and `KeyError` on the missing-key path. Existing tests stay green.
5. Phase 5 units, in this order, one commit each:
   1. Membership check in `sync_records` so empty and wrong types raise `ValueError`, missing key still raises `KeyError`, and a valid list continues to `init_twitter_client`
6. Phase 6. Run the must-pass commands. Confirm `sync_checkpoint.py` is unchanged.

## Must pass

```bash
cd /workspace
PYTHONPATH=. uv run pytest tests/data_platform/ingestion/test_sync_twitter_checkpoint.py tests/data_platform/ingestion/test_ingest_yaml_keys.py -q
```

Expected: exit 0.

```bash
cd /workspace
PYTHONPATH=. uv run pytest tests/data_platform/ingestion -q
```

Expected: exit 0. No new failures. Existing Twitter checkpoint tests still collected and passing.

## Must fail / not happen

- `data_platform/ingestion/sync_checkpoint.py` changed (including `RECORD_TYPE_FILENAMES`).
- Twitter YAML files changed.
- `init_twitter_client` or `run_sync_tasks` called when record types are missing, empty, or wrong.
- A new shared ingest validator module.
- Sibling GitHub issues 104 to 116 implemented in this PR.
