# Step 1: Write one skip count after each append, and seed leftover names on resume

## Goal

Stop writing three platform skip-count names after `append_deduped_records`. Add a run-level `rows_skipped_as_duplicates` total and a `skipped_as_duplicates_by_record_type` map. On resume, seed those fields from leftover `posts_skipped_as_duplicates`, `comments_skipped_as_duplicates`, and `tweets_skipped_as_duplicates` when the new fields are missing.

## Caller / unit of work

**Main caller:** `data_platform/ingestion/sync_checkpoint.py` `increment_duplicate_skip_counters`, reached from:

- `data_platform/ingestion/sync_bluesky.py` `run_sync_tasks` after `append_deduped_records`
- `data_platform/ingestion/sync_twitter.py` `run_sync_tasks` after `append_deduped_records`
- `data_platform/ingestion/sync_reddit.py` `_append_subreddit_deduped_rows` after each post or comment append

**Task:** after a dedupe append, seed canonical skip counters from leftover names if needed, then add `result.skipped` to the run-level total and the matching record-type bucket.

**Out of scope:** ISO creation timestamps (GitHub issue 112). YAML operator keys. Dedupe policy (GitHub issue 110). `row_count` and `post_row_count` semantics. Disk backfill of completed `metadata.json` files. Deleting leftover skip-count names on resume. `CHANGELOG.md`. Experiment YAML under `experiments/`. Sibling GitHub issues 103 to 110 and 112 to 116.

## Files to inspect (read-only)

| Path | Why |
|------|-----|
| `/workspace/data_platform/ingestion/sync_checkpoint.py` | Pattern: `resolve_dedupe_policy` and `build_base_sync_metadata`. Home for the new helpers. |
| `/workspace/data_platform/ingestion/sync_bluesky.py` | `run_sync_tasks` currently writes `posts_skipped_as_duplicates`. `POSTS_RECORD_TYPE` is `app.bsky.feed.post`. |
| `/workspace/data_platform/ingestion/sync_twitter.py` | `run_sync_tasks` currently writes `tweets_skipped_as_duplicates`. `TWEETS_RECORD_TYPE` is `twitter.tweet`. |
| `/workspace/data_platform/ingestion/sync_reddit.py` | `_append_subreddit_deduped_rows` currently writes `posts_skipped_as_duplicates` and `comments_skipped_as_duplicates`. Record types are `reddit.post` and `reddit.comment`. |
| `/workspace/tests/data_platform/ingestion/test_sync_checkpoint.py` | Add helper tests. Pattern: `TestResolveLimitPerTask`. |
| `/workspace/tests/data_platform/ingestion/test_sync_bluesky_checkpoint.py` | Asserts `posts_skipped_as_duplicates`, including `test_resume_dedupes_against_records_from_completed_tasks`. |
| `/workspace/tests/data_platform/ingestion/test_sync_twitter_checkpoint.py` | Asserts `tweets_skipped_as_duplicates`. |
| `/workspace/tests/data_platform/ingestion/test_sync_reddit_checkpoint.py` | Asserts `comments_skipped_as_duplicates` and `posts_skipped_as_duplicates`. |

## Files allowed to change

- `/workspace/data_platform/ingestion/sync_checkpoint.py`
- `/workspace/data_platform/ingestion/sync_bluesky.py`
- `/workspace/data_platform/ingestion/sync_twitter.py`
- `/workspace/data_platform/ingestion/sync_reddit.py`
- `/workspace/tests/data_platform/ingestion/test_sync_checkpoint.py`
- `/workspace/tests/data_platform/ingestion/test_sync_bluesky_checkpoint.py`
- `/workspace/tests/data_platform/ingestion/test_sync_twitter_checkpoint.py`
- `/workspace/tests/data_platform/ingestion/test_sync_reddit_checkpoint.py`

Plan package files under `/workspace/docs/plans/2026-09-02_unify_duplicate_skip_counters_7762f8/` may already be on the branch. Do not edit them during implementation.

## Files forbidden to change

- `/workspace/data_platform/ingestion/configs/**`
- `/workspace/data_platform/utils/storage.py`
- `/workspace/data_platform/utils/deduplication.py`
- `/workspace/tests/data_platform/ingestion/conftest.py`
- `/workspace/tests/data_platform/ingestion/reddit_conftest.py`
- `/workspace/tests/data_platform/ingestion/twitter_conftest.py`
- `/workspace/CHANGELOG.md`
- `/workspace/experiments/**`
- Any file outside the allowed list, except git commits of this work

## Contracts to lock

Add module constants and helpers in `sync_checkpoint.py`:

```text
ROWS_SKIPPED_AS_DUPLICATES_KEY = "rows_skipped_as_duplicates"
SKIPPED_BY_RECORD_TYPE_KEY = "skipped_as_duplicates_by_record_type"

def bootstrap_duplicate_skip_counters(
    metadata: dict[str, Any],
    *,
    legacy_by_record_type: dict[str, str],
) -> None

def increment_duplicate_skip_counters(
    metadata: dict[str, Any],
    *,
    record_type: str,
    skipped: int,
    legacy_by_record_type: dict[str, str],
) -> None
```

`bootstrap_duplicate_skip_counters` presence rules:

- Build a seed map from leftover names. For each `(record_type, legacy_key)` in `legacy_by_record_type`, if `legacy_key` is present on metadata and that `record_type` is not already in the existing breakdown (or there is no breakdown yet), add `int(metadata[legacy_key])` to the seed map for that type.
- If `ROWS_SKIPPED_AS_DUPLICATES_KEY` is missing, set it to the sum of seeded breakdown values, or `0` when no leftover names are present.
- If `SKIPPED_BY_RECORD_TYPE_KEY` is missing, set it to the seeded breakdown dict, which may be `{}`.
- If both canonical keys already exist, do nothing. Do not copy leftover names again.
- Do not delete leftover names. Do not rewrite leftover names.

`increment_duplicate_skip_counters` behavior:

- Call `bootstrap_duplicate_skip_counters` first with the same `legacy_by_record_type`.
- Add `skipped` to `metadata[ROWS_SKIPPED_AS_DUPLICATES_KEY]`.
- Add `skipped` to `metadata[SKIPPED_BY_RECORD_TYPE_KEY][record_type]`, creating that bucket at `0` if missing.
- Never write leftover `legacy_by_record_type` values back onto metadata.

Platform wiring. Keep leftover maps as module-level dicts next to each platform's record-type constant:

- Bluesky: `record_type=POSTS_RECORD_TYPE`, `legacy_by_record_type={POSTS_RECORD_TYPE: "posts_skipped_as_duplicates"}`.
- Twitter: `record_type=TWEETS_RECORD_TYPE`, `legacy_by_record_type={TWEETS_RECORD_TYPE: "tweets_skipped_as_duplicates"}`.
- Reddit: pass the full map `{POSTS_RECORD_TYPE: "posts_skipped_as_duplicates", COMMENTS_RECORD_TYPE: "comments_skipped_as_duplicates"}` on every increment, including when only posts or only comments appended. Posts increment with `POSTS_RECORD_TYPE`. Comments increment with `COMMENTS_RECORD_TYPE`.

Do not add the new keys in `build_base_sync_metadata`. Do not add a metadata alias registry, a deprecation logger, or a migration tool.

Keep `run_sync_tasks`, `_append_subreddit_deduped_rows`, `append_deduped_records`, and `init_sync_metadata` signatures unchanged.

## Test design

Prefer calling `bootstrap_duplicate_skip_counters` and `increment_duplicate_skip_counters` for metadata shape. One test class per function. Update existing platform assertions to the canonical keys. Add one Bluesky resume test that starts from leftover names only.

```text
given empty metadata
when increment_duplicate_skip_counters(..., record_type=app.bsky.feed.post, skipped=2, leftover posts_skipped_as_duplicates)
then rows_skipped_as_duplicates == 2
and skipped_as_duplicates_by_record_type["app.bsky.feed.post"] == 2
and posts_skipped_as_duplicates is absent

given metadata with only posts_skipped_as_duplicates: 3
when increment_duplicate_skip_counters(..., record_type=app.bsky.feed.post, skipped=1, leftover posts_skipped_as_duplicates)
then rows_skipped_as_duplicates == 4
and skipped_as_duplicates_by_record_type["app.bsky.feed.post"] == 4
and posts_skipped_as_duplicates stays 3

given metadata with rows_skipped_as_duplicates: 9, skipped_as_duplicates_by_record_type {"app.bsky.feed.post": 9}, and posts_skipped_as_duplicates: 3
when bootstrap_duplicate_skip_counters(..., leftover posts_skipped_as_duplicates)
then rows_skipped_as_duplicates stays 9
and the breakdown stays {"app.bsky.feed.post": 9}

given metadata with posts_skipped_as_duplicates: 2 and comments_skipped_as_duplicates: 5
when bootstrap_duplicate_skip_counters(..., both Reddit leftover names)
then rows_skipped_as_duplicates == 7
and skipped_as_duplicates_by_record_type == {"reddit.post": 2, "reddit.comment": 5}

given empty metadata
when bootstrap_duplicate_skip_counters(..., leftover posts_skipped_as_duplicates)
then rows_skipped_as_duplicates == 0
and skipped_as_duplicates_by_record_type == {}

given Bluesky fetch that appends with no duplicate
when run_sync_tasks(...)
then rows_skipped_as_duplicates == 0
and skipped_as_duplicates_by_record_type["app.bsky.feed.post"] == 0
and posts_skipped_as_duplicates is absent

given Bluesky resume of a run whose metadata.json has only posts_skipped_as_duplicates: 3, then one new skip
when run_sync_tasks(...)
then rows_skipped_as_duplicates == 4
and skipped_as_duplicates_by_record_type["app.bsky.feed.post"] == 4
and posts_skipped_as_duplicates stays 3

given Twitter fetch that skips one duplicate
when run_sync_tasks(...)
then rows_skipped_as_duplicates == 1
and skipped_as_duplicates_by_record_type["twitter.tweet"] == 1
and tweets_skipped_as_duplicates is absent

given Reddit fetch that skips one comment duplicate
when run_sync_tasks(...)
then rows_skipped_as_duplicates == 1
and skipped_as_duplicates_by_record_type["reddit.comment"] == 1
and comments_skipped_as_duplicates is absent
```

Existing zero-skip paths that currently use `.get(legacy_key, 0) == 0` should assert canonical total `0` with `.get("rows_skipped_as_duplicates", 0)` when the increment helper may not have run. Paths that did append should assert the canonical keys directly and assert the leftover name is absent.

## Implementation notes (implement-from-spec)

Files already exist. Scaffold means adding both helpers as `raise NotImplementedError`, adding the two key constants, and calling `increment_duplicate_skip_counters` from Bluesky, Twitter, and Reddit in place of the leftover field writes. Do not put the real seed or add logic in until Phase 5.

Phase order, one Git commit per phase that changes the repo, and one commit per Phase 5 unit:

1. Phase 1 scope. Confirm caller, file tree, and out-of-scope. No product-code commit if nothing on disk changes.
2. Phase 2 scaffold. Add constants and both helpers that raise `NotImplementedError`. Wire Bluesky, Twitter, and Reddit append paths to `increment_duplicate_skip_counters`. Existing fetch tests that append fail with `NotImplementedError` until Phase 5.
3. Phase 3 contracts. Confirm signatures and docstrings state seed presence rules and that leftover names are never written back. Bodies stay stubs. Full auto. Do not wait for approval.
4. Phase 4 test design. Add the helper tests and the Bluesky leftover-name resume test. Update existing platform skip-count assertions to canonical keys. Helper tests and updated fetch tests must fail until Phase 5.
5. Phase 5 units, in this order, one commit each:
   1. Implement `bootstrap_duplicate_skip_counters` so leftover names seed missing canonical fields and existing canonical fields are left alone. Bootstrap tests pass. Increment tests and fetch tests stay red.
   2. Implement `increment_duplicate_skip_counters` so it bootstraps then adds `skipped` to the total and the record-type bucket without writing leftover names. Increment tests, platform fetch tests, and the leftover-name resume test pass.
6. Phase 6. Run the must-pass commands. Confirm leftover names are not written on new flushes. Confirm ISO timestamps, YAML, and `row_count` stay unchanged.

## Must pass

```bash
cd /workspace
PYTHONPATH=. uv run pytest tests/data_platform/ingestion/test_sync_checkpoint.py tests/data_platform/ingestion/test_sync_bluesky_checkpoint.py tests/data_platform/ingestion/test_sync_twitter_checkpoint.py tests/data_platform/ingestion/test_sync_reddit_checkpoint.py -q
```

Expected: exit 0.

```bash
cd /workspace
PYTHONPATH=. uv run pytest tests/data_platform/ingestion -q
```

Expected: exit 0. No new failures.

## Must fail / not happen

- Writing `posts_skipped_as_duplicates`, `comments_skipped_as_duplicates`, or `tweets_skipped_as_duplicates` on new sync flushes.
- Batch-rewriting existing run `metadata.json` on disk.
- Changing YAML configs or dedupe session behavior.
- Changing `row_count` or `post_row_count` semantics.
- Changing ISO creation timestamps (issue 112).
- `CHANGELOG.md` edited.
- Experiment YAML under `experiments/` edited.
- Sibling GitHub issues 103 to 110 and 112 to 116 implemented in this PR.
