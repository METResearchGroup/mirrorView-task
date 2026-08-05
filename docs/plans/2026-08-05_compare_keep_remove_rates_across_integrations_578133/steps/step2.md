# Step 2: Add README and commit RESULTS

## Goal

Finish the experiment package: add a terse `README.md`, ensure `RESULTS.md` holds the live table from a successful script run, and leave the folder with exactly those three files.

## Caller / unit of work

**Main caller:** human operator reading `README.md` and running the documented command.

**In scope:** Create `README.md`; re-run Step 1 script if needed so `RESULTS.md` is current; confirm folder contents.

**Out of scope:** Changing script logic; shared data edits; extra docs, plots, or tests.

## Files to inspect (read-only)

| Path | Why |
|------|-----|
| `/workspace/docs/plans/2026-08-05_compare_keep_remove_rates_across_integrations_578133/plan.md` | Deliverable constraints |
| `/workspace/docs/plans/2026-08-05_compare_keep_remove_rates_across_integrations_578133/steps/step1.md` | Script + RESULTS contract |
| `/workspace/experiments/compare_keep_remove_rates_across_integrations_2026_08_04/compare_keep_remove_rates.py` | Must already exist from Step 1 |
| `/workspace/experiments/basic_summary_stats_2026_04_27/README.md` | Tone reference only (this README must be much shorter) |

## Files allowed to change

- `/workspace/experiments/compare_keep_remove_rates_across_integrations_2026_08_04/README.md` (create)
- `/workspace/experiments/compare_keep_remove_rates_across_integrations_2026_08_04/RESULTS.md` (refresh via script run only)

## Files forbidden to change

- `/workspace/experiments/compare_keep_remove_rates_across_integrations_2026_08_04/compare_keep_remove_rates.py` (unless a Step 1 bug blocks the run; then fix under Step 1 rules)
- `/workspace/shared/data/**`
- Any other experiment folder
- Do **not** add files beyond `README.md`, `compare_keep_remove_rates.py`, and `RESULTS.md`

## README contract

`README.md` must contain only:

1. **Context** — one short paragraph: crosstab of keep/remove labels vs platform (Bluesky / Reddit / Twitter) for Study Phase 2 Part 2 modal keep/remove labels loaded via the shared dataset loader.
2. **Run command** — exact block:

```bash
PYTHONPATH=. uv run python experiments/compare_keep_remove_rates_across_integrations_2026_08_04/compare_keep_remove_rates.py
```

3. **Results pointer** — one line pointing at `RESULTS.md`.

No methodology essay, no interpretation of the table, no second commands.

## Exact commands

```bash
cd /workspace

PYTHONPATH=. uv run python experiments/compare_keep_remove_rates_across_integrations_2026_08_04/compare_keep_remove_rates.py

ls experiments/compare_keep_remove_rates_across_integrations_2026_08_04/
```

Expected `ls` output (exactly these three names, any order):

```text
README.md
RESULTS.md
compare_keep_remove_rates.py
```

## Pass / fail

**Pass:**

1. `README.md` has context + the exact `uv run` command + pointer to `RESULTS.md`, and nothing else of substance.
2. `RESULTS.md` matches the script’s current output (live counts).
3. Experiment folder contains exactly the three files listed above.

**Fail:**

1. Extra files (tests, notebooks, plots, `__init__.py`, etc.).
2. Verbose README or RESULTS with commentary.
3. Script not re-run after data/script changes so RESULTS is stale.
