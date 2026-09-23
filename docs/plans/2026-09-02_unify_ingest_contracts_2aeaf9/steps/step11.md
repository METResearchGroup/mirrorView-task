# Step 11: Point stimuli sampling at preprocess text with no fallback

## Goal

Stimuli sampling (`normalize_mirrorview_df`) reads Reddit comment text from `body` today. Preprocess already copies `body` → `text` via `add_canonical_text_column` / `PreprocessedRedditCommentModel`. This PR makes Reddit use the same `text` column as Bluesky and Twitter and fails if it is missing — no fallback to `body`.

## Caller / unit of work

**Main caller:** `experiments/scaled_mirrors_generation_2026_06_02/sample_data_to_mirror.py` → `normalize_mirrorview_df`.

**Slice:** Reddit branch sets `text_col = "text"` → existing required-column and null checks apply → `original_text` is sourced from `text`.

**Out of scope:** Preprocess (`add_canonical_text_column`, `PreprocessedRedditCommentModel`), ingest, features, curate, other experiment scripts that read `body` directly (e.g. `fix_primary_key_column_for_reddit_posts.py` lookup repair).

## Decision (locked)

- Reddit `text_col` becomes `"text"`, matching Bluesky and Twitter. Do not read `body` as a substitute.
- If `text` is absent from the input frame, raise `ValueError` via the existing missing-column loop (`Integration \`reddit\` mirrorview export missing required column \`text\`.`). Do not add a `body` fallback branch.
- Bluesky and Twitter branches stay on `text_col = "text"`; no behavior change.
- Preprocess is already correct; do not change preprocess in this PR unless a test fixture needs a minimal row shape.
- Independently shippable; no dependency on other plan steps.
- `normalize_mirrorview_df` is a pure function and the production handoff for curated exports → stimuli records. Despite `UNIT_TESTING_STANDARDS` usually skipping `experiments/`, **add unit tests** for this function.

## Files to inspect (read-only)

| Path | Why |
|------|-----|
| `docs/plans/2026-09-02_unify_ingest_contracts_2aeaf9/plan.md` | Parent plan, step 11 summary |
| `experiments/scaled_mirrors_generation_2026_06_02/sample_data_to_mirror.py` | `normalize_mirrorview_df` — Reddit `text_col = "body"` today (lines ~94–97) |
| `experiments/scaled_mirrors_generation_2026_06_02/count_missing_flips.py` | Imports `normalize_mirrorview_df`; inherits stricter contract, no code change expected |
| `data_platform/preprocessing/runner.py` | `add_canonical_text_column` — confirms preprocess copies Reddit `body` → `text` |
| `.cursor/skills/implement-plan-and-open-pr/UNIT_TESTING_STANDARDS.md` | Test class naming and arrange-act-assert |

**Grep note (experiment folder only):** Only `count_missing_flips.py` calls `normalize_mirrorview_df` besides `sample_data_to_mirror.py` itself. `fix_primary_key_column_for_reddit_posts.py` reads `body` for a one-off lookup repair and does not call this function.

## Files allowed to change

- `experiments/scaled_mirrors_generation_2026_06_02/sample_data_to_mirror.py`
- `tests/experiments/test_sample_data_to_mirror.py` (new — no `tests/` folder exists under the experiment directory)
- `CHANGELOG.md` (after the PR exists, via write-changelog)

## Files forbidden to change

- `data_platform/preprocessing/**` (including `preprocess_reddit.py`, `runner.py`, models)
- `data_platform/ingestion/**`
- `data_platform/generate_features/**`
- `data_platform/curate/**`
- `experiments/scaled_mirrors_generation_2026_06_02/fix_primary_key_column_for_reddit_posts.py`
- Other experiment scripts in that folder unless a test import requires none

## Contracts

```text
normalize_mirrorview_df(df_raw: pd.DataFrame, *, integration: str) -> pd.DataFrame

integration == "reddit":
  text_col = "text"          # was "body"
  id_col = "post_reddit_id"
  comment_id_col = "comment_id"
  required_cols includes text_col, id_col, comment_id_col, tox_col, "political_stance"

integration in ("twitter", "bluesky"):
  text_col = "text"          # unchanged

If text_col not in df_raw.columns:
  raise ValueError(
    f"Integration `{integration}` mirrorview export missing required column `{text_col}`."
  )

normalized["original_text"] = df_raw[text_col].astype(str)   # never df_raw["body"]
```

No `body` fallback, alias, or `df_raw.get("text", df_raw["body"])` pattern.

## Tests (write first)

**Location:** `tests/experiments/test_sample_data_to_mirror.py` (import from `experiments.scaled_mirrors_generation_2026_06_02.sample_data_to_mirror`).

`TestNormalizeMirrorviewDf` — one class per function.

Minimal Reddit fixture columns: `post_reddit_id`, `comment_id`, `text`, `toxicity_tier` (or `sample_toxicity_type`), `political_stance` with non-null values and a binary stance (not `unclear` / `neutral`, which the function filters out).

- given Reddit frame with `text` and required columns, when `normalize_mirrorview_df(..., integration="reddit")`, then it returns a frame whose `original_text` matches `text` (and does not require `body`).
- given Reddit frame with only `body` (no `text`) and other required columns, then `pytest.raises(ValueError, match="missing required column `text`")`.
- given Bluesky or Twitter frame with `text`, then existing behavior unchanged (smoke: `original_text` populated).

Follow `.cursor/skills/implement-plan-and-open-pr/UNIT_TESTING_STANDARDS.md`. Use `PYTHONPATH=.` for imports.

## Must pass

```bash
PYTHONPATH=. uv run pytest tests/experiments/test_sample_data_to_mirror.py -q
```

Exit 0.

## Must still pass

```bash
PYTHONPATH=. uv run pytest tests/data_platform -q
```

Exit 0. No new failures.

## Must not happen

- Reading `body` when `text` is missing (no fallback).
- Changing Bluesky/Twitter text column selection.
- Modifying preprocess to add or rename columns for this PR.
- Changing `fix_primary_key_column_for_reddit_posts.py` or other body-based repair scripts.
