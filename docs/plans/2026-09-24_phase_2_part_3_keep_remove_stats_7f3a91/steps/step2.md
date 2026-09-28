# Step 2: Platform keep and remove rates with toxicity crosstab

## Goal

From Step 1 per-post vote counts, the implementer assigns modal keep or remove labels, joins stimuli for toxicity, and builds the three platform crosstabs that match the shipped Part 2 compare script table shapes. Land `platform_rates.py` with tiny-fixture pytest coverage. The results writer is not required yet.

## Caller / unit of work

Main caller for this step:

```bash
PYTHONPATH=. uv run pytest experiments/phase_2_part_3_keep_remove_descriptive_stats_2026_09_24/tests/test_platform_rates.py -q
```

Accept a per-post vote frame and a stimuli frame. Inner-join toxicity, derive platform and modal decision, and return count and proportion crosstabs.

In scope: `platform_rates.py`, `tests/test_platform_rates.py`.

Out of scope: four-cell agreement, funnel, `write_results.py`, `run.py`, README.md, SETUP.md, RESULTS.md, plots, S3.

## Files to inspect (read only)

| Path | Why |
|------|-----|
| `/workspace/experiments/compare_keep_remove_rates_across_integrations_2026_08_04/compare_keep_remove_rates.py` | Platform prefix map, toxicity map, crosstab shapes, four-decimal proportions |
| `/workspace/experiments/compare_keep_remove_rates_across_integrations_2026_08_04/RESULTS.md` | Markdown table column order |
| `/workspace/shared/data/transformed/study_phase_2_part_2/README.md` | Modal rule: keep only if `keep_count > remove_count`, else remove |
| `/workspace/experiments/phase_2_part_3_keep_remove_descriptive_stats_2026_09_24/votes.py` | Per-post input columns from Step 1 |
| `/workspace/shared/data/registry.py` | `STUDY_PHASE_2_PART_3_STIMULI` constant |
| `/workspace/docs/plans/2026-09-24_phase_2_part_3_keep_remove_stats_7f3a91/plan.md` | Locked scope |

## Files allowed to change

- `/workspace/experiments/phase_2_part_3_keep_remove_descriptive_stats_2026_09_24/platform_rates.py` (create)
- `/workspace/experiments/phase_2_part_3_keep_remove_descriptive_stats_2026_09_24/tests/test_platform_rates.py` (create)

## Files forbidden to change

- `/workspace/shared/data/**`
- `/workspace/experiments/compare_keep_remove_rates_across_integrations_2026_08_04/**`
- `/workspace/experiments/unanimous_vs_majority_labels_2026_08_08/**`
- Other experiment folders
- `/workspace/docs/plans/2026-09-24_phase_2_part_3_keep_remove_stats_7f3a91/**`
- Do not modify `votes.py` except to fix a Step 1 contract bug blocking Step 2 tests (document in commit message if needed).

## Contracts

Frozen display constants (match Part 2 compare script):

| Name | Value |
|------|-------|
| `PLATFORM_BY_PREFIX` | `bluesky` → `Bluesky`, `reddit` → `Reddit`, `twitter` → `Twitter` |
| `PLATFORM_COLUMNS` | `("Bluesky", "Reddit", "Twitter")` |
| `DECISION_ROWS` | `("keep", "remove")` |
| `TOXICITY_BY_SAMPLE_TYPE` | `sample_low_toxicity` → `low toxicity`, `sample_middle_toxicity` → `medium toxicity`, `sample_high_toxicity` → `high toxicity` |
| `TOXICITY_ORDER` | `("low toxicity", "medium toxicity", "high toxicity")` |
| `PLATFORM_TOXICITY_COLUMNS` | `f"{platform} {toxicity}"` for each platform in `PLATFORM_COLUMNS` and each toxicity in `TOXICITY_ORDER` |
| `PROPORTION_DECIMALS` | `4` |

### `platform_rates.py`

| Function | Signature | Returns |
|----------|-----------|---------|
| `modal_decision` | `(keep_count: int, remove_count: int) -> str` | `"keep"` when `keep_count > remove_count`, otherwise `"remove"` (ties become remove). |
| `derive_platform` | `(post_id: str) -> str` | Display platform from the prefix before the first `_`. Raise `ValueError` when the prefix is unknown. |
| `derive_toxicity_label` | `(sample_toxicity_type: str) -> str` | Mapped display toxicity. Raise `ValueError` when unknown. |
| `join_stimuli_for_platform` | `(per_post: pd.DataFrame, stimuli: pd.DataFrame) -> pd.DataFrame` | Inner join on `post_id == post_primary_key` with `validate="one_to_one"`. |
| `build_labeled_posts` | `(per_post: pd.DataFrame, stimuli: pd.DataFrame) -> pd.DataFrame` | Modal labels plus platform and toxicity fields. |
| `build_platform_crosstab` | `(labeled_posts: pd.DataFrame) -> pd.DataFrame` | 2×3 integer count matrix indexed by `DECISION_ROWS`, columns `PLATFORM_COLUMNS`. |
| `build_platform_toxicity_crosstab` | `(labeled_posts: pd.DataFrame) -> pd.DataFrame` | 2×9 integer count matrix with columns `PLATFORM_TOXICITY_COLUMNS`. |
| `column_proportions` | `(counts: pd.DataFrame) -> pd.DataFrame` | Column-wise shares (each column sums to 1.0 when the column total is positive). |
| `load_stimuli` | `() -> pd.DataFrame` | Loads `STUDY_PHASE_2_PART_3_STIMULI` via `load_dataset(..., low_memory=False)`. |

### `build_labeled_posts` output columns

| Column | Definition |
|--------|------------|
| `post_id` | From per-post frame |
| `decision` | Modal label (`keep` or `remove`) |
| `platform` | `derive_platform(post_id)` |
| `toxicity` | From stimuli `sample_toxicity_type` |
| `platform_toxicity` | `f"{platform} {toxicity}"` |

### Stimuli join rule

Inner-join posts to stimuli on `post_id == post_primary_key` for the platform tables. After the join, if any `post_id` present in the input per-post frame lacks a matching `post_primary_key`, raise `ValueError` listing up to five example ids (stricter than silent drop). Assert stimuli `post_primary_key` values are unique; raise `ValueError` on duplicates.

Stimuli input uses columns `post_primary_key` and `sample_toxicity_type` at minimum.

### Crosstab formatting rules

- Reindex rows to `DECISION_ROWS` and columns to `PLATFORM_COLUMNS` or `PLATFORM_TOXICITY_COLUMNS`, fill missing cells with `0`, cast counts to `int`.
- `column_proportions` divides each column by its sum; zero-sum columns become `pd.NA`.

## Tests (`test_platform_rates.py`)

Tiny fixture only. Two posts across two platforms and two toxicity strata.

Fixture sketch:

- `per_post`: `bluesky_a` with `keep_count=2`, `remove_count=0`; `reddit_b` with `keep_count=1`, `remove_count=1` (tie).
- `stimuli`: matching `post_primary_key` rows with `sample_low_toxicity` and `sample_high_toxicity`.

### Test 1: modal decision and tie becomes remove

- **Given** `keep_count=1`, `remove_count=1`.
- **When** `modal_decision` runs.
- **Then** return value is `"remove"`.

### Test 2: platform crosstab counts

- **Given** the tiny fixture after `build_labeled_posts`.
- **When** `build_platform_crosstab` runs.
- **Then** `keep` row sums to 1 (only `bluesky_a`), `remove` row sums to 1 (`reddit_b` tie label).

### Test 3: column proportions sum to 1.0000

- **Given** platform count crosstab from Test 2.
- **When** `column_proportions` runs and values round to four decimals per column.
- **Then** each platform column sums to `1.0000` at four decimal places.

### Test 4: platform-by-toxicity column order

- **Given** labeled posts from the fixture.
- **When** `build_platform_toxicity_crosstab` runs.
- **Then** column order exactly matches `PLATFORM_TOXICITY_COLUMNS`.

### Test 5 (failure): unknown platform prefix raises

- **Given** `post_id="unknown_123"`.
- **When** `derive_platform` runs.
- **Then** `ValueError` is raised.

### Test 6 (failure): missing stimuli row raises

- **Given** a per-post row whose `post_id` is absent from the stimuli fixture.
- **When** `build_labeled_posts` runs.
- **Then** `ValueError` is raised.

## Pass / fail

Pass:

```bash
PYTHONPATH=. uv run pytest experiments/phase_2_part_3_keep_remove_descriptive_stats_2026_09_24/tests/test_platform_rates.py -q
```

Also confirm Step 1 tests still pass:

```bash
PYTHONPATH=. uv run pytest experiments/phase_2_part_3_keep_remove_descriptive_stats_2026_09_24/tests/test_votes.py -q
```

Expected: both commands exit 0.

Fail:

- Ties labeled `keep` in platform tables.
- Column proportions that do not sum to 1.0000 at four decimals when the column total is positive.
- Hardcoded CSV path in `load_stimuli`.
- Missing stimuli rows are silently dropped without `ValueError`.

## Out of scope for this step

- Four-cell assignment, funnel, and agreement shares.
- `write_results.py`, `run.py`, RESULTS.md, README.md, SETUP.md.
- Markdown rendering and CSV export.
- Plots and S3 upload.

## Implement-from-spec commit sequence

Follow `/workspace/.cursor/skills/implement-from-spec/SKILL.md` in full auto mode, without pausing after contracts.

1. **Scaffold:** create `platform_rates.py` with stubs; add `tests/test_platform_rates.py`.
2. **Contracts:** lock signatures, frozen constants, and output column names.
3. **Failing tests:** implement all six tests above; commit when red.
4. **One function per commit** until `test_platform_rates.py` is green, in order:
   - `modal_decision`, `derive_platform`, `derive_toxicity_label`
   - `join_stimuli_for_platform`
   - `build_labeled_posts`
   - `build_platform_crosstab`, `build_platform_toxicity_crosstab`, `column_proportions`
   - `load_stimuli`

The implementer runs unattended in full auto mode with no approval stop.
