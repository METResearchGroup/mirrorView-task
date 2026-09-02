# Step 1: Point Twitter ingest at the list search-term key

## Goal

Stop using YAML `ingestion_params.keyword` as the only way to name Twitter search terms, because Bluesky already requires `ingestion_params.keywords` as a non-empty list of strings. Prefer `keywords` when that key is present, keep `keyword` as a string-or-list fallback, and update committed Twitter configs that still set the old key.

## Caller / unit of work

**Main caller:** `data_platform/ingestion/sync_twitter.py` `build_sync_tasks`, reached from `sync_records` before `init_twitter_client` and `run_sync_tasks`.

**Task:** resolve search terms from YAML, then build one `TwitterTask` per term.

**Out of scope:** `limit_per_keyword` (GitHub issue 108). Bluesky `build_sync_tasks` and Bluesky YAML. `TwitterTask.keyword` as a per-task field. Tweet row column `keyword`. `quote_query_term` behavior. Reddit YAML. Raw platform ids. Sibling GitHub issues 103, 104, 105, 106, and 108 to 116. A shared YAML alias framework. A deprecation logger.

## Files to inspect (read-only)

| Path | Why |
|------|-----|
| `/workspace/data_platform/ingestion/sync_bluesky.py` | Pattern: `build_sync_tasks` requires `keywords` as a non-empty list of non-empty strings, then strips each entry |
| `/workspace/data_platform/ingestion/sync_twitter.py` | Current `build_sync_tasks` reads `keyword` as a string or a list |
| `/workspace/data_platform/ingestion/query_terms.py` | Shared quoting. Twitter still quotes later in `twitter_client.build_query`. Do not change quoting here |
| `/workspace/data_platform/ingestion/twitter_client.py` | `fetch_posts_for_keyword` still takes one search term string. Do not rename that argument |
| `/workspace/data_platform/ingestion/configs/twitter/*.yaml` | All five committed Twitter configs still set `keyword` |
| `/workspace/data_platform/ingestion/configs/bluesky/default.yaml` | List shape to copy: `keywords:` then `- example` |
| `/workspace/tests/data_platform/ingestion/test_sync_twitter_checkpoint.py` | Add resolver tests here. Leave `_minimal_twitter_sync_config` on `keyword` so existing tests keep proving the fallback |
| `/workspace/tests/data_platform/ingestion/test_ingest_yaml_keys.py` | Add committed Twitter YAML key assertions here |
| `/workspace/tests/data_platform/ingestion/test_query_terms.py` | Must stay green. Do not change quoting tests |
| `/workspace/tests/data_platform/ingestion/twitter_conftest.py` | Row field `keyword` is tweet data, not YAML. Do not change |
| `/workspace/tests/data_platform/ingestion/test_sync_bluesky_checkpoint.py` | Bluesky list checks to match. Do not edit |

## Files allowed to change

- `/workspace/data_platform/ingestion/sync_twitter.py`
- `/workspace/data_platform/ingestion/configs/twitter/default.yaml`
- `/workspace/data_platform/ingestion/configs/twitter/mirrorview.yaml`
- `/workspace/data_platform/ingestion/configs/twitter/mirrorview_scale.yaml`
- `/workspace/data_platform/ingestion/configs/twitter/mirrorview_scale_2.yaml`
- `/workspace/data_platform/ingestion/configs/twitter/keyword_politics_econ_7000.yaml`
- `/workspace/tests/data_platform/ingestion/test_sync_twitter_checkpoint.py`
- `/workspace/tests/data_platform/ingestion/test_ingest_yaml_keys.py`

Plan package files under `/workspace/docs/plans/2026-09-02_twitter_list_search_terms_fdc6d4/` may already be on the branch. Do not edit them during implementation.

## Files forbidden to change

- `/workspace/data_platform/ingestion/sync_bluesky.py`
- `/workspace/data_platform/ingestion/sync_reddit.py`
- `/workspace/data_platform/ingestion/query_terms.py`
- `/workspace/data_platform/ingestion/twitter_client.py`
- `/workspace/data_platform/ingestion/configs/bluesky/**`
- `/workspace/data_platform/ingestion/configs/reddit/**`
- `/workspace/tests/data_platform/ingestion/test_query_terms.py`
- `/workspace/tests/data_platform/ingestion/twitter_conftest.py`
- `/workspace/CHANGELOG.md` during implementation (changelog is skipped for this PR)
- Any file outside the allowed list, except git commits of this work

## Contracts to lock

Add a module helper in `sync_twitter.py`:

```text
def _resolve_search_terms(ingestion_params: dict[str, Any]) -> list[str]:
```

Behavior:

- If the `keywords` key is present (`"keywords" in ingestion_params`):
  - If the value is not a non-empty list, raise `ValueError("ingestion_params must include 'keywords' as a non-empty list of strings")`.
  - For each entry, if it is not a string or `raw.strip()` is empty, raise `ValueError("ingestion_params.keywords entries must be non-empty strings")`.
  - Return stripped strings, in list order. Do not quote them. Twitter quoting stays in `twitter_client.build_query`.
- Else read `ingestion_params.get("keyword")`:
  - If it is a non-empty list, return `[str(k) for k in keyword]` (same as today's Twitter list path, including non-string items).
  - If it is a non-empty string, return `[keyword]`.
  - Else raise `ValueError("ingestion_params must include 'keywords' as a non-empty list of strings")`.
- If both keys are set, `keywords` wins even when `keyword` is also set. Do not fall back when `keywords` is present and invalid.
- Do not read `limit_per_keyword`.

In `build_sync_tasks`, replace the inline `keyword` lookup with the helper. Map each resolved string to `TwitterTask(task_id=term, keyword=term)`. Keep the `TwitterTask.keyword` field name.

There is no existing YAML key alias helper in this repo. Do not add a shared alias module, deprecation logger, or migration tool.

Rename YAML `ingestion_params.keyword` to `ingestion_params.keywords` in every file under `/workspace/data_platform/ingestion/configs/twitter/`. Keep list items and comments. Change `default.yaml` from `keyword: example` to a one-item list matching Bluesky `default.yaml`:

```yaml
  keywords:
    - example
```

Do not rename `limit_per_keyword`.

Keep `build_sync_tasks(ingestion_params: dict[str, Any]) -> list[TwitterTask]` and `sync_records` signatures unchanged.

## Test design

Prefer calling `build_sync_tasks` for key resolution. One test class per function. Do not rewrite existing `run_sync_tasks` tests. Leave `_minimal_twitter_sync_config` on `keyword` so those tests keep proving the fallback. Add YAML assertions in the ingest YAML keys file.

```text
given ingestion_params with keywords ["alpha", "beta"]
when build_sync_tasks(params)
then two tasks with task_id and keyword equal to alpha then beta

given ingestion_params with keywords [" gun control "]
when build_sync_tasks(params)
then one task with task_id and keyword equal to "gun control" (stripped), not quoted

given ingestion_params with keywords ["alpha", ""]
when build_sync_tasks(params)
then raise ValueError matching "non-empty strings"

given ingestion_params with keywords [] or keywords as a string or keywords missing and keyword missing
when build_sync_tasks(params)
then raise ValueError matching "keywords"

given ingestion_params with keyword ["alpha", "beta"] and no keywords key
when build_sync_tasks(params)
then two tasks for alpha and beta

given ingestion_params with keyword "example" and no keywords key
when build_sync_tasks(params)
then one task for example

given ingestion_params with keywords ["alpha"] and keyword "ignored"
when build_sync_tasks(params)
then one task for alpha

given Twitter YAML files under data_platform/ingestion/configs/twitter/
when each file is loaded
then ingestion_params does not contain keyword
and ingestion_params.keywords is a non-empty list of non-empty strings
and default.yaml keywords equals ["example"]
and limit_per_keyword is still present in files that already set it
```

## Implementation notes (implement-from-spec)

Files already exist. Scaffold means adding `_resolve_search_terms` as `raise NotImplementedError` and calling it from `build_sync_tasks` in place of `ingestion_params.get("keyword")`. Do not put the real key preference in until Phase 5.

Phase order, one Git commit per phase that changes the repo, and one commit per Phase 5 unit:

1. Phase 1 scope. Confirm caller, file tree, and out-of-scope. No product-code commit if nothing on disk changes.
2. Phase 2 scaffold. Add `_resolve_search_terms` that raises `NotImplementedError`. In `build_sync_tasks`, call it and map the returned strings to `TwitterTask` objects. Existing tests that call `build_sync_tasks` fail with `NotImplementedError` until Phase 5.
3. Phase 3 contracts. Confirm `_resolve_search_terms(ingestion_params: dict[str, Any]) -> list[str]`. Bodies stay stubs. Full auto. Do not wait for approval.
4. Phase 4 test design. Add the tests from the pseudocode. Resolution tests must fail for `NotImplementedError`. YAML tests fail until committed Twitter YAML is renamed.
5. Phase 5 units, in this order, one commit each:
   1. Implement `_resolve_search_terms` so `keywords` wins when present, `keyword` is the fallback, and missing or invalid terms raise. `build_sync_tasks` tests pass. Existing checkpoint tests pass again through the `keyword` fallback. YAML tests stay red.
   2. Rename `keyword` to `keywords` in every file under `data_platform/ingestion/configs/twitter/` so the YAML-key tests pass.
6. Phase 6. Run the must-pass commands. Confirm Bluesky, Reddit, `query_terms.py`, `twitter_client.py`, and `limit_per_keyword` are unchanged.

## Must pass

```bash
cd /workspace
PYTHONPATH=. uv run pytest tests/data_platform/ingestion/test_sync_twitter_checkpoint.py tests/data_platform/ingestion/test_ingest_yaml_keys.py tests/data_platform/ingestion/test_query_terms.py -q
```

Expected: exit 0.

```bash
cd /workspace
PYTHONPATH=. uv run pytest tests/data_platform/ingestion -q
```

Expected: exit 0. No new failures. Existing Twitter checkpoint tests still collected and passing. `test_query_terms.py` still passing with no edits.

## Must fail / not happen

- `data_platform/ingestion/sync_bluesky.py` changed.
- `limit_per_keyword` renamed in YAML or Python.
- Tweet row field `keyword` or `TwitterTask.keyword` renamed.
- A new shared ingest alias module or deprecation logger.
- `quote_query_term` behavior changed.
- Sibling GitHub issues 103, 104, 105, 106, and 108 to 116 implemented in this PR.
