# Step 3: Four-cell rates, funnel, caller, and docs

## Goal

The implementer assigns unanimous versus majority cells with the Part 2 build_cohort rules, reports the vote funnel, wires the single caller that writes RESULTS.md and output CSVs, and adds README.md and SETUP.md. Pytest covers cell assignment and required markdown headers.

## Caller / unit of work

Main caller:

```bash
PYTHONPATH=. uv run python experiments/phase_2_part_3_keep_remove_descriptive_stats_2026_09_24/run.py
```

Full test suite:

```bash
PYTHONPATH=. uv run pytest experiments/phase_2_part_3_keep_remove_descriptive_stats_2026_09_24/tests -q
```

Load both registry datasets and call `build_per_post_votes`. Compute platform crosstabs and the four-cell table plus funnel. Write RESULTS.md and CSVs under `outputs/`, and print markdown to stdout.

In scope: `agreement.py`, `write_results.py`, `run.py`, `tests/test_agreement.py`, `README.md`, `SETUP.md`, `RESULTS.md`, `outputs/*.csv`.

Out of scope: plots, S3 upload, hypothesis tests, confidence intervals, textual features, new registry entries, edits to shared data or other experiments.

## Files to inspect (read only)

| Path | Why |
|------|-----|
| `/workspace/experiments/unanimous_vs_majority_labels_2026_08_08/src/build_cohort.py` | Four-cell assignment, `n_raters >= 3`, drop ties |
| `/workspace/experiments/compare_keep_remove_rates_across_integrations_2026_08_04/compare_keep_remove_rates.py` | Markdown table formatting for platform tables |
| `/workspace/experiments/compare_keep_remove_rates_across_integrations_2026_08_04/RESULTS.md` | Platform table header shape |
| `/workspace/experiments/reasoning_during_moderation_2026_09_15/SETUP.md` | Duplicate vote rule exact quote |
| `/workspace/shared/data/raw/study_phase_2_part_3/README.md` | Registry names for SETUP.md |
| `/workspace/AGENTS.md` | Experiment README and SETUP conventions |
| `/workspace/docs/plans/2026-09-24_phase_2_part_3_keep_remove_stats_7f3a91/plan.md` | Locked end state |

## Files allowed to change

- `/workspace/experiments/phase_2_part_3_keep_remove_descriptive_stats_2026_09_24/agreement.py` (create)
- `/workspace/experiments/phase_2_part_3_keep_remove_descriptive_stats_2026_09_24/write_results.py` (create)
- `/workspace/experiments/phase_2_part_3_keep_remove_descriptive_stats_2026_09_24/run.py` (create)
- `/workspace/experiments/phase_2_part_3_keep_remove_descriptive_stats_2026_09_24/tests/test_agreement.py` (create)
- `/workspace/experiments/phase_2_part_3_keep_remove_descriptive_stats_2026_09_24/README.md` (create)
- `/workspace/experiments/phase_2_part_3_keep_remove_descriptive_stats_2026_09_24/SETUP.md` (create)
- `/workspace/experiments/phase_2_part_3_keep_remove_descriptive_stats_2026_09_24/RESULTS.md` (create or regenerate)
- `/workspace/experiments/phase_2_part_3_keep_remove_descriptive_stats_2026_09_24/outputs/` (create CSV mirrors)

## Files forbidden to change

- `/workspace/shared/data/**`
- `/workspace/experiments/compare_keep_remove_rates_across_integrations_2026_08_04/**`
- `/workspace/experiments/unanimous_vs_majority_labels_2026_08_08/**`
- Other experiment folders
- `/workspace/docs/plans/2026-09-24_phase_2_part_3_keep_remove_stats_7f3a91/**`

## README and SETUP contract

### `README.md`

Per `/workspace/AGENTS.md`: one or two lines with the experiment title, then pointers to `SETUP.md` and `RESULTS.md`. No environment setup prose.

### `SETUP.md`

Data requirements only (no `uv sync`, no AWS, no pytest install steps). Must state:

1. Required datasets: `STUDY_PHASE_2_PART_3_RESULTS_FULL` and `STUDY_PHASE_2_PART_3_STIMULI`, loaded only through `shared.data.dataloader.load_dataset`.
2. Rows are not filtered on `attention_check_passed` or `phase`. Failed attention checks remain in the rate denominators.
3. Exact duplicate vote quote from `/workspace/experiments/reasoning_during_moderation_2026_09_15/SETUP.md` line 7:

   > The build drops worker-post pairs that contain both keep and remove, then keeps the earliest remaining row per worker and post.

4. Modal platform labels use keep when `keep_count > remove_count`, otherwise remove (ties become remove). The modal rule matches Part 2 modal labels.
5. Four-cell table uses raw vote counts, not modal labels. Posts need at least three raters. Exact ties (`keep_count == remove_count`) are excluded from the four-cell universe.
6. The run command:

   ```bash
   PYTHONPATH=. uv run python experiments/phase_2_part_3_keep_remove_descriptive_stats_2026_09_24/run.py
   ```

## Contracts

### `agreement.py`

Frozen constants:

| Name | Value |
|------|-------|
| `_MIN_RATERS` | `3` |
| `_CELL_ORDER` | `("unanimous_keep", "majority_keep", "majority_remove", "unanimous_remove")` |

| Function | Signature | Returns |
|----------|-----------|---------|
| `assign_agreement_cell` | `(row: pd.Series) -> str` | One of the four cell strings. Raise `ValueError` on exact ties or invalid rows. |
| `build_four_cell_counts` | `(per_post: pd.DataFrame) -> pd.DataFrame` | Two columns: `cell`, `count`. Rows follow `_CELL_ORDER`. |
| `build_four_cell_shares` | `(cell_counts: pd.DataFrame) -> pd.DataFrame` | Adds `share` column: `count / count.sum()` at four decimal places in display. |
| `build_vote_funnel` | `(per_post: pd.DataFrame) -> pd.DataFrame` | Funnel counts (see below). |

### Four-cell rules (match Part 2 `build_cohort`)

On the per-post frame after Step 1 cleaning (do not apply modal labels here):

1. Start from all posts in `per_post`.
2. `posts_after_vote_clean` = row count of `per_post`.
3. Drop posts with `n_raters < 3`. `posts_dropped_lt_3_raters` = count dropped.
4. Among survivors, drop posts with `keep_count == remove_count`. `posts_dropped_ties` = count dropped.
5. `posts_remaining` = rows that receive a cell label.

Cell assignment on each remaining row:

| Condition | `cell` |
|-----------|--------|
| `is_unanimous` and `keep_count == n_raters` | `unanimous_keep` |
| `is_unanimous` and `remove_count == n_raters` | `unanimous_remove` |
| not unanimous and `keep_count > remove_count` | `majority_keep` |
| not unanimous and `remove_count > keep_count` | `majority_remove` |

### Funnel output (`build_vote_funnel`)

Single-column metric frame with exactly these rows and integer `count` values:

| metric | Definition |
|--------|------------|
| `posts_after_vote_clean` | `len(per_post)` |
| `posts_dropped_lt_3_raters` | posts with `n_raters < 3` |
| `posts_dropped_ties` | posts with `n_raters >= 3` and `keep_count == remove_count` |
| `posts_remaining` | posts that enter the four-cell table |

### `write_results.py`

| Function | Signature | Returns |
|----------|-----------|---------|
| `format_counts_table` | `(table: pd.DataFrame, decision_rows: tuple[str, ...]) -> str` | Markdown pipe table for integer crosstabs (platform and platform-toxicity). |
| `format_proportions_table` | `(table: pd.DataFrame, decision_rows: tuple[str, ...], decimals: int) -> str` | Markdown pipe table with fixed decimal formatting. |
| `format_four_cell_table` | `(cell_counts: pd.DataFrame, cell_shares: pd.DataFrame) -> str` | Markdown table with columns `cell`, `count`, `share`. |
| `format_funnel_table` | `(funnel: pd.DataFrame) -> str` | Markdown table with columns `metric`, `count`. |
| `format_results_markdown` | `(platform_counts, platform_proportions, platform_toxicity_proportions, four_cell_counts, four_cell_shares, funnel) -> str` | Full RESULTS.md body with section headings. |
| `write_results` | `(markdown: str, csv_bundle: dict[str, pd.DataFrame], experiment_dir: Path) -> Path` | Writes `RESULTS.md` and CSV files under `experiment_dir / "outputs"`. Returns `RESULTS.md` path. |

### `run.py`

| Function | Signature | Returns |
|----------|-----------|---------|
| `main` | `() -> None` | End-to-end pipeline; writes results; prints markdown. |

`main` must call, in order: load results, `build_per_post_votes`, load stimuli, platform crosstabs, four-cell and funnel builders, `format_results_markdown`, `write_results`.

### RESULTS.md required sections and headers

The implementer re-runs `run.py` to fill numeric cells. Do not invent expected counts in tests or the plan.

1. **Platform counts**. Markdown table with header row starting `| decision | Bluesky | Reddit | Twitter |`
2. **Platform proportions**. Same column header. Values at four decimals. Each platform column sums to `1.0000` at four decimals when the column total is positive.
3. **Platform by toxicity proportions**. Header includes `Bluesky low toxicity` through `Twitter high toxicity` in `PLATFORM_TOXICITY_COLUMNS` order.
4. **Four-cell counts**. Table with header `| cell | count | share |` and rows for all four cells in `_CELL_ORDER`.
5. **Vote funnel**. Table with header `| metric | count |` and the four funnel metrics above.

### Output CSV paths (under `outputs/`)

| File | Content |
|------|---------|
| `platform_counts.csv` | Platform count crosstab |
| `platform_proportions.csv` | Platform proportion crosstab |
| `platform_toxicity_proportions.csv` | Platform-toxicity proportion crosstab |
| `four_cell_counts.csv` | `cell`, `count`, `share` |
| `funnel.csv` | `metric`, `count` |

## Tests (`test_agreement.py`)

### Test 1: unanimous keep cell

- **Given** a row with `n_raters=3`, `keep_count=3`, `remove_count=0`, `is_unanimous=True`.
- **When** `assign_agreement_cell` runs.
- **Then** return value is `unanimous_keep`.

### Test 2: majority keep cell

- **Given** a row with `n_raters=3`, `keep_count=2`, `remove_count=1`, `is_unanimous=False`.
- **When** `assign_agreement_cell` runs.
- **Then** return value is `majority_keep`.

### Test 3: tie excluded from four-cell universe

- **Given** per-post fixture with one row `keep_count=2`, `remove_count=2`, `n_raters=4`.
- **When** `build_four_cell_counts` runs.
- **Then** the tie post is absent and total `count` sum excludes it.

### Test 4: platform tie is remove in modal label but excluded from four-cell

- **Given** the same tie row as Test 3 in a per-post frame.
- **When** `modal_decision(2, 2)` runs and `build_four_cell_counts` runs.
- **Then** modal label is `remove` and the post is not in the four-cell table.

### Test 5 (failure): exact tie raises in `assign_agreement_cell`

- **Given** a row with `keep_count == remove_count`.
- **When** `assign_agreement_cell` runs.
- **Then** `ValueError` is raised.

### Test 6: RESULTS.md contains required table headers

- **Given** a minimal fake markdown string from `format_results_markdown` using tiny synthetic frames (two posts).
- **When** the test checks substring presence.
- **Then** the string contains all five header patterns listed in the RESULTS contract above.

## Pass / fail

Pass:

```bash
PYTHONPATH=. uv run pytest experiments/phase_2_part_3_keep_remove_descriptive_stats_2026_09_24/tests -q
```

Expected: exit code 0.

Then:

```bash
PYTHONPATH=. uv run python experiments/phase_2_part_3_keep_remove_descriptive_stats_2026_09_24/run.py
```

Expected: exit code 0; `RESULTS.md` is written; stdout includes the platform and four-cell tables.

After `run.py`, manually confirm `RESULTS.md` contains:

- Platform count table (`| decision | Bluesky | Reddit | Twitter |`)
- Platform proportion table (same header; column proportions sum to `1.0000` at four decimals per platform)
- Platform-by-toxicity proportion table (nine platform-toxicity columns)
- Four-cell table (`| cell | count | share |`)
- Funnel table (`| metric | count |`)

Numeric cell values are filled by re-running `run.py` on the current export. Tests must not assert live production counts.

Fail:

- Any pytest failure.
- `run.py` hardcodes CSV paths.
- Modal tie-break used inside four-cell assignment.
- `RESULTS.md` missing any required header row.
- Attention check or phase filtering added.

## Out of scope for this step

- Plots and image assets.
- S3 upload to `mirrorview-experimental-artifacts`.
- Hypothesis tests and confidence intervals.
- Textual features, word clouds, stance tables.
- New shared registry entries.

## Implement-from-spec commit sequence

Follow `/workspace/.cursor/skills/implement-from-spec/SKILL.md` in full auto mode, without pausing after contracts.

1. **Scaffold:** create `agreement.py`, `write_results.py`, `run.py` stubs; add `tests/test_agreement.py`; add README.md and SETUP.md shells.
2. **Contracts:** lock all signatures, funnel metrics, RESULTS section headers, and CSV paths.
3. **Failing tests:** write Tests 1 through 6; commit when red.
4. **One function per commit** until green, in order:
   - `assign_agreement_cell`, `build_four_cell_counts`, `build_four_cell_shares`, `build_vote_funnel`
   - `format_counts_table`, `format_proportions_table`, `format_four_cell_table`, `format_funnel_table`, `format_results_markdown`, `write_results`
   - `main` in `run.py`
   - finalize README.md and SETUP.md text
5. **Phase 6:** run full pytest and `run.py`; commit regenerated `RESULTS.md` and `outputs/*.csv`.

The implementer runs unattended in full auto mode with no approval stop.
