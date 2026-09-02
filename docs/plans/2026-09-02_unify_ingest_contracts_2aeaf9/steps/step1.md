# Step 1: Validate Twitter ingest record types at CLI startup

## Goal

Twitter YAML lists `record_types: [twitter.tweet]` but `sync_twitter.sync_records` never checks it. Bluesky requires `app.bsky.feed.post`. Reddit requires `reddit.comment` and/or `reddit.post`. This PR makes Twitter fail fast the same way.

## Caller / unit of work

**Main caller:** `data_platform/ingestion/sync_twitter.py` → `sync_records`.

**Slice:** load YAML → reject missing/wrong `record_types` → existing sync continues.

**Out of scope:** Bluesky/Reddit validators, YAML key renames, output format, other steps.

## Decision (locked)

- Constant `POSTS_RECORD_TYPE = "twitter.tweet"` in `sync_twitter.py`, matching Bluesky’s `POSTS_RECORD_TYPE` pattern in `data_platform/ingestion/sync_bluesky.py`.
- If `twitter.tweet` is not in `config["record_types"]`, raise `ValueError` with the same message shape Bluesky uses: `Unsupported record types for checkpoint sync: {record_types}`.
- Empty or missing `record_types` is invalid (raise). Extra unknown strings in the list are invalid even if `twitter.tweet` is also present — Twitter ingest only produces tweets.
- Do not add `twitter.tweet` to `RECORD_TYPE_FILENAMES` in this step (filename work is step 4).

## Files to inspect (read-only)

| Path | Why |
|------|-----|
| `docs/plans/2026-09-02_unify_ingest_contracts_2aeaf9/plan.md` | Parent plan |
| `data_platform/ingestion/sync_bluesky.py` | `POSTS_RECORD_TYPE` check around the `sync_records` record_types block |
| `data_platform/ingestion/sync_reddit.py` | Reddit allow-list pattern |
| `data_platform/ingestion/sync_twitter.py` | Current `sync_records` with no record_types check |
| `tests/data_platform/ingestion/test_sync_twitter_checkpoint.py` | Fixtures already set `record_types: ["twitter.tweet"]` |
| `tests/data_platform/ingestion/test_sync_bluesky_checkpoint.py` | Pattern for unsupported record_types tests if present |

## Files allowed to change

- `data_platform/ingestion/sync_twitter.py`
- `tests/data_platform/ingestion/test_sync_twitter_checkpoint.py`
- `CHANGELOG.md` (after the PR exists, via write-changelog)

## Files forbidden to change

- `data_platform/ingestion/sync_bluesky.py`
- `data_platform/ingestion/sync_reddit.py`
- `data_platform/ingestion/sync_checkpoint.py`
- All YAML under `data_platform/ingestion/configs/`
- Preprocess, features, curate, stimuli

## Contracts

```text
POSTS_RECORD_TYPE: str = "twitter.tweet"

sync_records(...)
  After load_yaml_config and require_dataset_id, before fetch:
  if POSTS_RECORD_TYPE not in record_types or set(record_types) != {POSTS_RECORD_TYPE}:
      raise ValueError(f"Unsupported record types for checkpoint sync: {record_types}")
```

Exact extra-type rule: the list must be exactly `["twitter.tweet"]` (order irrelevant). Duplicate `twitter.tweet` twice is invalid.

## Tests (write first)

`TestSyncRecordsRecordTypes` in `tests/data_platform/ingestion/test_sync_twitter_checkpoint.py` (or a new `test_sync_twitter_record_types.py` if that file is already large).

- given config with `record_types: ["twitter.tweet"]`, when `sync_records` is invoked with existing mocks, then it does not raise for record types (existing happy path still passes).
- given `record_types: ["reddit.comment"]`, then `pytest.raises(ValueError, match="Unsupported record types")`.
- given `record_types: ["twitter.tweet", "twitter.user"]`, then same `ValueError`.
- given `record_types: []`, then `ValueError`.

Follow `.cursor/skills/implement-plan-and-open-pr/UNIT_TESTING_STANDARDS.md`. One test class per function.

## Must pass

```bash
PYTHONPATH=. uv run pytest tests/data_platform/ingestion/test_sync_twitter_checkpoint.py tests/data_platform/ingestion/test_ingest_yaml_keys.py -q
```

Exit 0.

## Must still pass

```bash
PYTHONPATH=. uv run pytest tests/data_platform/ingestion -q
```

Exit 0. No new failures.

## Must not happen

- Twitter YAML rewritten in this PR.
- Bluesky/Reddit record-type strings changed.
- Fetch or checkpoint behavior changed for valid configs.
