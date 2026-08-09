# Step 5: Rewrite the README and freeze RESULTS

## Goal

Replace the outdated experiment README with the grill contract, and write `RESULTS.md` that presents the three analyses without statistical tests.

## Caller / unit of work

There is no runtime caller. The operator finishes Steps 1 through 4, then updates the two markdown files so a new reader can understand the question, the method, and the descriptive findings.

In scope: README and RESULTS only, plus links to existing output paths.

Out of scope: rerunning analyses, changing cohort rules, editing `GRILL.md` unless a factual conflict forces a one line pointer fix.

## Files to inspect (read only)

| Path | Why |
|------|-----|
| `/Users/mark/src/work/mirrorview-wt/experiments/unanimous_vs_majority_labels_2026_08_08/GRILL.md` | Locked claims and method |
| `/Users/mark/src/work/mirrorview-wt/experiments/unanimous_vs_majority_labels_2026_08_08/README.md` | Current outdated draft |
| `/Users/mark/src/work/mirrorview-wt/experiments/create_llm_features_2026_08_05/RESULTS.md` | Results doc tone precedent |
| `/Users/mark/src/work/mirrorview-wt/experiments/unanimous_vs_majority_labels_2026_08_08/outputs/analysis1/cell_summary.csv` | Numbers for RESULTS |
| `/Users/mark/src/work/mirrorview-wt/experiments/unanimous_vs_majority_labels_2026_08_08/outputs/analysis2/top_tokens_by_cell.csv` | Token tables for RESULTS |
| `/Users/mark/src/work/mirrorview-wt/experiments/unanimous_vs_majority_labels_2026_08_08/outputs/analysis3/stance_by_cell_all_strata.csv` | Stance tables for RESULTS |
| `/Users/mark/src/work/mirrorview-wt/docs/plans/2026-08-08_unanimous_vs_majority_labels_c8d521/plan.md` | Done bar |

## Files allowed to change

- `/Users/mark/src/work/mirrorview-wt/experiments/unanimous_vs_majority_labels_2026_08_08/README.md`
- `/Users/mark/src/work/mirrorview-wt/experiments/unanimous_vs_majority_labels_2026_08_08/RESULTS.md` (create)

## Files forbidden to change

- `/Users/mark/src/work/mirrorview-wt/experiments/unanimous_vs_majority_labels_2026_08_08/GRILL.md` unless fixing a broken path reference
- `/Users/mark/src/work/mirrorview-wt/experiments/unanimous_vs_majority_labels_2026_08_08/outputs/**`
- `/Users/mark/src/work/mirrorview-wt/shared/**`
- `/Users/mark/src/work/mirrorview-wt/experiments/rater_agreement_2026_08_06/**`
- `/Users/mark/src/work/mirrorview-wt/docs/plans/2026-08-08_unanimous_vs_majority_labels_c8d521/**`

## Contracts to freeze

### README required sections

The rewritten README must state, in plain language:

1. Primary and secondary claims from `GRILL.md`
2. Descriptive only method, with no hypothesis tests
3. Universe: linked fate, at least three raters, ties dropped
4. Four cell names and expected sizes on current data
5. Original text for Analyses 1 and 3 metrics and summaries
6. Analysis 1 feature list, including that PRIME is the shared binary `is_prime` label
7. Analysis 2 Stage 1 reuse and generate approach, token counting rules, and output paths
8. Analysis 3 three strata stance tables
9. How to run each script from repo root with `PYTHONPATH=. uv run python ...`
10. Pointer to `GRILL.md` and `RESULTS.md`
11. Explicit out of scope list matching the plan

The README must not say that exact ties are kept as a separate analysis cell.

### RESULTS required sections

`RESULTS.md` must include:

1. Cohort size and per cell counts from the written cohort file
2. Analysis 1 cell summary table, including high toxicity share and median length style metrics
3. Analysis 2 coverage counts (reused versus generated) and the top token tables, with links or paths to the four word cloud PNGs
4. Analysis 3 three stance tables, or the long table pivoted for display
5. A short descriptive reading of the primary claim and the secondary claim that does not claim statistical significance
6. Limitations: classifier labels can change across model calls, Stage 1 features used a dual text prompt, and PRIME is one binary label rather than four separate cues

### Tone

Follow the plain writing rules used for this plan packet. Prefer tables and concrete numbers over slogans.

## Exact commands

### 1. Confirm analysis artifacts exist before writing RESULTS

```bash
cd /Users/mark/src/work/mirrorview-wt
PYTHONPATH=. uv run python - <<'PY'
from pathlib import Path
base = Path("experiments/unanimous_vs_majority_labels_2026_08_08/outputs")
required = [
    base / "cohort" / "four_cell_cohort.csv",
    base / "analysis1" / "cell_summary.csv",
    base / "analysis2" / "coverage.json",
    base / "analysis2" / "top_tokens_by_cell.csv",
    base / "analysis2" / "wordcloud_unanimous_keep.png",
    base / "analysis2" / "wordcloud_majority_keep.png",
    base / "analysis2" / "wordcloud_majority_remove.png",
    base / "analysis2" / "wordcloud_unanimous_remove.png",
    base / "analysis3" / "stance_by_cell_all_strata.csv",
]
missing = [str(p) for p in required if not p.exists()]
assert not missing, missing
print("artifacts_ok", len(required))
PY
```

Expected:

```text
artifacts_ok 9
```

### 2. Grep guard against outdated README claims

```bash
cd /Users/mark/src/work/mirrorview-wt
rg -n "keep these separate|Exact ties: 275|political disagreement itself" experiments/unanimous_vs_majority_labels_2026_08_08/README.md || true
```

Expected after the rewrite: no matches for those outdated phrases.

### 3. Confirm RESULTS exists and mentions all three analyses

```bash
cd /Users/mark/src/work/mirrorview-wt
rg -n "Analysis 1|Analysis 2|Analysis 3|unanimous_keep|sample_high_toxicity" experiments/unanimous_vs_majority_labels_2026_08_08/RESULTS.md
```

Expected: at least one match for each of Analysis 1, Analysis 2, and Analysis 3.

## Pass / fail

Pass:

- README matches the grill contract and lists runnable commands.
- RESULTS cites the real output files and does not invent p values.
- Artifact check prints `artifacts_ok 9`.
- Outdated tie and headline politics phrases are gone from the README.

Fail:

- README still describes ties as part of the primary design.
- RESULTS is written before Analysis 1 through 3 outputs exist.
- `GRILL.md` is rewritten as a substitute for RESULTS.

## Commit gate

Commit README and RESULTS together after the three commands above pass.
