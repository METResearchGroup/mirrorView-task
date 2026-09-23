# Step 6: Standardize per-task fetch caps across ingest platforms

## Goal

Bluesky uses `limit`, Twitter `limit_per_keyword`, Reddit `limit_per_subreddit` for the same knob: max items fetched for one checkpoint task.

## Caller / unit of work

**Main caller:** `build_sync_tasks` / fetch loops in `sync_bluesky.py`, `sync_twitter.py`, `sync_reddit.py`.

**Slice:** resolve `limit_per_task` with aliases → existing fetch limits unchanged in meaning.

**Out of scope:** `max_rows` (step 7). Output filenames.

## Decision (locked)

- Canonical YAML key: `limit_per_task` (int > 0).
- Aliases, platform-specific: Bluesky `limit`; Twitter `limit_per_keyword`; Reddit `limit_per_subreddit`.
- Resolution order: `limit_per_task` if present, else the platform alias. If both present and unequal, `ValueError`. If both present and equal, use it and warn if the alias is present (`DeprecationWarning`).
- Twitter default when neither is set remains `25` (today’s `limit_per_keyword` default). Bluesky and Reddit keep requiring an explicit value (today they require `limit` / `limit_per_subreddit`).
- Update committed YAML to `limit_per_task` and remove the old key from those files.
- Helper `resolve_limit_per_task(ingestion_params, *, alias_key: str, default: int | None) -> int` in `sync_checkpoint.py` so all three CLIs share it.

## Files to inspect (read-only)

| Path | Why |
|------|-----|
| `data_platform/ingestion/sync_bluesky.py` | `limit` |
| `data_platform/ingestion/sync_twitter.py` | `_effective_limit_per_keyword` |
| `data_platform/ingestion/sync_reddit.py` | `limit_per_subreddit` |
| `data_platform/ingestion/sync_checkpoint.py` | shared helper home |
| All `data_platform/ingestion/configs/**/*.yaml` | current cap keys |
| Existing checkpoint tests | fixtures |

## Files allowed to change

- `data_platform/ingestion/sync_checkpoint.py`
- `data_platform/ingestion/sync_bluesky.py`
- `data_platform/ingestion/sync_twitter.py`
- `data_platform/ingestion/sync_reddit.py`
- `data_platform/ingestion/configs/**/*.yaml` (cap keys only)
- `tests/data_platform/ingestion/test_sync_checkpoint.py` (helper tests)
- `tests/data_platform/ingestion/test_sync_bluesky_checkpoint.py`
- `tests/data_platform/ingestion/test_sync_twitter_checkpoint.py`
- `tests/data_platform/ingestion/test_sync_reddit_checkpoint.py`
- `tests/data_platform/ingestion/conftest.py` and `reddit_conftest.py` / `twitter_conftest.py` as needed
- `CHANGELOG.md`

## Files forbidden to change

- Preprocess / features / curate
- `max_rows` semantics
- Models

## Contracts

```text
resolve_limit_per_task(
    ingestion_params: dict[str, Any],
    *,
    alias_key: str,
    default: int | None = None,
) -> int
  Canonical key "limit_per_task".
  Raise ValueError if missing and default is None.
  Raise ValueError if the resolved int is <= 0.
  Raise ValueError if canonical and alias both set and int(canonical) != int(alias).
```

Bluesky: `alias_key="limit", default=None`.
Twitter: `alias_key="limit_per_keyword", default=25`.
Reddit: `alias_key="limit_per_subreddit", default=None`.

Twitter `_effective_limit_per_keyword` still mins with remaining `max_rows` budget; rename the function to `_effective_limit_per_task` in this PR.

## Tests (write first)

`TestResolveLimitPerTask` covering canonical, alias+warning, conflict, missing, non-positive.

Platform checkpoint tests still collect the same number of rows when YAML uses `limit_per_task` equal to the old value.

## Must pass

```bash
PYTHONPATH=. uv run pytest tests/data_platform/ingestion -q
```

Exit 0.

## Must not happen

- Changing numeric defaults except via the documented Twitter 25.
- Removing alias support in this PR (configs outside the repo may still use old keys).
