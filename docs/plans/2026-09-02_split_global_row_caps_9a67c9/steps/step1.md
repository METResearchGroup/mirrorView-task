# Step 1: Read a post cap or a comment cap, with the older mixed key as fallback

## Goal

Stop using one YAML name for a run-wide cap whose unit differs by platform. Add `ingestion_params.max_posts` as the primary Bluesky and Twitter cap, add `ingestion_params.max_comments` as the primary Reddit comment cap, keep `max_rows` as a fallback with today's platform meaning, and update committed configs that still set `max_rows`.

## Caller / unit of work

**Main caller:** `data_platform/ingestion/sync_checkpoint.py` `parse_max_posts` and `parse_max_comments`, reached from:

- `data_platform/ingestion/sync_bluesky.py` `run_sync_tasks`
- `data_platform/ingestion/sync_twitter.py` `run_sync_tasks`
- `data_platform/ingestion/sync_reddit.py` `run_sync_tasks`

**Task:** resolve the run-wide cap from YAML, then use that integer as the existing checkpoint stop and remaining-budget clamp.

**Out of scope:** Dedupe policy key collapse (GitHub issue 110). Capping Reddit `post_row_count` with `max_posts`. Renaming Bluesky `fetch_posts_for_keyword` parameter `max_rows`. Renaming Twitter `_remaining_row_budget`. Renaming `_effective_limit_per_keyword`. Per-task `limit_per_task`. Twitter `keywords`. Bluesky `author_filter`. Sibling GitHub issues 103 to 108 and 110 to 116. A generic YAML alias framework. A deprecation logger. `CHANGELOG.md`. Experiment YAML under `experiments/`.

## Files to inspect (read-only)

| Path | Why |
|------|-----|
| `/workspace/data_platform/ingestion/sync_checkpoint.py` | Today `parse_max_rows` and `stop_at_max_rows`. Pattern for aliases: `resolve_limit_per_task` |
| `/workspace/data_platform/ingestion/sync_bluesky.py` | `run_sync_tasks` currently does `parse_max_rows(ingestion_params)` then clamps remaining posts |
| `/workspace/data_platform/ingestion/sync_twitter.py` | `run_sync_tasks` currently does `parse_max_rows(ingestion_params)` then `_remaining_row_budget` |
| `/workspace/data_platform/ingestion/sync_reddit.py` | `run_sync_tasks` currently does `parse_max_rows(ingestion_params)` and stores comments in `row_count` |
| `/workspace/data_platform/ingestion/configs/bluesky/default.yaml` | `max_rows: 200` |
| `/workspace/data_platform/ingestion/configs/bluesky/smoke.yaml` | `max_rows: 100` |
| `/workspace/data_platform/ingestion/configs/bluesky/mirrorview_scale.yaml` | `max_rows: 20000` |
| `/workspace/data_platform/ingestion/configs/twitter/default.yaml` | `max_rows: 50` |
| `/workspace/data_platform/ingestion/configs/twitter/mirrorview.yaml` | `max_rows: 1000` |
| `/workspace/data_platform/ingestion/configs/twitter/mirrorview_scale.yaml` | `max_rows: 10000` |
| `/workspace/data_platform/ingestion/configs/twitter/mirrorview_scale_2.yaml` | `max_rows: 15000` |
| `/workspace/data_platform/ingestion/configs/twitter/keyword_politics_econ_7000.yaml` | `max_rows: 10000` with a trailing comment |
| `/workspace/data_platform/ingestion/configs/reddit/default.yaml` | `max_rows: 100` |
| `/workspace/tests/data_platform/ingestion/test_sync_checkpoint.py` | Replace `test_parse_max_rows_none_when_unset`. Pattern: `TestResolveLimitPerTask` |
| `/workspace/tests/data_platform/ingestion/test_sync_bluesky_checkpoint.py` | Leave `test_run_sync_tasks_caps_fetch_by_remaining_max_rows` on `max_rows`. Add a primary-key cap test |
| `/workspace/tests/data_platform/ingestion/test_sync_twitter_checkpoint.py` | Add a primary-key remaining-budget test. Pattern: `TestEffectiveLimitPerKeyword` |
| `/workspace/tests/data_platform/ingestion/test_sync_reddit_checkpoint.py` | Add primary-key and alias cap tests. Pattern: `test_run_sync_tasks_appends_per_subreddit` |
| `/workspace/tests/data_platform/ingestion/test_ingest_yaml_keys.py` | Add assertions that committed YAML dropped `max_rows` |
| `/workspace/tests/data_platform/ingestion/conftest.py` | Bluesky fixture has no run-wide cap. Do not change |
| `/workspace/tests/data_platform/ingestion/reddit_conftest.py` | Reddit fixture has no run-wide cap. Do not change |
| `/workspace/data_platform/ingestion/sync_checkpoint.py` `resolve_limit_per_task` | Alias pattern: if the primary key is present, do not fall back |

## Files allowed to change

- `/workspace/data_platform/ingestion/sync_checkpoint.py`
- `/workspace/data_platform/ingestion/sync_bluesky.py`
- `/workspace/data_platform/ingestion/sync_twitter.py`
- `/workspace/data_platform/ingestion/sync_reddit.py`
- `/workspace/data_platform/ingestion/configs/bluesky/default.yaml`
- `/workspace/data_platform/ingestion/configs/bluesky/smoke.yaml`
- `/workspace/data_platform/ingestion/configs/bluesky/mirrorview_scale.yaml`
- `/workspace/data_platform/ingestion/configs/twitter/default.yaml`
- `/workspace/data_platform/ingestion/configs/twitter/mirrorview.yaml`
- `/workspace/data_platform/ingestion/configs/twitter/mirrorview_scale.yaml`
- `/workspace/data_platform/ingestion/configs/twitter/mirrorview_scale_2.yaml`
- `/workspace/data_platform/ingestion/configs/twitter/keyword_politics_econ_7000.yaml`
- `/workspace/data_platform/ingestion/configs/reddit/default.yaml`
- `/workspace/tests/data_platform/ingestion/test_sync_checkpoint.py`
- `/workspace/tests/data_platform/ingestion/test_sync_bluesky_checkpoint.py`
- `/workspace/tests/data_platform/ingestion/test_sync_twitter_checkpoint.py`
- `/workspace/tests/data_platform/ingestion/test_sync_reddit_checkpoint.py`
- `/workspace/tests/data_platform/ingestion/test_ingest_yaml_keys.py`

Plan package files under `/workspace/docs/plans/2026-09-02_split_global_row_caps_9a67c9/` may already be on the branch. Do not edit them during implementation.

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
- `/workspace/data_platform/ingestion/configs/bluesky/trump_econ_iran.yaml`
- `/workspace/data_platform/ingestion/configs/bluesky/mirrorview.yaml`
- `/workspace/data_platform/ingestion/configs/bluesky/mirrorview2.yaml`
- `/workspace/data_platform/ingestion/configs/reddit/mirrorview.yaml`
- `/workspace/data_platform/ingestion/configs/reddit/mirrorview_scale.yaml`
- `/workspace/data_platform/ingestion/configs/reddit/mirrorview_scale_run_2.yaml`
- Any file outside the allowed list, except git commits of this work

## Contracts to lock

Add module constants and helpers in `sync_checkpoint.py`:

```text
MAX_POSTS_KEY = "max_posts"
MAX_COMMENTS_KEY = "max_comments"
MAX_ROWS_ALIAS = "max_rows"

def parse_max_posts(ingestion_params: dict[str, Any]) -> int | None:
def parse_max_comments(ingestion_params: dict[str, Any]) -> int | None:
def stop_at_record_cap(
    metadata: dict[str, Any],
    storage: StorageManager,
    output_dir: Path,
    record_cap: int | None,
) -> bool:
```

Behavior, matching `resolve_limit_per_task` presence rules, not a truthy `or` (because `0` is a valid cap):

- `parse_max_posts`: if `MAX_POSTS_KEY` is present (`"max_posts" in ingestion_params`), return `int(ingestion_params["max_posts"])` when the value is not None, else None. Do not fall back when the primary key is present.
- Else return `int(ingestion_params[MAX_ROWS_ALIAS])` when `max_rows` is present and not None, else None.
- `parse_max_comments`: same rules with `MAX_COMMENTS_KEY` as the primary key and `MAX_ROWS_ALIAS` as the fallback.
- If both the primary key and `max_rows` are set, the primary key wins.
- If neither key is set, return None.
- `parse_max_posts` must ignore `max_comments`. `parse_max_comments` must ignore `max_posts`.
- Delete `parse_max_rows`. Do not keep it as a wrapper.

Stop helper:

- Rename `stop_at_max_rows` to `stop_at_record_cap`. Keep the body. Compare `metadata["row_count"]` against `record_cap`.
- Rename `run_checkpointed_sync` parameter `max_rows_int` to `record_cap`. Call `stop_at_record_cap`.

Platform call sites:

- Bluesky `run_sync_tasks`: `max_posts_int = parse_max_posts(ingestion_params)`. Keep the remaining-budget clamp against `metadata["row_count"]`. Keep passing that remaining integer into `fetch_posts_for_keyword(..., max_rows=remaining)`. Pass `record_cap=max_posts_int` into `run_checkpointed_sync`.
- Twitter `run_sync_tasks`: `max_posts_int = parse_max_posts(ingestion_params)`. Keep `_remaining_row_budget(metadata, max_posts_int)` and `_effective_limit_per_keyword`. Pass `record_cap=max_posts_int` into `run_checkpointed_sync`.
- Reddit `run_sync_tasks`: `max_comments_int = parse_max_comments(ingestion_params)`. Pass `record_cap=max_comments_int` into `run_checkpointed_sync`. Do not compare against `post_row_count`.

Do not add a platform registry, a deprecation logger, or a migration tool.

Rename YAML `ingestion_params` run-wide cap keys in committed files that already set `max_rows`:

- Bluesky `default.yaml`, `smoke.yaml`, `mirrorview_scale.yaml`: `max_rows` to `max_posts`
- Twitter `default.yaml`, `mirrorview.yaml`, `mirrorview_scale.yaml`, `mirrorview_scale_2.yaml`, `keyword_politics_econ_7000.yaml`: `max_rows` to `max_posts`. Keep the trailing comment on `keyword_politics_econ_7000.yaml`.
- Reddit `default.yaml`: `max_rows` to `max_comments`

Keep numeric values. Default files must keep `200` (Bluesky posts), `50` (Twitter posts), and `100` (Reddit comments).

Do not add a run-wide cap to committed YAML that currently omits `max_rows`.

Keep `run_sync_tasks`, `fetch_posts_for_keyword`, `_remaining_row_budget`, and `sync_records` signatures unchanged except the `run_checkpointed_sync` parameter rename above.

## Test design

Prefer calling `parse_max_posts` and `parse_max_comments` for key resolution. One test class per function. Leave `test_run_sync_tasks_caps_fetch_by_remaining_max_rows` on `max_rows` so that Bluesky test keeps proving the fallback. Add YAML assertions in the ingest YAML keys file. Add one platform fetch test per caller that uses only the primary key.

```text
given ingestion_params with max_posts 7
when parse_max_posts(params)
then return 7

given ingestion_params with max_rows 4 and no max_posts
when parse_max_posts(params)
then return 4

given ingestion_params with max_posts 7 and max_rows 4
when parse_max_posts(params)
then return 7

given ingestion_params with max_posts 0
when parse_max_posts(params)
then return 0

given ingestion_params empty
when parse_max_posts(params)
then return None

given ingestion_params with max_posts None
when parse_max_posts(params)
then return None

given ingestion_params with max_comments 9 and no max_posts
when parse_max_posts(params)
then return None

given ingestion_params with max_comments 8
when parse_max_comments(params)
then return 8

given ingestion_params with max_rows 4 and no max_comments
when parse_max_comments(params)
then return 4

given ingestion_params with max_comments 8 and max_rows 4
when parse_max_comments(params)
then return 8

given ingestion_params with max_comments 0
when parse_max_comments(params)
then return 0

given ingestion_params empty
when parse_max_comments(params)
then return None

given ingestion_params with max_posts 7 and no max_comments
when parse_max_comments(params)
then return None

given metadata row_count 10 and two tasks, one pending
when stop_at_record_cap(..., record_cap=10)
then return True and the pending task is skipped

given Bluesky ingestion_params with max_posts 2, no max_rows, limit 5, two keywords
when run_sync_tasks(...)
then row_count is 2, first task completed, second task skipped

given Twitter ingestion_params with max_posts 8, no max_rows, remaining None
when _remaining_row_budget is computed from parse_max_posts and passed to _effective_limit_per_keyword
then the per-task limit is 8 when limit_per_task is 8

given Reddit ingestion_params with max_comments 1, no max_rows, two subreddits that each yield one comment
when run_sync_tasks(...)
then row_count is 1, first task completed, second task skipped

given Reddit ingestion_params with max_rows 1 and no max_comments, two subreddits that each yield one comment
when run_sync_tasks(...)
then row_count is 1, first task completed, second task skipped

given ingest YAML under data_platform/ingestion/configs/{bluesky,twitter,reddit}/
when each file is loaded
then ingestion_params does not contain max_rows
and bluesky and twitter files that set a run-wide cap use max_posts as an int
and reddit files that set a run-wide cap use max_comments as an int
and bluesky and twitter files do not contain max_comments
and reddit files do not contain max_posts
and bluesky/default.yaml max_posts equals 200
and twitter/default.yaml max_posts equals 50
and reddit/default.yaml max_comments equals 100
```

For the Twitter remaining-budget case, a focused test that `parse_max_posts({"max_posts": 8})` feeds `_remaining_row_budget` is enough if a full `run_sync_tasks` cap test would duplicate the Bluesky path. Prefer testing `parse_max_posts` plus `_remaining_row_budget(metadata, parse_max_posts(params))` returning `8 - row_count`.

## Implementation notes (implement-from-spec)

Files already exist. Scaffold means adding `parse_max_posts` and `parse_max_comments` as `raise NotImplementedError`, renaming `stop_at_max_rows` to `stop_at_record_cap` with the same body, renaming `run_checkpointed_sync`'s cap parameter, and calling the new parse helpers from the three fetch sites. Do not put the real key preference in until Phase 5. Keep `parse_max_rows` as a one-line forward to `parse_max_posts` during scaffold so existing imports fail with `NotImplementedError` rather than `ImportError`. Delete `parse_max_rows` in Phase 5.

Phase order, one Git commit per phase that changes the repo, and one commit per Phase 5 unit:

1. Phase 1 scope. Confirm caller, file tree, and out-of-scope. No product-code commit if nothing on disk changes.
2. Phase 2 scaffold. Add `MAX_POSTS_KEY`, `MAX_COMMENTS_KEY`, `MAX_ROWS_ALIAS`, and parse helpers that raise `NotImplementedError`. Rename the stop helper and the `run_checkpointed_sync` cap parameter. Wire Bluesky and Twitter to `parse_max_posts`, Reddit to `parse_max_comments`. Existing fetch-cap tests fail with `NotImplementedError` until Phase 5.
3. Phase 3 contracts. Confirm parse signatures return `int | None`. Bodies stay stubs. Full auto. Do not wait for approval.
4. Phase 4 test design. Add the tests from the pseudocode. Resolver and primary-key fetch tests must fail for `NotImplementedError`. YAML tests fail until committed YAML is renamed. Update the old `parse_max_rows` and `stop_at_max_rows` tests to the new names.
5. Phase 5 units, in this order, one commit each:
   1. Implement `parse_max_posts` and `parse_max_comments` so the primary key wins when present, `max_rows` is the fallback, and a missing cap returns None. Delete `parse_max_rows`. Resolver tests, the Bluesky alias remaining-budget test, and the Reddit alias cap test pass. YAML tests stay red.
   2. Rename `max_rows` to `max_posts` or `max_comments` in every committed file listed above so the YAML-key tests pass.
6. Phase 6. Run the must-pass commands. Confirm dedupe policy keys, `limit_per_task`, Bluesky `fetch_posts_for_keyword` parameter `max_rows`, Twitter `_remaining_row_budget`, and Reddit `post_row_count` handling are unchanged.

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

Expected: exit 0. No new failures. Existing Bluesky remaining-budget test still collected and passing through the older-key fallback.

## Must fail / not happen

- Dedupe policy keys collapsed (issue 110).
- Reddit `post_row_count` capped by `max_posts`.
- Bluesky `fetch_posts_for_keyword` parameter `max_rows` renamed.
- Twitter `_remaining_row_budget` renamed.
- A second identical stop helper named only for comments.
- A new generic ingest alias module or deprecation logger.
- `CHANGELOG.md` edited.
- Experiment YAML under `experiments/` edited.
- Committed YAML that currently omits `max_rows` given a new cap.
- Sibling GitHub issues 103 to 108 and 110 to 116 implemented in this PR.
