# Step 12: Add canonical author fields at preprocess

## Goal

Downstream stages need one author-handle column name across platforms. Raw ingest keeps platform-native author fields; preprocess adds shared `author_handle` (and `author_id` only when the platform already has one).

## Caller / unit of work

**Main caller:** `data_platform/preprocessing/runner.py` → `preprocess_records` (after `add_canonical_text_column`, before `apply_text_transform`).

**Slice:** copy or passthrough author fields onto canonical columns → validate preprocessed rows on write → existing filter/save unchanged in meaning.

**Out of scope:** raw ingest column names; `source_record_id` (step 13); stimuli sampling (step 11); feature/curate consumers switching to `author_handle` (they may read it later; this PR only writes it).

## Decision (locked)

- **Raw ingest unchanged:** Bluesky `author_handle`; Reddit `author`; Twitter `username` + `author_id`. Do not add `author_handle` to `SyncRedditCommentModel`, `SyncRedditPostModel`, or `SyncTwitterPostModel`.
- **Preprocess adds `author_handle` on every platform:**
  - Bluesky: passthrough — column already named `author_handle` on raw rows; helper must not duplicate or overwrite.
  - Reddit: copy `author` → `author_handle`; keep `author`.
  - Twitter: copy `username` → `author_handle`; keep `username`.
- **`author_id` only when native:** Twitter passthrough (`author_id` already on raw). Bluesky and Reddit: **omit the column** from preprocessed output — do not write empty strings or `None` placeholders.
- **Pydantic `extra="forbid"`:** extend preprocess-only models so new columns validate on preprocessed load/write. `PreprocessedRedditCommentModel` already exists (`text`). Add `author_handle` there. Add `PreprocessedTwitterPostModel` with `author_handle` (inherits `author_id` from `SyncTwitterPostModel`). Bluesky needs no new model — `SyncBlueskyPostModel` already declares `author_handle` and matches preprocessed shape.
- **Mirror the text helper:** `add_canonical_author_columns(df, spec)` alongside `add_canonical_text_column`, with platform source columns on `PreprocessPlatformSpec` (see Contracts).
- **Row validators unchanged:** Reddit `filter_records` / `check_if_not_automoderator` still read native `author`, not `author_handle`.
- **Independently shippable:** one PR; no bundled step 11 or 13 work.

## Files to inspect (read-only)

| Path | Why |
|------|-----|
| `docs/plans/2026-09-02_unify_ingest_contracts_2aeaf9/plan.md` | Parent plan step 12 |
| `data_platform/preprocessing/runner.py` | `add_canonical_text_column`, `preprocess_records`, `AUTHOR_COLUMN`, `PreprocessPlatformSpec` |
| `data_platform/preprocessing/preprocess_bluesky.py` | `BLUESKY_SPEC` |
| `data_platform/preprocessing/preprocess_reddit.py` | `REDDIT_SPEC`, row validators on `author` |
| `data_platform/preprocessing/preprocess_twitter.py` | `TWITTER_SPEC` |
| `data_platform/models/sync.py` | `Sync*` vs `PreprocessedRedditCommentModel` |
| `data_platform/utils/storage.py` | `RedditStorageManager` preprocessed model swap; Bluesky/Twitter model wiring |
| `data_platform/utils/platform_specific_columns.py` | `CANONICAL_TEXT_COLUMN` pattern |
| `tests/data_platform/preprocessing/test_add_canonical_text_column.py` | Helper test shape |
| `tests/data_platform/preprocessing/test_preprocess_reddit.py` | End-to-end preprocess assertions |
| `tests/data_platform/preprocessing/test_preprocess_twitter.py` | End-to-end preprocess assertions |
| `tests/data_platform/preprocessing/test_preprocess_bluesky.py` | Bluesky preprocess coverage |
| `tests/data_platform/ingestion/reddit_conftest.py` | `mock_comment_row` (`author`) |
| `tests/data_platform/ingestion/twitter_conftest.py` | `mock_tweet_row` (`username`, `author_id`) |
| `tests/data_platform/conftest.py` | `make_post_row` (`author_handle`) |

## Files allowed to change

- `data_platform/preprocessing/runner.py`
- `data_platform/preprocessing/preprocess_bluesky.py` (spec fields only, if needed)
- `data_platform/preprocessing/preprocess_reddit.py` (spec fields only, if needed)
- `data_platform/preprocessing/preprocess_twitter.py` (spec fields only, if needed)
- `data_platform/models/sync.py` (`PreprocessedRedditCommentModel`, new `PreprocessedTwitterPostModel`)
- `data_platform/utils/platform_specific_columns.py` (canonical author column constant)
- `data_platform/utils/storage.py` (Twitter preprocessed model on `StorageStage.PREPROCESSED`)
- `tests/data_platform/preprocessing/test_add_canonical_author_columns.py` (new)
- `tests/data_platform/preprocessing/test_add_canonical_text_column.py` (only if shared imports/fixtures move)
- `tests/data_platform/preprocessing/test_preprocess_reddit.py`
- `tests/data_platform/preprocessing/test_preprocess_twitter.py`
- `tests/data_platform/preprocessing/test_preprocess_bluesky.py` (if adding author assertions)
- `CHANGELOG.md`

## Files forbidden to change

- `data_platform/ingestion/**` (raw author columns and sync writers)
- `SyncBlueskyPostModel`, `SyncRedditCommentModel`, `SyncRedditPostModel`, `SyncTwitterPostModel` field lists (no new fields on raw sync models)
- Stimuli / curate / feature generation (unless a test breaks only because preprocessed CSV schema changed — fix the test assertion, not downstream readers)
- `source_record_id` or any step 13 join renames
- Ingest YAML configs

## Contracts

```text
CANONICAL_AUTHOR_HANDLE_COLUMN: str = "author_handle"
CANONICAL_AUTHOR_ID_COLUMN: str = "author_id"   # documentation only; not written on Bluesky/Reddit

@dataclass(frozen=True)
class PreprocessPlatformSpec:
  ...
  author_handle_source_column: str | None = None
    None → author_handle already on the frame (Bluesky).
    Non-None → copy str(source) onto author_handle (Reddit: "author"; Twitter: "username").
  preprocessed_model_cls: type[BaseModel] | None = None
    When set, validate each output row with this model before write (Reddit/Twitter).
    Bluesky may omit (SyncBlueskyPostModel already matches).

add_canonical_author_columns(df: pd.DataFrame, spec: PreprocessPlatformSpec) -> pd.DataFrame
  Returns a new frame; does not mutate input.
  When author_handle_source_column is None:
    require CANONICAL_AUTHOR_HANDLE_COLUMN present; leave values unchanged.
  Else:
    require source column present; set author_handle = source.map(str); keep source column.
  Do not add author_id unless it already exists on the input frame (Twitter only today).
  Do not add author_id with empty values for Bluesky/Reddit.

preprocess_records(...):
  records = add_canonical_text_column(records, spec)
  records = add_canonical_author_columns(records, spec)
  ... apply_text_transform / filter_records / save_preprocessed unchanged ...

PreprocessedRedditCommentModel(SyncRedditCommentModel):
  text: str
  author_handle: str

PreprocessedTwitterPostModel(SyncTwitterPostModel):
  author_handle: str
  # author_id inherited from SyncTwitterPostModel
```

Platform spec wiring:

- Bluesky: `author_handle_source_column=None`; `preprocessed_model_cls=None` (or `SyncBlueskyPostModel`).
- Reddit: `author_handle_source_column="author"`; `preprocessed_model_cls=PreprocessedRedditCommentModel`.
- Twitter: `author_handle_source_column="username"`; `preprocessed_model_cls=PreprocessedTwitterPostModel`; `TwitterStorageManager` uses `PreprocessedTwitterPostModel` when `stage == PREPROCESSED` (mirror Reddit).

## Tests (write first)

New `TestAddCanonicalAuthorColumns` in `tests/data_platform/preprocessing/test_add_canonical_author_columns.py` (mirror `test_add_canonical_text_column.py`).

- given Reddit frame with `author="regular_user"`, when `add_canonical_author_columns` with `REDDIT_SPEC`, then `author_handle == "regular_user"` and `author` unchanged; `author_id` not in columns.
- given Twitter frame with `username="handle"` and `author_id="123"`, when helper runs with `TWITTER_SPEC`, then `author_handle == "handle"`, `username` and `author_id` unchanged.
- given Bluesky frame with `author_handle="a.bsky.social"`, when helper runs with `BLUESKY_SPEC`, then value unchanged; `author_id` not in columns.
- given Reddit frame missing `author`, then `KeyError`.
- given Bluesky frame missing `author_handle`, then `KeyError`.

Extend end-to-end preprocess tests:

- `test_preprocess_records_writes_output` (Reddit): saved row has `author_handle == author`; no `author_id` column.
- `test_preprocess_records_writes_output` (Twitter): saved row has `author_handle == username` and `author_id` preserved.
- Add or extend Bluesky test: preprocessed CSV still has `author_handle` equal to raw value; no `author_id` column.

Reload preprocessed CSVs through `StorageManager(StorageStage.PREPROCESSED, ...)` so pydantic validation runs.

Follow `.cursor/skills/implement-plan-and-open-pr/UNIT_TESTING_STANDARDS.md`. One test class per function for the new helper.

## Must pass

```bash
PYTHONPATH=. uv run pytest tests/data_platform/preprocessing -q
```

Exit 0.

## Must still pass

```bash
PYTHONPATH=. uv run pytest tests/data_platform -q
```

Exit 0. No new failures outside preprocessing.

## Must not happen

- Raw ingest writers renamed or duplicated (`author` → `author_handle` at sync time).
- `author_id` column added to Bluesky or Reddit preprocessed CSVs.
- `author_handle` added to any `Sync*` model except the existing Bluesky field.
- Stimuli, curate, or feature code changed to depend on `author_handle` in this PR.
- `source_record_id` or step 13 join column work bundled here.
