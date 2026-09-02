# Step 1: Read one shared per-task fetch cap, with older keys as fallback

## Goal

Stop using three YAML names for the same per-checkpoint-task fetch cap. Add `ingestion_params.limit_per_task` as the shared key, keep Bluesky `limit`, Twitter `limit_per_keyword`, and Reddit `limit_per_subreddit` as fallbacks, and update committed configs that still set the older keys.

## Caller / unit of work

**Main caller:** `data_platform/ingestion/sync_checkpoint.py` `resolve_limit_per_task`, reached from:

- `data_platform/ingestion/sync_bluesky.py` `fetch_posts_for_keyword`
- `data_platform/ingestion/sync_twitter.py` `_effective_limit_per_keyword`
- `data_platform/ingestion/sync_reddit.py` `fetch_records_for_subreddit`

**Task:** resolve the per-task fetch cap from YAML, then use that integer as the existing per-task fetch limit.

**Out of scope:** `max_rows` (GitHub issue 109). Dedupe policy key collapse (GitHub issue 110). Renaming Reddit stats field `limit_per_subreddit`. Renaming `_effective_limit_per_keyword`. Twitter remaining-row clamp math. `TwitterTask.keyword`. Bluesky `author_filter`. Twitter `keywords`. Sibling GitHub issues 103 to 107 and 109 to 116. A generic YAML alias framework. A deprecation logger. `CHANGELOG.md`. Experiment YAML under `experiments/`.

## Files to inspect (read-only)

| Path | Why |
|------|-----|
| `/workspace/data_platform/ingestion/sync_checkpoint.py` | Add `resolve_limit_per_task` next to `parse_max_rows` |
| `/workspace/data_platform/ingestion/sync_bluesky.py` | `fetch_posts_for_keyword` currently does `int(ingestion_params["limit"])` |
| `/workspace/data_platform/ingestion/sync_twitter.py` | `_effective_limit_per_keyword` currently does `int(ingestion_params.get("limit_per_keyword", 25))` then clamps by remaining rows |
| `/workspace/data_platform/ingestion/sync_reddit.py` | `fetch_records_for_subreddit` currently does `int(ingestion_params["limit_per_subreddit"])` |
| `/workspace/data_platform/ingestion/configs/bluesky/*.yaml` | Six files set `limit` |
| `/workspace/data_platform/ingestion/configs/twitter/*.yaml` | Five files set `limit_per_keyword` |
| `/workspace/data_platform/ingestion/configs/reddit/*.yaml` | Four files set `limit_per_subreddit` |
| `/workspace/tests/data_platform/ingestion/test_sync_checkpoint.py` | Add resolver tests here. Pattern: `test_parse_max_rows_none_when_unset` |
| `/workspace/tests/data_platform/ingestion/test_sync_bluesky_checkpoint.py` | Add primary-key fetch tests. Leave `minimal_sync_config` on `limit` |
| `/workspace/tests/data_platform/ingestion/test_sync_twitter_checkpoint.py` | Add primary-key and default-25 tests. Leave `_minimal_twitter_sync_config` on `limit_per_keyword` |
| `/workspace/tests/data_platform/ingestion/test_sync_reddit_checkpoint.py` | Add primary-key fetch tests. Leave `minimal_reddit_sync_config` on `limit_per_subreddit` |
| `/workspace/tests/data_platform/ingestion/test_ingest_yaml_keys.py` | Replace `test_committed_twitter_yaml_keeps_limit_per_keyword` with shared-key assertions |
| `/workspace/tests/data_platform/ingestion/conftest.py` | Bluesky fixture `limit: 2` is the fallback. Do not change |
| `/workspace/tests/data_platform/ingestion/reddit_conftest.py` | Reddit fixture `limit_per_subreddit: 2` is the fallback. Do not change |
| `/workspace/data_platform/ingestion/sync_bluesky.py` `_resolve_search_author` | Alias pattern: prefer the new key, then the older key |
| `/workspace/data_platform/ingestion/sync_twitter.py` `_resolve_search_terms` | Alias pattern: if the new key is present, do not fall back |

## Files allowed to change

- `/workspace/data_platform/ingestion/sync_checkpoint.py`
- `/workspace/data_platform/ingestion/sync_bluesky.py`
- `/workspace/data_platform/ingestion/sync_twitter.py`
- `/workspace/data_platform/ingestion/sync_reddit.py`
- `/workspace/data_platform/ingestion/configs/bluesky/default.yaml`
- `/workspace/data_platform/ingestion/configs/bluesky/trump_econ_iran.yaml`
- `/workspace/data_platform/ingestion/configs/bluesky/smoke.yaml`
- `/workspace/data_platform/ingestion/configs/bluesky/mirrorview_scale.yaml`
- `/workspace/data_platform/ingestion/configs/bluesky/mirrorview2.yaml`
- `/workspace/data_platform/ingestion/configs/bluesky/mirrorview.yaml`
- `/workspace/data_platform/ingestion/configs/twitter/default.yaml`
- `/workspace/data_platform/ingestion/configs/twitter/mirrorview.yaml`
- `/workspace/data_platform/ingestion/configs/twitter/mirrorview_scale.yaml`
- `/workspace/data_platform/ingestion/configs/twitter/mirrorview_scale_2.yaml`
- `/workspace/data_platform/ingestion/configs/twitter/keyword_politics_econ_7000.yaml`
- `/workspace/data_platform/ingestion/configs/reddit/default.yaml`
- `/workspace/data_platform/ingestion/configs/reddit/mirrorview.yaml`
- `/workspace/data_platform/ingestion/configs/reddit/mirrorview_scale.yaml`
- `/workspace/data_platform/ingestion/configs/reddit/mirrorview_scale_run_2.yaml`
- `/workspace/tests/data_platform/ingestion/test_sync_checkpoint.py`
- `/workspace/tests/data_platform/ingestion/test_sync_bluesky_checkpoint.py`
- `/workspace/tests/data_platform/ingestion/test_sync_twitter_checkpoint.py`
- `/workspace/tests/data_platform/ingestion/test_sync_reddit_checkpoint.py`
- `/workspace/tests/data_platform/ingestion/test_ingest_yaml_keys.py`

Plan package files under `/workspace/docs/plans/2026-09-02_standardize_per_task_fetch_caps_9c0f69/` may already be on the branch. Do not edit them during implementation.

## Files forbidden to change

- `/workspace/data_platform/ingestion/query_terms.py`
- `/workspace/data_platform/ingestion/twitter_client.py`
- `/workspace/data_platform/ingestion/sync_clients.py`
- `/workspace/tests/data_platform/ingestion/conftest.py`
- `/workspace/tests/data_platform/ingestion/reddit_conftest.py`
- `/workspace/tests/data_platform/ingestion/twitter_conftest.py`
- `/workspace/tests/data_platform/ingestion/test_raw_row_timestamps.py`
- `/workspace/CHANGELOG.md`
- `/workspace/experiments/**`
- Any file outside the allowed list, except git commits of this work

## Contracts to lock

Add a module constant and helper in `sync_checkpoint.py`:

```text
LIMIT_PER_TASK_KEY = "limit_per_task"

def resolve_limit_per_task(
    ingestion_params: dict[str, Any],
    alias_key: str,
) -> int:
```

Behavior, matching `_resolve_search_terms` presence rules, not the truthy `or` used by `_resolve_search_author` (because `0` is a valid cap):

- If `LIMIT_PER_TASK_KEY` is present (`"limit_per_task" in ingestion_params`), return `int(ingestion_params["limit_per_task"])`. Do not fall back when the primary key is present.
- Else return `int(ingestion_params[alias_key])`. Missing alias raises `KeyError`, same as today's Bluesky `["limit"]` and Reddit `["limit_per_subreddit"]` reads.
- If both keys are set, `limit_per_task` wins even when the alias is also set.
- Do not clamp against `max_rows`. That clamp stays in each platform caller.

Platform constants and call sites:

- Bluesky: `BLUESKY_LIMIT_ALIAS = "limit"`. In `fetch_posts_for_keyword`, replace `int(ingestion_params["limit"])` with `resolve_limit_per_task(ingestion_params, BLUESKY_LIMIT_ALIAS)`. Keep the existing `max_rows` `min` clamp after that.
- Twitter: `TWITTER_LIMIT_ALIAS = "limit_per_keyword"` and `TWITTER_DEFAULT_LIMIT_PER_TASK = 25`. In `_effective_limit_per_keyword`, if neither `limit_per_task` nor `limit_per_keyword` is present, use `TWITTER_DEFAULT_LIMIT_PER_TASK`. Else call `resolve_limit_per_task(ingestion_params, TWITTER_LIMIT_ALIAS)`. Keep `max(0, min(per_keyword, remaining))` when `remaining` is not None. Do not rename `_effective_limit_per_keyword`.
- Reddit: `REDDIT_LIMIT_ALIAS = "limit_per_subreddit"`. In `fetch_records_for_subreddit`, replace `int(ingestion_params["limit_per_subreddit"])` with `resolve_limit_per_task(ingestion_params, REDDIT_LIMIT_ALIAS)`. Keep stats field `"limit_per_subreddit"` as the resolved integer. Do not rename that stats key.

Do not add a platform registry, a deprecation logger, or a migration tool.

Rename YAML `ingestion_params` cap keys to `limit_per_task` in every committed file under:

- `/workspace/data_platform/ingestion/configs/bluesky/` (`limit` to `limit_per_task`)
- `/workspace/data_platform/ingestion/configs/twitter/` (`limit_per_keyword` to `limit_per_task`)
- `/workspace/data_platform/ingestion/configs/reddit/` (`limit_per_subreddit` to `limit_per_task`)

Keep numeric values. Default files must keep `50` (Bluesky), `25` (Twitter), and `5` (Reddit).

Keep `fetch_posts_for_keyword`, `_effective_limit_per_keyword`, `fetch_records_for_subreddit`, and `sync_records` signatures unchanged.

## Test design

Prefer calling `resolve_limit_per_task` for key resolution. One test class per function. Leave existing `run_sync_tasks` fixtures on the older keys so those tests keep proving the fallback. Add YAML assertions in the ingest YAML keys file. Add one platform fetch test per caller that uses only `limit_per_task`.

```text
given ingestion_params with limit_per_task 7 and alias_key "limit"
when resolve_limit_per_task(params, "limit")
then return 7

given ingestion_params with limit 4 and no limit_per_task
when resolve_limit_per_task(params, "limit")
then return 4

given ingestion_params with limit_per_keyword 9 and no limit_per_task
when resolve_limit_per_task(params, "limit_per_keyword")
then return 9

given ingestion_params with limit_per_subreddit 3 and no limit_per_task
when resolve_limit_per_task(params, "limit_per_subreddit")
then return 3

given ingestion_params with limit_per_task 7 and limit 4
when resolve_limit_per_task(params, "limit")
then return 7

given ingestion_params with limit_per_task 0
when resolve_limit_per_task(params, "limit")
then return 0

given ingestion_params empty and alias_key "limit"
when resolve_limit_per_task(params, "limit")
then raise KeyError

given Bluesky ingestion_params with limit_per_task 1 and no limit
when fetch_posts_for_keyword(...)
then collect 1 row

given Twitter ingestion_params with limit_per_task 8, no limit_per_keyword, remaining None
when _effective_limit_per_keyword(params, None)
then return 8

given Twitter ingestion_params with neither cap key, remaining None
when _effective_limit_per_keyword(params, None)
then return 25

given Twitter ingestion_params with limit_per_task 10 and remaining 3
when _effective_limit_per_keyword(params, 3)
then return 3

given Reddit ingestion_params with limit_per_task 1 and no limit_per_subreddit
when fetch_records_for_subreddit(...)
then the listing fetch uses limit 1

given ingest YAML under data_platform/ingestion/configs/{bluesky,twitter,reddit}/
when each file is loaded
then ingestion_params does not contain limit, limit_per_keyword, or limit_per_subreddit
and ingestion_params.limit_per_task is an int
and bluesky/default.yaml limit_per_task equals 50
and twitter/default.yaml limit_per_task equals 25
and reddit/default.yaml limit_per_task equals 5
```

## Implementation notes (implement-from-spec)

Files already exist. Scaffold means adding `resolve_limit_per_task` as `raise NotImplementedError` and calling it from the three fetch sites in place of the inline YAML reads. Do not put the real key preference in until Phase 5. Twitter's neither-key default of 25 may stay in `_effective_limit_per_keyword` during scaffold so that helper still has a path when both keys are absent.

Phase order, one Git commit per phase that changes the repo, and one commit per Phase 5 unit:

1. Phase 1 scope. Confirm caller, file tree, and out-of-scope. No product-code commit if nothing on disk changes.
2. Phase 2 scaffold. Add `LIMIT_PER_TASK_KEY` and `resolve_limit_per_task` that raises `NotImplementedError`. Wire Bluesky, Twitter, and Reddit fetch to call it. Existing fetch tests fail with `NotImplementedError` until Phase 5.
3. Phase 3 contracts. Confirm `resolve_limit_per_task(ingestion_params: dict[str, Any], alias_key: str) -> int`. Bodies stay stubs. Full auto. Do not wait for approval.
4. Phase 4 test design. Add the tests from the pseudocode. Resolver and primary-key fetch tests must fail for `NotImplementedError`. YAML tests fail until committed YAML is renamed.
5. Phase 5 units, in this order, one commit each:
   1. Implement `resolve_limit_per_task` so `limit_per_task` wins when present, the alias is the fallback, and a missing alias raises `KeyError`. Wire Twitter's default 25 when neither key is present. Resolver tests and existing alias-based checkpoint tests pass. YAML tests stay red.
   2. Rename the older cap keys to `limit_per_task` in every committed file under `data_platform/ingestion/configs/{bluesky,twitter,reddit}/` so the YAML-key tests pass.
6. Phase 6. Run the must-pass commands. Confirm `max_rows` handling, dedupe policy keys, Reddit stats field `limit_per_subreddit`, and `_effective_limit_per_keyword` name are unchanged.

## Must pass

```bash
cd /workspace
PYTHONPATH=. uv run pytest tests/data_platform/ingestion/test_sync_checkpoint.py tests/data_platform/ingestion/test_sync_bluesky_checkpoint.py tests/data_platform/ingestion/test_sync_twitter_checkpoint.py tests/data_platform/ingestion/test_sync_reddit_checkpoint.py tests/data_platform/ingestion/test_ingest_yaml_keys.py -q
```

Expected: exit 0.

```bash
cd /workspace
PYTHONPATH=. uv run pytest tests/data_platform/ingestion -q
```

Expected: exit 0. No new failures. Existing Bluesky, Twitter, and Reddit checkpoint tests still collected and passing through the older-key fallback.

## Must fail / not happen

- `max_rows` split or a second run-wide cap key (issue 109).
- Dedupe policy keys collapsed (issue 110).
- Reddit stats field `limit_per_subreddit` renamed.
- `_effective_limit_per_keyword` renamed.
- A new generic ingest alias module or deprecation logger.
- `CHANGELOG.md` edited.
- Experiment YAML under `experiments/` edited.
- Sibling GitHub issues 103 to 107 and 109 to 116 implemented in this PR.
