# Step 1: Add experiment script

## Goal

Create `experiments/compare_keep_remove_rates_across_integrations_2026_08_04/compare_keep_remove_rates.py` that loads Study Phase 2 Part 2 keep/remove labels via the shared dataloader, derives platform from `message_id`, builds a 2×3 keep/remove × platform count matrix, and writes that table (only) to `RESULTS.md` in the same folder.

## Caller / unit of work

**Main caller:** CLI `__main__` of `compare_keep_remove_rates.py` (run with `PYTHONPATH=. uv run python ...` from repo root).

**In scope:** Create the experiment directory and the single Python script. Script may create/overwrite `RESULTS.md` when run.

**Out of scope:** `README.md` (Step 2); edits to `shared/data/**`; tests package; plots; rate/proportion columns; narrative commentary in `RESULTS.md`.

## Files to inspect (read-only)

| Path | Why |
|------|-----|
| `/workspace/shared/data/dataloader.py` | `load_dataset` contract |
| `/workspace/shared/data/registry.py` | Registry name `STUDY_PHASE_2_PART_2_KEEP_REMOVE_LABELS` |
| `/workspace/shared/data/transformed/study_phase_2_part_2/README.md` | Label columns and expected size (~8791 rows) |
| `/workspace/shared/data/transformed/study_phase_2_part_2/keep_remove_labels.csv` | On-disk labels; `message_id` prefixes `bluesky_`, `reddit_`, `twitter_` |
| `/workspace/docs/plans/2026-08-05_compare_keep_remove_rates_across_integrations_578133/plan.md` | Parent plan |

## Files allowed to change

- `/workspace/experiments/compare_keep_remove_rates_across_integrations_2026_08_04/compare_keep_remove_rates.py` (create)
- `/workspace/experiments/compare_keep_remove_rates_across_integrations_2026_08_04/RESULTS.md` (create/overwrite when script runs)

## Files forbidden to change

- `/workspace/shared/data/dataloader.py`
- `/workspace/shared/data/registry.py`
- `/workspace/shared/data/transformed/**`
- `/workspace/shared/data/raw/**`
- `/workspace/experiments/**` other than this new experiment folder
- Do **not** create a `tests/` package under this experiment

## Contracts to freeze

### Data ingress

- Load with `shared.data.dataloader.load_dataset` using registry name `STUDY_PHASE_2_PART_2_KEEP_REMOVE_LABELS`.
- Do **not** `pd.read_csv` a hardcoded path to `keep_remove_labels.csv`.
- Required columns after load: `message_id`, `decision` (values `keep` / `remove`).

### Platform derivation

- From each `message_id` string, take `message_id.split("_", 1)[0]` (lowercase token as stored).
- Map tokens to display names:
  - `bluesky` → `Bluesky`
  - `reddit` → `Reddit`
  - `twitter` → `Twitter`
- Raise `ValueError` if any row’s token is outside that set (fail loudly; do not silently drop).

### Contingency table

- Rows: `keep`, `remove` (use the `decision` column strings; normalize with `.astype(str).str.lower().str.strip()` if needed).
- Columns: `Bluesky`, `Reddit`, `Twitter` (fixed order).
- Cells: integer counts (`pandas.crosstab` or equivalent).
- Include zeros if a cell is empty (do not omit a platform column).

### `RESULTS.md` write format

- Overwrite `/workspace/experiments/compare_keep_remove_rates_across_integrations_2026_08_04/RESULTS.md`.
- Content: markdown table of the 2×3 matrix only. No title paragraph, no rates, no interpretation.
- Example shape (counts illustrative):

```markdown
| decision | Bluesky | Reddit | Twitter |
|---|---:|---:|---:|
| keep | 0 | 0 | 0 |
| remove | 0 | 0 | 0 |
```

### CLI behavior

- Running the script prints the same table to stdout (plain text or markdown is fine) and writes `RESULTS.md`.
- No argparse required unless useful; defaults only.

## Exact commands

```bash
cd /workspace

PYTHONPATH=. uv run python experiments/compare_keep_remove_rates_across_integrations_2026_08_04/compare_keep_remove_rates.py
```

Expected: process exits 0; stdout shows a 2×3 count table; `RESULTS.md` exists with the same counts; row totals across platforms sum to ~8791; platform column totals match prefix counts (~1979 Bluesky, ~4267 Reddit, ~2545 Twitter).

## Pass / fail

**Pass:**

1. Script exists at the path above and imports `load_dataset` + `STUDY_PHASE_2_PART_2_KEEP_REMOVE_LABELS` (no hardcoded CSV path).
2. Command above exits 0.
3. `RESULTS.md` is a markdown 2×3 table with rows `keep`/`remove` and columns `Bluesky`/`Reddit`/`Twitter`.
4. Cell integers sum to the loaded frame length; unknown prefixes raise.

**Fail:**

1. Script reads the CSV via a filesystem path instead of the shared loader.
2. `RESULTS.md` includes commentary, rates, or extra sections.
3. Platform columns missing or mis-ordered; silent drop of unknown prefixes.
