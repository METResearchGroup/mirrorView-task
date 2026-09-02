# Step 14: Own content-length and language policy at preprocess

## Goal

Length and language gates for stimuli-ready text live in one preprocess-owned policy. Bluesky and Twitter already enforce length and English at preprocess; Reddit enforces English but not length. This PR centralizes the numeric thresholds as named constants, documents the per-record-type policy, and adds Reddit’s missing minimum-length gate at preprocess without changing ingest fetch filters or importing PushShift experiment thresholds.

## Caller / unit of work

**Main callers:** `preprocess_bluesky.py`, `preprocess_twitter.py`, `preprocess_reddit.py` → `COMMENT_TEXT_VALIDATORS` / `POST_TEXT_VALIDATORS` tuples → validator functions in `data_platform/preprocessing/validators/`.

**Slice:** add `content_filter_policy.py` → wire constants into existing length validators → add Reddit min-length validator → tests.

**Out of scope:** Bluesky/Twitter ingest filters, Reddit ingest `min_comment_body_length` behavior, PushShift experiment code, features/curate/stimuli, runbook edits.

## Decision (locked)

- New module `data_platform/preprocessing/content_filter_policy.py` is the single source of truth for per-record-type length bounds and a short policy docstring stating that **English is required at preprocess for all platforms** via `check_if_text_english`.
- **Do not change numeric thresholds** — only replace literals with named constants:
  - Bluesky post: min `100`, max `300` (`check_if_valid_post_length` in `validators.py`).
  - Twitter post: min `50`, max `280` (`check_if_valid_twitter_post_length` in `twitter_validators.py`).
  - Reddit comment: min `30`, **no max** (new validator; aligns with ingest default `min_comment_body_length: 30`, not PushShift `20`–`300`).
- **Language:** keep `check_if_text_english` as the preprocess English gate; it already appears in all three `preprocess_*.py` validator tuples — no new language validator.
- **Reddit preprocess** currently has no length validator — add one using `REDDIT_COMMENT_MIN_LENGTH` and append it to `COMMENT_TEXT_VALIDATORS` (place after `check_if_body_not_removed`, before mention/URL validators).
- **Ingest:** Reddit `min_comment_body_length` stays a cheap fetch-time filter in `sync_reddit.py` (YAML default `30`). Do **not** add length or language filters to Bluesky or Twitter ingest. Do **not** import `content_filter_policy` from ingest.
- Do **not** wire `experiments/fetch_reddit_pushshift_dump_2026_06_15/` (`MIN_BODY_LEN = 20`, `MAX_BODY_LEN = 300`) into sync or preprocess.
- Independently shippable; no dependency on other plan steps.

## Files to inspect (read-only)

| Path | Why |
|------|-----|
| `docs/plans/2026-09-02_unify_ingest_contracts_2aeaf9/plan.md` | Parent plan step 14 summary |
| `data_platform/preprocessing/validators/validators.py` | `check_if_valid_post_length`, `check_if_text_english` |
| `data_platform/preprocessing/validators/twitter_validators.py` | `check_if_valid_twitter_post_length` |
| `data_platform/preprocessing/validators/reddit_validators.py` | Reddit-specific validators; home for new min-length check |
| `data_platform/preprocessing/preprocess_bluesky.py` | `POST_TEXT_VALIDATORS` tuple |
| `data_platform/preprocessing/preprocess_twitter.py` | `POST_TEXT_VALIDATORS` tuple |
| `data_platform/preprocessing/preprocess_reddit.py` | `COMMENT_TEXT_VALIDATORS` — no length gate today |
| `data_platform/ingestion/sync_reddit.py` | `min_comment_body_length` fetch filter (~line 289) |
| `data_platform/ingestion/configs/reddit/default.yaml` | `min_comment_body_length: 30` |
| `experiments/fetch_reddit_pushshift_dump_2026_06_15/config.py` | Out-of-scope `20`/`300` — do not import |
| `tests/data_platform/preprocessing/test_preprocess_twitter.py` | Existing Twitter length parametrized tests |
| `tests/data_platform/preprocessing/test_preprocess_reddit.py` | Reddit validator / filter tests |
| `tests/data_platform/preprocessing/test_preprocess_bluesky.py` | Bluesky preprocess integration tests |

## Files allowed to change

- `data_platform/preprocessing/content_filter_policy.py` (new)
- `data_platform/preprocessing/validators/validators.py`
- `data_platform/preprocessing/validators/twitter_validators.py`
- `data_platform/preprocessing/validators/reddit_validators.py`
- `data_platform/preprocessing/preprocess_reddit.py`
- `tests/data_platform/preprocessing/test_content_filter_policy.py` (new)
- `tests/data_platform/preprocessing/test_preprocess_reddit.py`
- `tests/data_platform/preprocessing/test_preprocess_twitter.py` (only if imports move; behavior unchanged)
- `CHANGELOG.md`

## Files forbidden to change

- `data_platform/ingestion/sync_bluesky.py`
- `data_platform/ingestion/sync_twitter.py`
- `data_platform/ingestion/sync_reddit.py`
- All YAML under `data_platform/ingestion/configs/`
- `experiments/fetch_reddit_pushshift_dump_2026_06_15/`
- `data_platform/generate_features/`, `data_platform/curate/`, stimuli sampling
- `docs/runbooks/HOW_TO_GET_POSTS_FOR_STIMULI_DATASET.md` (follow-up doc pass optional; not required for this PR)

## Contracts

```text
# data_platform/preprocessing/content_filter_policy.py

BLUESKY_POST_MIN_LENGTH: int = 100
BLUESKY_POST_MAX_LENGTH: int = 300
TWITTER_POST_MIN_LENGTH: int = 50
TWITTER_POST_MAX_LENGTH: int = 280
REDDIT_COMMENT_MIN_LENGTH: int = 30
# Module docstring: per-record-type bounds above; English required at preprocess
# for bluesky.post, twitter.tweet, reddit.comment via check_if_text_english.

check_if_valid_post_length(text) -> bool
  return BLUESKY_POST_MIN_LENGTH <= len(text) <= BLUESKY_POST_MAX_LENGTH

check_if_valid_twitter_post_length(text) -> bool
  return TWITTER_POST_MIN_LENGTH <= len(text) <= TWITTER_POST_MAX_LENGTH

check_if_valid_reddit_comment_min_length(text) -> bool   # new, in reddit_validators.py
  return len(text) >= REDDIT_COMMENT_MIN_LENGTH

COMMENT_TEXT_VALIDATORS (preprocess_reddit.py)
  ... existing validators ...
  includes check_if_valid_reddit_comment_min_length
  still ends with check_if_text_english
```

Ingest contract unchanged: `sync_reddit` continues `min_comment_body_length = int(ingestion_params.get("min_comment_body_length", 30))` at fetch time only.

## Tests (write first)

`TestContentFilterPolicy` in `tests/data_platform/preprocessing/test_content_filter_policy.py`:

- given module constants, then Bluesky/Twitter/Reddit values match locked thresholds (`100`/`300`, `50`/`280`, `30` min only).

`TestBlueskyPostLength` (same file or colocated with policy tests):

- given text at `99`, `100`, `300`, `301` chars, then `check_if_valid_post_length` matches prior behavior.

`TestRedditCommentMinLength` in `test_preprocess_reddit.py` or `test_content_filter_policy.py`:

- given body shorter than 30 chars (but otherwise valid), then `passes_all_validators` is False.
- given body at exactly 30 chars (otherwise valid English comment), then True.
- given `filter_comments` with one short and one valid row, then only the valid row remains.

Existing `test_check_if_valid_twitter_post_length` in `test_preprocess_twitter.py` must still pass unchanged thresholds.

Follow `.cursor/skills/implement-plan-and-open-pr/UNIT_TESTING_STANDARDS.md`. One test class per function under test.

## Must pass

```bash
PYTHONPATH=. uv run pytest tests/data_platform/preprocessing/test_content_filter_policy.py tests/data_platform/preprocessing/test_preprocess_reddit.py tests/data_platform/preprocessing/test_preprocess_twitter.py -q
```

Exit 0.

## Must still pass

```bash
PYTHONPATH=. uv run pytest tests/data_platform/preprocessing -q
```

Exit 0. No new failures.

## Must not happen

- Bluesky `100`–`300` or Twitter `50`–`280` numeric bounds changed.
- PushShift `20`–`300` imported into sync or preprocess.
- Length or language validators added to Bluesky or Twitter ingest.
- Reddit ingest `min_comment_body_length` removed or wired to preprocess constants.
- Replacing `check_if_text_english` with a new language implementation.
