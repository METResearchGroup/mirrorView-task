# Step 9: Unify duplicate-skip counters in ingest run metadata

## Goal

Each platform writes a different metadata key after `append_deduped_records` (`posts_skipped_as_duplicates`, `comments_skipped_as_duplicates`, `tweets_skipped_as_duplicates`). Operators and tooling should read one run-level total plus an optional per-record-type breakdown.

## Caller / unit of work

**Main callers:** post-append metadata updates in `sync_bluesky.py`, `sync_twitter.py`, and `sync_reddit.py` (`_append_task_records` / `_append_fetched_records`).

**Slice:** replace per-platform skip counter writes with shared helpers → same dedupe behavior, new metadata shape.

**Out of scope:** YAML operator keys, dedupe policy (step 8), `metadata.json` backfill for completed runs, preprocess/features/curate.

## Decision (locked)

- Canonical run-level key: `rows_skipped_as_duplicates` (`int`).
- Optional breakdown: `skipped_as_duplicates_by_record_type: dict[str, int]` with keys `app.bsky.feed.post`, `twitter.tweet`, `reddit.post`, `reddit.comment` as applicable to the sync.
- Stop writing `posts_skipped_as_duplicates`, `comments_skipped_as_duplicates`, and `tweets_skipped_as_duplicates` on new metadata flushes. Do not migrate old `metadata.json` files on disk.
- **Resume:** on the first increment in a resumed run, if canonical keys are missing, seed them from legacy keys, then only increment canonical keys for the remainder of the run:
  - Bluesky: `posts_skipped_as_duplicates` → `app.bsky.feed.post` (and run total).
  - Twitter: `tweets_skipped_as_duplicates` → `twitter.tweet`.
  - Reddit: `posts_skipped_as_duplicates` → `reddit.post`; `comments_skipped_as_duplicates` → `reddit.comment`; run total = sum of present legacy keys.
- Independently shippable. No YAML changes.

## Files to inspect (read-only)

| Path | Why |
|------|-----|
| `docs/plans/2026-09-02_unify_ingest_contracts_2aeaf9/plan.md` | Parent plan step 9 |
| `data_platform/ingestion/sync_bluesky.py` | `metadata["posts_skipped_as_duplicates"]` after `append_deduped_records` (~287) |
| `data_platform/ingestion/sync_twitter.py` | `metadata["tweets_skipped_as_duplicates"]` (~156) |
| `data_platform/ingestion/sync_reddit.py` | `posts_skipped_as_duplicates` / `comments_skipped_as_duplicates` in `_append_fetched_records` (~433–446) |
| `data_platform/ingestion/sync_checkpoint.py` | Shared helper home (`RECORD_TYPE_FILENAMES`, metadata flush helpers) |
| `tests/data_platform/ingestion/test_sync_bluesky_checkpoint.py` | Asserts `posts_skipped_as_duplicates` (incl. resume dedupe ~392) |
| `tests/data_platform/ingestion/test_sync_twitter_checkpoint.py` | Asserts `tweets_skipped_as_duplicates` |
| `tests/data_platform/ingestion/test_sync_reddit_checkpoint.py` | Asserts `comments_skipped_as_duplicates` |

## Files allowed to change

- `data_platform/ingestion/sync_checkpoint.py`
- `data_platform/ingestion/sync_bluesky.py`
- `data_platform/ingestion/sync_twitter.py`
- `data_platform/ingestion/sync_reddit.py`
- `tests/data_platform/ingestion/test_sync_checkpoint.py` (helper unit tests)
- `tests/data_platform/ingestion/test_sync_bluesky_checkpoint.py`
- `tests/data_platform/ingestion/test_sync_twitter_checkpoint.py`
- `tests/data_platform/ingestion/test_sync_reddit_checkpoint.py`
- `CHANGELOG.md` (after the PR exists, via write-changelog)

## Files forbidden to change

- All YAML under `data_platform/ingestion/configs/`
- `data_platform/utils/storage.py` (dedupe logic unchanged)
- Preprocess, features, curate, stimuli
- `experiments/` smoke artifacts and notes

## Contracts

```text
ROWS_SKIPPED_AS_DUPLICATES_KEY = "rows_skipped_as_duplicates"
SKIPPED_BY_RECORD_TYPE_KEY = "skipped_as_duplicates_by_record_type"

def bootstrap_duplicate_skip_counters(
    metadata: dict[str, Any],
    *,
    legacy_by_record_type: dict[str, str],
) -> None
  For each (record_type, legacy_key) in legacy_by_record_type:
    if legacy_key in metadata and record_type not in breakdown:
      add int(metadata[legacy_key]) to per-type breakdown seed.
  If ROWS_SKIPPED_AS_DUPLICATES_KEY missing:
    set it to sum of seeded breakdown values (or 0 if no legacy keys present).
  If SKIPPED_BY_RECORD_TYPE_KEY missing:
    set it to the seeded breakdown dict (may be {}).
  Idempotent: no-op when both canonical keys already exist.
  Does not delete or rewrite legacy keys (read-only for resume).

def increment_duplicate_skip_counters(
    metadata: dict[str, Any],
    *,
    record_type: str,
    skipped: int,
    legacy_by_record_type: dict[str, str],
) -> None
  Call bootstrap_duplicate_skip_counters first.
  metadata[ROWS_SKIPPED_AS_DUPLICATES_KEY] += skipped
  metadata[SKIPPED_BY_RECORD_TYPE_KEY][record_type] += skipped
  Never write legacy_by_record_type values back to metadata.
```

Platform wiring:

- Bluesky: `record_type=POSTS_RECORD_TYPE` (`app.bsky.feed.post`), `legacy_by_record_type={"app.bsky.feed.post": "posts_skipped_as_duplicates"}`.
- Twitter: `record_type="twitter.tweet"`, `legacy_by_record_type={"twitter.tweet": "tweets_skipped_as_duplicates"}`.
- Reddit `_append_fetched_records`: one increment per append path — posts use `reddit.post` / `posts_skipped_as_duplicates`; comments use `reddit.comment` / `comments_skipped_as_duplicates`. Pass the full Reddit legacy map on each call so bootstrap can seed both types when resuming.

## Tests (write first)

`TestDuplicateSkipCounters` in `tests/data_platform/ingestion/test_sync_checkpoint.py`:

- given empty metadata, when `increment_duplicate_skip_counters(..., skipped=2)`, then `rows_skipped_as_duplicates == 2` and breakdown matches.
- given metadata with only `posts_skipped_as_duplicates: 3`, when bootstrap then increment `skipped=1` for `app.bsky.feed.post`, then run total `4` and breakdown `app.bsky.feed.post: 4`.
- given metadata with `rows_skipped_as_duplicates` already set, when bootstrap runs, then legacy keys are not copied again (idempotent).
- given Reddit legacy `posts_skipped_as_duplicates: 2` and `comments_skipped_as_duplicates: 5`, when bootstrap with both legacy mappings, then run total `7` and both breakdown keys seeded.

Update platform checkpoint tests to assert canonical keys instead of legacy names:

- Bluesky dedupe and resume tests: `rows_skipped_as_duplicates` and `skipped_as_duplicates_by_record_type["app.bsky.feed.post"]`; assert legacy key absent after sync.
- Twitter: same for `twitter.tweet`.
- Reddit comment-dedupe test: `reddit.comment` breakdown; zero-skip paths still assert run total `0`.

Add one resume test (Bluesky or Reddit): pre-write `metadata.json` with a legacy skip counter only, resume sync, expect canonical total = legacy + new skips.

Follow `.cursor/skills/implement-plan-and-open-pr/UNIT_TESTING_STANDARDS.md`.

## Must pass

```bash
PYTHONPATH=. uv run pytest tests/data_platform/ingestion/test_sync_checkpoint.py tests/data_platform/ingestion/test_sync_bluesky_checkpoint.py tests/data_platform/ingestion/test_sync_twitter_checkpoint.py tests/data_platform/ingestion/test_sync_reddit_checkpoint.py -q
```

Exit 0.

## Must still pass

```bash
PYTHONPATH=. uv run pytest tests/data_platform/ingestion -q
```

Exit 0. No new failures.

## Must not happen

- Writing `posts_skipped_as_duplicates`, `comments_skipped_as_duplicates`, or `tweets_skipped_as_duplicates` on new sync flushes.
- Batch-rewriting existing run `metadata.json` on disk.
- Changing YAML configs or dedupe/session behavior.
- Changing `row_count` / `post_row_count` semantics.
