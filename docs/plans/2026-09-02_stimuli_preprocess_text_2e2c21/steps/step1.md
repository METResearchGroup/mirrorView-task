# Step 1: Require preprocess text for Reddit stimuli sampling

## Goal

Make Reddit stimuli sampling read the shared preprocess `text` column, the same way Bluesky and Twitter already do. Fail if `text` is missing. Do not fall back to `body`.

## Caller / unit of work

**Main caller:** `experiments/scaled_mirrors_generation_2026_06_02/sample_data_to_mirror.py` `normalize_mirrorview_df`, reached from `main` after each curated CSV load, and from `experiments/scaled_mirrors_generation_2026_06_02/count_missing_flips.py`.

**Task:** set Reddit `text_col` to `"text"`. Keep the existing required-column loop and null check. `original_text` comes from that column.

**Out of scope:** Shared author fields (GitHub issue 114). Source record id (115). Length and language gates (116). Preprocess `add_canonical_text_column`. Ingest writers. Renaming raw Reddit `body`. `CHANGELOG.md`. `experiments/scaled_mirrors_generation_2026_06_02/fix_primary_key_column_for_reddit_posts.py`. Sibling GitHub issues 103 to 112 and 114 to 116.

## Files to inspect (read-only)

| Path | Why |
|------|-----|
| `/workspace/experiments/scaled_mirrors_generation_2026_06_02/sample_data_to_mirror.py` | `normalize_mirrorview_df` sets Reddit `text_col = "body"` today. Bluesky and Twitter already use `"text"`. |
| `/workspace/data_platform/preprocessing/runner.py` | `add_canonical_text_column` copies Reddit `body` onto `text`. Do not change it. |
| `/workspace/data_platform/utils/platform_specific_columns.py` | `CANONICAL_TEXT_COLUMN = "text"` and `REDDIT_ORIGINAL_PLATFORM_TEXT_COLUMN = "body"`. |
| `/workspace/tests/data_platform/preprocessing/test_add_canonical_text_column.py` | Proves preprocess already copies Reddit `body` onto `text` and keeps `body`. |
| `/workspace/experiments/scaled_mirrors_generation_2026_06_02/count_missing_flips.py` | Imports `normalize_mirrorview_df`. Inherits the stricter contract. Do not edit it. |
| `/workspace/.cursor/skills/implement-plan-and-open-pr/UNIT_TESTING_STANDARDS.md` | One test class per function. Arrange, act, assert. |

## Files allowed to change

- `/workspace/experiments/scaled_mirrors_generation_2026_06_02/sample_data_to_mirror.py`
- `/workspace/tests/experiments/test_sample_data_to_mirror.py` (new)

Plan package files under `/workspace/docs/plans/2026-09-02_stimuli_preprocess_text_2e2c21/` may already be on the branch. Do not edit them during implementation.

## Files forbidden to change

- `/workspace/data_platform/preprocessing/**`
- `/workspace/data_platform/ingestion/**`
- `/workspace/data_platform/generate_features/**`
- `/workspace/data_platform/curate/**`
- `/workspace/data_platform/models/**`
- `/workspace/experiments/scaled_mirrors_generation_2026_06_02/fix_primary_key_column_for_reddit_posts.py`
- `/workspace/CHANGELOG.md`
- Any file outside the allowed list, except git commits of this work

## Contracts to lock

Keep this signature unchanged:

```text
normalize_mirrorview_df(df_raw: pd.DataFrame, *, integration: str) -> pd.DataFrame
```

Reddit branch:

- `id_col = "post_reddit_id"`
- `comment_id_col = "comment_id"`
- `text_col = "text"` (was `"body"`)
- `required_cols` includes `text_col`, so a missing `text` column raises:

```text
Integration `reddit` mirrorview export missing required column `text`.
```

Bluesky and Twitter:

- `text_col = "text"` unchanged

All platforms:

- `normalized["original_text"] = df_raw[text_col].astype(str)`
- Do not read `body` as a substitute.
- Do not use `df_raw.get("text", ...)` or any other fallback.

## Test design

Location: `/workspace/tests/experiments/test_sample_data_to_mirror.py`

Import `normalize_mirrorview_df` from `experiments.scaled_mirrors_generation_2026_06_02.sample_data_to_mirror`.

One class: `TestNormalizeMirrorviewDf`.

Minimal Reddit frame: `post_reddit_id`, `comment_id`, `text`, `toxicity_tier`, `political_stance`. Stance must be `left` or `right` so the row is not filtered out. Do not include `body` on the happy-path frame.

```text
given a Reddit frame with text and the other required columns, and no body
when normalize_mirrorview_df(..., integration="reddit")
then original_text equals that text value
and unique_reddit_id uses post_reddit_id and comment_id

given a Reddit frame with body and the other required columns, and no text
when normalize_mirrorview_df(..., integration="reddit")
then raise ValueError matching missing required column `text`

given a Reddit frame with both text and a different body
when normalize_mirrorview_df(..., integration="reddit")
then original_text equals text, not body

given a Twitter frame with tweet_id and text
when normalize_mirrorview_df(..., integration="twitter")
then original_text equals that text value

given a Bluesky frame with uri and text
when normalize_mirrorview_df(..., integration="bluesky")
then original_text equals that text value
```

## Implementation notes (implement-from-spec)

The production function already exists. Do not add a new helper. Scaffold and contracts are a new test file plus a docstring update.

Phase order, one Git commit per phase that changes the repo, and one commit per Phase 5 unit:

1. Phase 1 scope. Confirm callers, file tree, and out-of-scope. No product-code commit if nothing on disk changes.
2. Phase 2 scaffold. Create `/workspace/tests/experiments/test_sample_data_to_mirror.py` with the import and an empty `TestNormalizeMirrorviewDf` class. No test methods yet. Imports must resolve.
3. Phase 3 contracts. Update the `normalize_mirrorview_df` docstring to say every platform, including Reddit, requires preprocess `text` and does not fall back to `body`. Leave `text_col = "body"` for Reddit so runtime is unchanged. Full auto. Do not wait for approval.
4. Phase 4 test design. Add the failing tests listed above. They fail because Reddit still requires `body` and does not require `text`.
5. Phase 5 unit: in the Reddit branch of `normalize_mirrorview_df`, set `text_col = "text"`. The new tests pass. Bluesky and Twitter stay on `text`.
6. Phase 6. Run the must-pass commands. Confirm preprocess and ingest files are unchanged. Confirm no `body` fallback.

## Must pass

```bash
cd /workspace
PYTHONPATH=. uv run pytest tests/experiments/test_sample_data_to_mirror.py -q
```

Expected: exit 0.

```bash
cd /workspace
PYTHONPATH=. uv run pytest tests/data_platform -q
```

Expected: exit 0. No new failures.

## Must fail / not happen

- Reddit sampling reading `body` when `text` is missing.
- A `body` fallback, alias, or `get("text", ...)` pattern.
- Bluesky or Twitter text column selection changing.
- Preprocess, ingest, or curated export writers edited.
- Raw Reddit `body` renamed on ingest.
- Shared author fields added.
- `CHANGELOG.md` edited.
- Sibling GitHub issues 103 to 112 and 114 to 116 implemented in this PR.
