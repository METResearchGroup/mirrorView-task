# Step 1: Own length and language policy at preprocess

## Goal

Put Bluesky, Twitter, and Reddit length bounds in one preprocess-owned policy module. Keep the current numbers. Document that English is required at preprocess for every record type. Add Reddit's missing minimum-length gate. Do not change ingest fetch filters.

## Caller / unit of work

**Main caller:** `data_platform/preprocessing/preprocess_reddit.py` `COMMENT_TEXT_VALIDATORS`, reached from `filter_comments` and `preprocess_records`. Bluesky and Twitter callers already run length and English checks. They must keep using those checks, now backed by the shared constants.

**Task:** add `data_platform/preprocessing/content_filter_policy.py`, point existing Bluesky and Twitter length validators at those constants, add `check_if_valid_reddit_comment_min_length`, and insert it into `COMMENT_TEXT_VALIDATORS` after `check_if_body_not_removed`.

**Out of scope:** Ingest writers and YAML, including `min_comment_body_length` on Reddit ingest. PushShift experiment thresholds. Feature generation, curation, and stimuli sampling. Engagement-metric renaming. Configs-folder README hygiene. `CHANGELOG.md`. Sibling GitHub issues 103 to 115.

## Files to inspect (read-only)

| Path | Why |
|------|-----|
| `/workspace/data_platform/preprocessing/validators/validators.py` | `check_if_valid_post_length` uses `100` and `300`. `check_if_text_english` is the English gate. |
| `/workspace/data_platform/preprocessing/validators/twitter_validators.py` | `check_if_valid_twitter_post_length` uses `50` and `280`. |
| `/workspace/data_platform/preprocessing/validators/reddit_validators.py` | Reddit text checks. No length check today. |
| `/workspace/data_platform/preprocessing/preprocess_bluesky.py` | `POST_TEXT_VALIDATORS` already includes length and English. |
| `/workspace/data_platform/preprocessing/preprocess_twitter.py` | `POST_TEXT_VALIDATORS` already includes length and English. |
| `/workspace/data_platform/preprocessing/preprocess_reddit.py` | `COMMENT_TEXT_VALIDATORS` includes English and not length. |
| `/workspace/data_platform/ingestion/sync_reddit.py` | `min_comment_body_length` is ingest fetch only. Do not import preprocess policy. |
| `/workspace/data_platform/ingestion/configs/reddit/default.yaml` | Fetch default `min_comment_body_length: 30`. Leave it. |
| `/workspace/tests/data_platform/preprocessing/test_preprocess_twitter.py` | Existing Twitter length tests must still pass. |
| `/workspace/tests/data_platform/preprocessing/test_preprocess_reddit.py` | Existing Reddit validator tests, plus new min-length coverage. |
| `/workspace/.cursor/skills/implement-plan-and-open-pr/UNIT_TESTING_STANDARDS.md` | One test class per function. Arrange, act, assert. |

## Files allowed to change

- `/workspace/data_platform/preprocessing/content_filter_policy.py` (new)
- `/workspace/data_platform/preprocessing/validators/validators.py`
- `/workspace/data_platform/preprocessing/validators/twitter_validators.py`
- `/workspace/data_platform/preprocessing/validators/reddit_validators.py`
- `/workspace/data_platform/preprocessing/preprocess_reddit.py`
- `/workspace/tests/data_platform/preprocessing/test_content_filter_policy.py` (new)
- `/workspace/tests/data_platform/preprocessing/test_preprocess_reddit.py`

Plan package files under `/workspace/docs/plans/2026-09-02_preprocess_content_policy_93b116/` may already be on the branch. Do not edit them during implementation.

## Files forbidden to change

- `/workspace/data_platform/ingestion/**`
- `/workspace/data_platform/preprocessing/preprocess_bluesky.py`
- `/workspace/data_platform/preprocessing/preprocess_twitter.py`
- `/workspace/tests/data_platform/preprocessing/test_preprocess_twitter.py`
- `/workspace/experiments/fetch_reddit_pushshift_dump_2026_06_15/**`
- `/workspace/data_platform/generate_features/**`
- `/workspace/data_platform/curate/**`
- `/workspace/CHANGELOG.md`
- Any file outside the allowed list, except git commits of this work

## Contracts to lock

Add `/workspace/data_platform/preprocessing/content_filter_policy.py`:

```text
BLUESKY_POST_MIN_LENGTH: int = 100
BLUESKY_POST_MAX_LENGTH: int = 300
TWITTER_POST_MIN_LENGTH: int = 50
TWITTER_POST_MAX_LENGTH: int = 280
REDDIT_COMMENT_MIN_LENGTH: int = 30
```

Module docstring must state the per-record-type policy:

- Bluesky post: min 100, max 300, English required at preprocess
- Twitter post: min 50, max 280, English required at preprocess
- Reddit comment: min 30, no max, English required at preprocess
- English is `check_if_text_english` on all three platforms
- Reddit ingest `min_comment_body_length` is a fetch-time filter, not this policy

```text
check_if_valid_post_length(text: str) -> bool
  return BLUESKY_POST_MIN_LENGTH <= len(text) <= BLUESKY_POST_MAX_LENGTH

check_if_valid_twitter_post_length(text: str) -> bool
  return TWITTER_POST_MIN_LENGTH <= len(text) <= TWITTER_POST_MAX_LENGTH

check_if_valid_reddit_comment_min_length(text: str) -> bool
  return len(text) >= REDDIT_COMMENT_MIN_LENGTH
```

Do not strip text before measuring length. Bluesky and Twitter already measure `len(text)` that way.

`COMMENT_TEXT_VALIDATORS` in `/workspace/data_platform/preprocessing/preprocess_reddit.py`:

```text
check_if_body_not_removed
check_if_valid_reddit_comment_min_length
check_if_no_reddit_mentions
check_if_no_markdown_links
check_if_no_direct_urls
check_if_no_media_hosts
check_if_not_phone
check_if_text_english
```

Do not add a Reddit maximum. Do not import `content_filter_policy` from ingest. Do not change `check_if_text_english`.

## Test design

Location: `/workspace/tests/data_platform/preprocessing/test_content_filter_policy.py`

Import constants from `data_platform.preprocessing.content_filter_policy`. Import `check_if_valid_post_length` from `data_platform.preprocessing.validators.validators`. Import `check_if_valid_twitter_post_length` from `data_platform.preprocessing.validators.twitter_validators`. Import `check_if_valid_reddit_comment_min_length` from `data_platform.preprocessing.validators.reddit_validators`.

```text
given the policy module
when reading the named constants
then Bluesky min is 100 and max is 300
and Twitter min is 50 and max is 280
and Reddit min is 30

given text of 99, 100, 300, and 301 characters
when check_if_valid_post_length
then False, True, True, False

given text of 49, 50, 280, and 281 characters
when check_if_valid_twitter_post_length
then False, True, True, False

given text of 29 and 30 characters
when check_if_valid_reddit_comment_min_length
then False, True
```

One class per function: `TestContentFilterPolicy`, `TestCheckIfValidPostLength`, `TestCheckIfValidTwitterPostLength`, `TestCheckIfValidRedditCommentMinLength`.

Extend `/workspace/tests/data_platform/preprocessing/test_preprocess_reddit.py`:

```text
given an otherwise valid English body of 29 characters
when passes_all_validators
then False

given an otherwise valid English body of 30 characters
when passes_all_validators
then True

given filter_comments with one 29-character English row and one current valid row
when filter_comments
then only the valid row remains
```

Use these bodies, which langdetect already labels as English:

- 29 characters: `This is a short English note.`
- 30 characters: `This is clearly English text!!`

Existing Twitter length tests in `test_preprocess_twitter.py` stay as they are. Existing Reddit tests that use `_valid_body()` stay green because that body is longer than 30 characters.

## Implementation notes (implement-from-spec)

Full auto. Do not wait for approval.

Phase order, one Git commit per phase that changes the repo, and one commit per Phase 5 unit:

1. Phase 1 scope. Confirm callers, file tree, and out-of-scope. No product-code commit if nothing on disk changes.
2. Phase 2 scaffold. Add `content_filter_policy.py` with the constant names assigned to `0` and a module docstring placeholder. Add `check_if_valid_reddit_comment_min_length` that raises `NotImplementedError`. Add `test_content_filter_policy.py` with the import and empty test classes. Do not call the Reddit length check from `COMMENT_TEXT_VALIDATORS` yet. Do not change existing Bluesky or Twitter validators yet.
3. Phase 3 contracts. Set the constants to the locked numbers. Write the per-record-type policy docstring. Give `check_if_valid_reddit_comment_min_length` its signature and docstring. Body still raises `NotImplementedError`. Full auto.
4. Phase 4 test design. Add the failing tests. Constant-value tests pass because Phase 3 locked the numbers. Bluesky and Twitter length tests pass because current literals match those numbers. Reddit min-length tests fail because of `NotImplementedError` or because `COMMENT_TEXT_VALIDATORS` still has no length check.
5. Phase 5 units, in this order, one commit each:
   1. Point `check_if_valid_post_length` at the Bluesky constants.
   2. Point `check_if_valid_twitter_post_length` at the Twitter constants.
   3. Implement `check_if_valid_reddit_comment_min_length`. Direct Reddit length tests pass. `passes_all_validators` tests stay red until the caller tuple includes the check.
   4. Insert `check_if_valid_reddit_comment_min_length` into `COMMENT_TEXT_VALIDATORS` after `check_if_body_not_removed`. Reddit `passes_all_validators` and `filter_comments` tests pass.
6. Phase 6. Run the must-pass commands. Confirm ingest files are unchanged. Confirm Twitter and Bluesky numeric bounds are unchanged. Confirm `CHANGELOG.md` is unchanged.

## Must pass

```bash
cd /workspace
PYTHONPATH=. uv run pytest tests/data_platform/preprocessing/test_content_filter_policy.py tests/data_platform/preprocessing/test_preprocess_reddit.py tests/data_platform/preprocessing/test_preprocess_twitter.py -q
```

Expected: exit 0.

```bash
cd /workspace
PYTHONPATH=. uv run pytest tests/data_platform/preprocessing -q
```

Expected: exit 0 with no new failures.

## Must fail / not happen

- Bluesky bounds changed away from 100 and 300.
- Twitter bounds changed away from 50 and 280.
- Reddit preprocess given a maximum length.
- PushShift `20` and `300` imported into sync or preprocess.
- Length or language validators added to Bluesky or Twitter ingest.
- Reddit ingest `min_comment_body_length` removed or wired to preprocess constants.
- `check_if_text_english` replaced with a new language implementation.
- `CHANGELOG.md` edited.
- Sibling GitHub issues 103 to 115 implemented in this PR.
