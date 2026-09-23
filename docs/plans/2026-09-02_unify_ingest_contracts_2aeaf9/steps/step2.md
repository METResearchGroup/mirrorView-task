# Step 2: Rename Bluesky YAML author filter away from login identity

## Goal

Bluesky YAML `ingestion_params.handle` is an API author filter. Env `BLUESKY_HANDLE` is login identity. Rename the YAML key so operators cannot confuse them.

## Caller / unit of work

**Main caller:** `data_platform/ingestion/sync_bluesky.py` → `_search_posts_page` / `fetch_posts_for_keyword` reading the author filter.

**Slice:** read `author_filter` (preferred) or deprecated `handle` → pass to AppView `author` param as today.

**Out of scope:** Env var names, Twitter/Reddit, other YAML keys.

## Decision (locked)

- Canonical YAML key: `author_filter` (string, optional).
- If both `author_filter` and `handle` are set and differ, raise `ValueError` naming both keys.
- If only `handle` is set, use it and emit a `warnings.warn` (`DeprecationWarning`) that `handle` is deprecated in favor of `author_filter`.
- Update committed Bluesky YAML that currently set `handle` (`data_platform/ingestion/configs/bluesky/default.yaml`) to `author_filter`.
- Do not change `BLUESKY_HANDLE` / `BLUESKY_PASSWORD` in `data_platform/ingestion/sync_clients.py`.

## Files to inspect (read-only)

| Path | Why |
|------|-----|
| `data_platform/ingestion/sync_bluesky.py` | `ingestion_params.get("handle")` in `_search_posts_page` |
| `data_platform/ingestion/sync_clients.py` | Login env; do not change |
| `data_platform/ingestion/configs/bluesky/default.yaml` | Has `handle: user.bsky.social` |
| `tests/data_platform/ingestion/test_sync_bluesky_checkpoint.py` | Search/fetch tests |

## Files allowed to change

- `data_platform/ingestion/sync_bluesky.py`
- `data_platform/ingestion/configs/bluesky/*.yaml` (only the `handle` key → `author_filter`; no other key changes)
- `tests/data_platform/ingestion/test_sync_bluesky_checkpoint.py`
- `CHANGELOG.md`

## Files forbidden to change

- `data_platform/ingestion/sync_clients.py`
- `data_platform/ingestion/sync_twitter.py`
- `data_platform/ingestion/sync_reddit.py`
- Twitter and Reddit YAML
- Preprocess / features / curate

## Contracts

```text
resolve_bluesky_author_filter(ingestion_params: dict) -> str | None
  Returns author_filter if set (non-empty string).
  Else returns handle if set, after DeprecationWarning.
  Else None.
  Raise ValueError if both set and not equal.

_search_posts_page uses resolve_bluesky_author_filter; API query param remains "author".
```

Put `resolve_bluesky_author_filter` in `sync_bluesky.py` (not a new module).

## Tests (write first)

`TestResolveBlueskyAuthorFilter`:

- `author_filter` only → that string; no warning.
- `handle` only → that string; `DeprecationWarning`.
- both equal → that string; still warn because `handle` is present.
- both differ → `ValueError`.
- neither → `None`.

Existing fetch tests that omit both still work. If a test passed `handle` in params, update it to `author_filter` except one alias test.

## Must pass

```bash
PYTHONPATH=. uv run pytest tests/data_platform/ingestion/test_sync_bluesky_checkpoint.py tests/data_platform/ingestion/test_ingest_yaml_keys.py -q
```

Exit 0.

## Must not happen

- Renaming env `BLUESKY_HANDLE`.
- Changing the AppView query parameter name (`author`).
- Dropping author-scoped search.
