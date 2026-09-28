# Step 1: Clean trials and count votes per post

## Goal

The implementer adds vote cleaning and per-post aggregation shared by both downstream stats. Land `votes.py` with pytest coverage for the trial gate, the duplicate worker vote rule, and per-post `keep_count` and `remove_count`. Do not write RESULTS.md in this step.

## Caller / unit of work

Main caller for this step (tests only; `run.py` arrives in Step 3):

```bash
PYTHONPATH=. uv run pytest experiments/phase_2_part_3_keep_remove_descriptive_stats_2026_09_24/tests/test_votes.py -q
```

Load an optional raw frame (or the registry in integration tests only). Apply the linked-fate trial gate, dedupe worker votes, and aggregate to one row per `post_id` with counts.

In scope: `votes.py`, `tests/test_votes.py`, `tests/__init__.py` if needed.

Out of scope: platform crosstabs, four-cell assignment, `run.py`, `write_results.py`, README.md, SETUP.md, RESULTS.md, stimuli joins, output CSVs.

## Files to inspect (read only)

| Path | Why |
|------|-----|
| `/workspace/experiments/unanimous_vs_majority_labels_2026_08_08/src/build_cohort.py` | Linked-fate trial gate, stable text assert, per-post aggregation fields |
| `/workspace/experiments/reasoning_during_moderation_2026_09_15/SETUP.md` | Duplicate vote rule wording |
| `/workspace/experiments/reasoning_during_moderation_2026_09_15/shared/cohort.py` | `drop_conflicting_worker_posts` and `dedupe_worker_post` sort keys |
| `/workspace/shared/data/registry.py` | `STUDY_PHASE_2_PART_3_RESULTS_FULL` constant |
| `/workspace/docs/plans/2026-09-24_phase_2_part_3_keep_remove_stats_7f3a91/plan.md` | Locked scope |

## Files allowed to change

- `/workspace/experiments/phase_2_part_3_keep_remove_descriptive_stats_2026_09_24/votes.py` (create)
- `/workspace/experiments/phase_2_part_3_keep_remove_descriptive_stats_2026_09_24/tests/__init__.py` (create if needed)
- `/workspace/experiments/phase_2_part_3_keep_remove_descriptive_stats_2026_09_24/tests/test_votes.py` (create)

## Files forbidden to change

- `/workspace/shared/data/**`
- `/workspace/experiments/compare_keep_remove_rates_across_integrations_2026_08_04/**`
- `/workspace/experiments/unanimous_vs_majority_labels_2026_08_08/**`
- `/workspace/experiments/reasoning_during_moderation_2026_09_15/**`
- Any other experiment folder
- `/workspace/docs/plans/2026-09-24_phase_2_part_3_keep_remove_stats_7f3a91/**` (plan files are read-only during implementation)

## Contracts

Frozen string sets:

- `_KEEP_REMOVE = frozenset({"keep", "remove"})`
- Required trial columns: `evaluation_mode`, `decision`, `post_id`, `prolific_id`, `trial_index`, `time_elapsed`, `original_text`, `mirror_text`

### `votes.py`

| Function | Signature | Returns |
|----------|-----------|---------|
| `load_results_full` | `() -> pd.DataFrame` | Loads `STUDY_PHASE_2_PART_3_RESULTS_FULL` via `load_dataset(..., low_memory=False)`. Never hardcodes a CSV path. |
| `filter_linked_fate_trials` | `(raw: pd.DataFrame) -> pd.DataFrame` | Slim trial rows after the gate below. |
| `dedupe_worker_votes` | `(trials: pd.DataFrame) -> pd.DataFrame` | Rows after conflict drop and earliest-row dedupe. |
| `aggregate_votes_per_post` | `(trials: pd.DataFrame) -> pd.DataFrame` | One row per `post_id`. |
| `build_per_post_votes` | `(raw: pd.DataFrame \| None = None) -> pd.DataFrame` | `filter_linked_fate_trials` → `dedupe_worker_votes` → `aggregate_votes_per_post`. Loads registry when `raw` is `None`. |

### Trial gate (`filter_linked_fate_trials`)

Keep a row only when all of the following hold after lowercasing and stripping string fields:

1. `evaluation_mode` equals `linked_fate`.
2. `decision` is `keep` or `remove`.
3. `post_id` is non-null, non-empty after stripping, and not the literal string `nan`.

Do not filter on `attention_check_passed`, `phase`, or `trial_type`.

Raise `KeyError` when a required column is missing.

### Duplicate vote rule (`dedupe_worker_votes`)

Quote for SETUP.md (Step 3) and implement here:

> The build drops worker-post pairs that contain both keep and remove, then keeps the earliest remaining row per worker and post.

Implementation mapping:

1. Drop rows with null, empty, or literal `nan` `prolific_id` before worker-post logic.
2. Treat `prolific_id` as the worker id.
3. Drop every `(post_id, prolific_id)` group whose `decision` has more than one distinct value after the trial gate.
4. Sort remaining rows by `post_id`, `prolific_id`, `trial_index`, `time_elapsed` with `kind="mergesort"`.
5. Keep the first row per `(post_id, prolific_id)`.

### Per-post aggregation (`aggregate_votes_per_post`)

Before aggregating, assert each `post_id` has exactly one distinct `original_text` and one distinct `mirror_text` among input trials. Raise `ValueError` on conflict (same message pattern as Part 2 build_cohort).

Output columns in this order:

| Column | Type | Definition |
|--------|------|------------|
| `post_id` | str | Post identifier |
| `n_raters` | int | Row count after dedupe |
| `keep_count` | int | Count of `keep` decisions |
| `remove_count` | int | Count of `remove` decisions |
| `n_unique_decisions` | int | Distinct decision count |
| `is_unanimous` | bool | `n_unique_decisions == 1` |
| `original_text` | str | Stable text (`first` in group) |
| `mirror_text` | str | Stable text (`first` in group) |

## Tests (`test_votes.py`)

Use synthetic `pd.DataFrame` fixtures only. Do not load the full CSV in unit tests.

### Test 1: trial gate keeps linked-fate keep and remove only

- **Given** rows with `linked_fate` keep, `linked_fate` remove, `practice` keep, and empty `post_id`.
- **When** `filter_linked_fate_trials` runs.
- **Then** only the two valid linked-fate rows with usable `post_id` remain.

### Test 2: conflicting worker-post pair is dropped

- **Given** one `(post_id, prolific_id)` with both `keep` and `remove`, plus a second worker on the same post with only `keep`.
- **When** `dedupe_worker_votes` runs.
- **Then** the conflicting worker-post pair is gone; the other worker row remains.

### Test 3: duplicate keep rows keep earliest `trial_index`

- **Given** two `keep` rows for the same `(post_id, prolific_id)` with `trial_index` 0 and 9.
- **When** `dedupe_worker_votes` runs.
- **Then** the row with `trial_index == 0` remains.

### Test 4: per-post counts after full pipeline

- **Given** three workers on post `twitter_x` (two keep, one remove) and three unanimous `keep` rows on post `reddit_y` after dedupe.
- **When** `build_per_post_votes(raw=fixture)` runs.
- **Then** `twitter_x` has `n_raters=3`, `keep_count=2`, `remove_count=1`, `is_unanimous=False`; `reddit_y` has `n_raters=3`, `keep_count=3`, `remove_count=0`, `is_unanimous=True`.

### Test 5 (failure): unstable text raises

- **Given** two slim rows for the same `post_id` with different `original_text`.
- **When** `aggregate_votes_per_post` runs.
- **Then** `ValueError` is raised.

## Pass / fail

Pass:

```bash
PYTHONPATH=. uv run pytest experiments/phase_2_part_3_keep_remove_descriptive_stats_2026_09_24/tests/test_votes.py -q
```

Expected: exit code 0.

Fail:

- Any test above fails or is skipped.
- `load_results_full` hardcodes a filesystem path instead of the registry name.
- Trial gate filters on `attention_check_passed` or `phase`.
- A worker-post pair with both keep and remove survives dedupe.

## Out of scope for this step

- Modal labels and platform derivation.
- Stimuli join.
- Four-cell assignment and funnel.
- `RESULTS.md`, README.md, SETUP.md.
- `platform_rates.py`, `agreement.py`, `write_results.py`, `run.py`.

## Implement-from-spec commit sequence

Follow `/workspace/.cursor/skills/implement-from-spec/SKILL.md` in full auto mode, without pausing after contracts.

1. **Scaffold:** create `votes.py` with stub bodies and `tests/test_votes.py` importing the module.
2. **Contracts:** lock the five function signatures and frozen column list. Bodies stay `raise NotImplementedError`.
3. **Failing tests:** write all five tests from the given/when/then blocks. Commit when tests fail for the right reason.
4. **One function per commit** until `test_votes.py` is green, in dependency order:
   - `filter_linked_fate_trials`
   - `dedupe_worker_votes`
   - `aggregate_votes_per_post`
   - `build_per_post_votes`
   - `load_results_full` (thin wrapper; can land with `build_per_post_votes`)

The implementer runs unattended in full auto mode with no approval stop.
