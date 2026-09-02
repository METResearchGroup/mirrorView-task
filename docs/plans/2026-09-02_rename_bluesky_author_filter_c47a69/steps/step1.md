# Step 1: Rename the Bluesky YAML author filter

## Goal

Stop using YAML `ingestion_params.handle` as the name of the Bluesky search author filter, because env `BLUESKY_HANDLE` is login identity. Add `author_filter` as the YAML key, keep `handle` as a fallback, and update committed Bluesky configs that still set the old key.

## Caller / unit of work

**Main caller:** `data_platform/ingestion/sync_bluesky.py` `_search_posts_page`, reached from `fetch_posts_for_keyword` during `run_sync_tasks` / `sync_records`.

**Task:** resolve YAML author filter, then pass it as `author` on `client.app.bsky.feed.search_posts` when the value is truthy.

**Out of scope:** env `BLUESKY_HANDLE` / `init_bluesky_client` login. Row field `author_handle`. `tests/data_platform/constants.py` `"author_handle": "handle"`. Twitter and Reddit YAML keys. Raw platform ids. Sibling GitHub issues 103 and 105 to 116. A shared YAML alias framework.

## Files to inspect (read-only)

| Path | Why |
|------|-----|
| `/workspace/data_platform/ingestion/sync_bluesky.py` | `_search_posts_page` currently does `ingestion_params.get("handle")` and passes it as `author` |
| `/workspace/data_platform/ingestion/sync_clients.py` | Env login via `BLUESKY_HANDLE`. Do not change |
| `/workspace/data_platform/ingestion/configs/bluesky/default.yaml` | Only committed Bluesky config that sets `handle: user.bsky.social` |
| `/workspace/data_platform/ingestion/configs/bluesky/*.yaml` | Confirm other configs omit the key |
| `/workspace/tests/data_platform/ingestion/test_sync_bluesky_checkpoint.py` | Add resolver and search-page tests here |
| `/workspace/tests/data_platform/ingestion/test_ingest_yaml_keys.py` | Add committed Bluesky YAML key assertions here |
| `/workspace/tests/data_platform/ingestion/conftest.py` | `mock_post` uses `author.handle` on API post objects, not YAML |
| `/workspace/tests/data_platform/constants.py` | `"author_handle": "handle"` is a column map fixture, out of scope |

## Files allowed to change

- `/workspace/data_platform/ingestion/sync_bluesky.py`
- `/workspace/data_platform/ingestion/configs/bluesky/default.yaml`
- `/workspace/tests/data_platform/ingestion/test_sync_bluesky_checkpoint.py`
- `/workspace/tests/data_platform/ingestion/test_ingest_yaml_keys.py`

Plan package files under `/workspace/docs/plans/2026-09-02_rename_bluesky_author_filter_c47a69/` may already be on the branch. Do not edit them during implementation.

## Files forbidden to change

- `/workspace/data_platform/ingestion/sync_clients.py`
- `/workspace/data_platform/ingestion/sync_twitter.py`
- `/workspace/data_platform/ingestion/sync_reddit.py`
- `/workspace/data_platform/ingestion/configs/twitter/**`
- `/workspace/data_platform/ingestion/configs/reddit/**`
- `/workspace/tests/data_platform/constants.py`
- `/workspace/CHANGELOG.md` during implementation (changelog is a later PR step)
- Any file outside the allowed list, except git commits of this work

## Contracts to lock

Add a module helper in `sync_bluesky.py`:

```text
def _resolve_search_author(ingestion_params: dict[str, Any]) -> str | None:
```

Behavior:

- If `ingestion_params["author_filter"]` is truthy, return that value.
- Else if `ingestion_params["handle"]` is truthy, return that value.
- Else return `None`.
- Missing keys are the same as empty. Do not raise.
- If both keys are set and `author_filter` is truthy, `author_filter` wins.
- Do not read env `BLUESKY_HANDLE`.

In `_search_posts_page`, replace `handle = ingestion_params.get("handle")` with the helper. Keep the existing truthy check before adding `"author"` to searchPosts params. Keep `sort` default `"latest"`. Do not change the retry decorator or pagination.

There is no existing YAML key alias helper in this repo. Do not add a shared alias module, deprecation logger, or migration tool.

Rename YAML in `/workspace/data_platform/ingestion/configs/bluesky/default.yaml` from `handle: user.bsky.social` to `author_filter: user.bsky.social`. Do not add `author_filter` to other Bluesky configs that never set `handle`.

Keep `_search_posts_page` and `sync_records` signatures unchanged.

## Test design

Prefer calling `_resolve_search_author` for key resolution, and `_search_posts_page` for the API author argument. One test class per function. Use `MagicMock` for the Bluesky client so tests do not hit the network. Do not rewrite existing `run_sync_tasks` tests.

```text
given ingestion_params with author_filter "alice.bsky.social"
when _resolve_search_author(params)
then return "alice.bsky.social"

given ingestion_params with handle "old.bsky.social" and no author_filter
when _resolve_search_author(params)
then return "old.bsky.social"

given ingestion_params with author_filter "alice.bsky.social" and handle "old.bsky.social"
when _resolve_search_author(params)
then return "alice.bsky.social"

given ingestion_params with neither key, or with empty strings
when _resolve_search_author(params)
then return None

given ingestion_params with author_filter "alice.bsky.social"
when _search_posts_page(client, params, query, page_limit=10)
then search_posts is called with params.author equal to "alice.bsky.social"

given ingestion_params with handle "old.bsky.social" and no author_filter
when _search_posts_page(client, params, query, page_limit=10)
then search_posts is called with params.author equal to "old.bsky.social"

given ingestion_params with neither key
when _search_posts_page(client, params, query, page_limit=10)
then search_posts is called without an author key

given Bluesky YAML files under data_platform/ingestion/configs/bluesky/
when each file is loaded
then ingestion_params does not contain handle
and default.yaml ingestion_params.author_filter equals "user.bsky.social"
```

## Implementation notes (implement-from-spec)

Files already exist. Scaffold means adding `_resolve_search_author` as `raise NotImplementedError` and calling it from `_search_posts_page` in place of `ingestion_params.get("handle")`. Do not put the real key preference in until Phase 5.

Phase order, one Git commit per phase that changes the repo, and one commit per Phase 5 unit:

1. Phase 1 scope. Confirm caller, file tree, and out-of-scope. No product-code commit if nothing on disk changes.
2. Phase 2 scaffold. Add `_resolve_search_author` that raises `NotImplementedError`. In `_search_posts_page`, call it instead of `ingestion_params.get("handle")`. If the helper raises, the page fetch does not call searchPosts.
3. Phase 3 contracts. Confirm `_resolve_search_author(ingestion_params: dict[str, Any]) -> str | None`. Bodies stay stubs. Full auto. Do not wait for approval.
4. Phase 4 test design. Add the tests from the pseudocode. Resolution and search-page tests must fail for `NotImplementedError`. YAML tests fail until `default.yaml` is renamed. Existing checkpoint tests stay green because they monkeypatch `_search_posts_page`.
5. Phase 5 units, in this order, one commit each:
   1. Implement `_resolve_search_author` so author_filter wins, handle is the fallback, and empty or missing keys return None. Search-page tests that need a resolved author should pass.
   2. Rename `handle` to `author_filter` in `data_platform/ingestion/configs/bluesky/default.yaml` so the YAML-key tests pass.
6. Phase 6. Run the must-pass commands. Confirm `sync_clients.py`, Twitter, and Reddit files are unchanged.

## Must pass

```bash
cd /workspace
PYTHONPATH=. uv run pytest tests/data_platform/ingestion/test_sync_bluesky_checkpoint.py tests/data_platform/ingestion/test_ingest_yaml_keys.py -q
```

Expected: exit 0.

```bash
cd /workspace
PYTHONPATH=. uv run pytest tests/data_platform/ingestion -q
```

Expected: exit 0. No new failures. Existing Bluesky checkpoint tests still collected and passing.

## Must fail / not happen

- `data_platform/ingestion/sync_clients.py` changed, or env `BLUESKY_HANDLE` used as the search author.
- Twitter or Reddit YAML keys changed.
- `tests/data_platform/constants.py` or row `author_handle` renamed.
- A new shared ingest alias module or deprecation logger.
- Sibling GitHub issues 103 and 105 to 116 implemented in this PR.
