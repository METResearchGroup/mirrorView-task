# Step 5: Require list-form search terms on Twitter ingest configs

## Goal

Bluesky YAML uses `keywords: [str, ...]`. Twitter uses `keyword` as a string or a list. Unify Twitter on `keywords`.

## Caller / unit of work

**Main caller:** `data_platform/ingestion/sync_twitter.py` → `build_sync_tasks`.

**Slice:** parse `keywords` (list) or deprecated `keyword` → `list[TwitterTask]`.

**Out of scope:** Bluesky `keywords` parser, Reddit subreddits, limit keys (step 6).

## Decision (locked)

- Canonical key: `keywords` as a non-empty list of non-empty strings (same rules as Bluesky `build_sync_tasks`).
- Alias: `keyword` as `str` or `list[str]`. If only `keyword` is present, build tasks from it and `warnings.warn` `DeprecationWarning`.
- If both `keywords` and `keyword` are present, raise `ValueError` (do not merge).
- Update all committed files under `data_platform/ingestion/configs/twitter/` from `keyword:` to `keywords:` (wrap a scalar `example` as a one-item list).
- Task ledger field stays `keyword` (the term for that task). Row field `keyword` on `SyncTwitterPostModel` stays.

## Files to inspect (read-only)

| Path | Why |
|------|-----|
| `data_platform/ingestion/sync_twitter.py` | `build_sync_tasks` |
| `data_platform/ingestion/sync_bluesky.py` | list validation to copy |
| `data_platform/ingestion/configs/twitter/*.yaml` | `keyword:` |
| `tests/data_platform/ingestion/test_sync_twitter_checkpoint.py` | fixtures using `keyword` |
| `tests/data_platform/ingestion/conftest.py` | twitter params |

## Files allowed to change

- `data_platform/ingestion/sync_twitter.py`
- `data_platform/ingestion/configs/twitter/*.yaml`
- `tests/data_platform/ingestion/test_sync_twitter_checkpoint.py`
- `tests/data_platform/ingestion/conftest.py` (twitter ingest params only)
- `tests/data_platform/ingestion/test_ingest_yaml_keys.py` only if a dead-key set must allow neither (prefer not)
- `CHANGELOG.md`

## Files forbidden to change

- Bluesky and Reddit sync/YAML except if a shared helper is extracted into a new function in `sync_twitter.py` only
- `data_platform/models/sync.py` (row `keyword` stays)
- Preprocess / features / curate

## Contracts

```text
build_sync_tasks(ingestion_params) -> list[TwitterTask]
  Prefer ingestion_params["keywords"] as list[str], non-empty, each stripped non-empty.
  Else ingestion_params["keyword"] as str or list[str] (deprecated).
  Else ValueError: must include 'keywords' as a non-empty list of strings.
```

## Tests (write first)

`TestBuildSyncTasks`:

- `keywords: ["a", "b"]` → two tasks, ids `a` and `b`.
- `keyword: "a"` → one task, `DeprecationWarning`.
- `keyword: ["a"]` → one task, warning.
- both keys → `ValueError`.
- `keywords: []` → `ValueError`.
- `keywords: ["  "]` → `ValueError`.

Existing checkpoint tests: switch fixtures to `keywords` except the alias tests.

## Must pass

```bash
PYTHONPATH=. uv run pytest tests/data_platform/ingestion/test_sync_twitter_checkpoint.py tests/data_platform/ingestion/test_ingest_yaml_keys.py tests/data_platform/ingestion/test_query_terms.py -q
```

Exit 0.

## Must not happen

- Changing Bluesky’s `keywords` key.
- Removing per-row `keyword` from Twitter CSV schema.
- Silently ignoring one of two conflicting keys.
