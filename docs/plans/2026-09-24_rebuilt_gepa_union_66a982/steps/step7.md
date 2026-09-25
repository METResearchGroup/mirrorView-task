# Step 7: RESULTS.md, analysis hooks, and docs

## Scope

- **Caller:** `experiments/predict_keep_remove_jev_gepa_2026_09_23/RESULTS.md`, `SETUP.md`, `jev_gepa_rebuilt/README.md`, repo `CHANGELOG.md`, `analysis/run.py` or `analysis/cluster_errors.py` entry for rebuilt vs union A1
- **Task:** Add a **Rebuilt GEPA (union cohort)** section to RESULTS.md with an ablation table vs Stage A union A1 pair test F1 **0.538**. Include columns for dev-A F1, dev-B F1, test F1, reflection iterations (or proposal count), acceptance rate, stop reason, reflection USD, and optimized prompt length. Optionally run error clustering that compares **R1** to union **A1** through the existing `analysis/` pipeline. Update SETUP.md and the jev_gepa_rebuilt README with operator commands, and add a CHANGELOG entry for the rebuild.
- **Out of scope:** Re-running production optimizes, changing scoring code, editing plan.md/design.md unless fixing typos found during results write-up.

## Dependencies

Step 6 artifacts for each launched ablation: `dev_selection.json`, `gepa_result.json`, `candidate_dev_scores.jsonl`, `test_results.json`, `stop_reason.json`, `reflection_usage.jsonl`.

## Files to inspect (read-only)

| Path | Why |
|------|-----|
| `/workspace/experiments/predict_keep_remove_jev_gepa_2026_09_23/RESULTS.md` | Stage A union table format, A1 0.5384 |
| `/workspace/experiments/predict_keep_remove_jev_gepa_2026_09_23/analysis/run.py` | Orchestration pattern |
| `/workspace/experiments/predict_keep_remove_jev_gepa_2026_09_23/analysis/cluster_errors.py` | Cluster inputs |
| `/workspace/experiments/predict_keep_remove_jev_gepa_2026_09_23/jev_baseline/outputs_union/A1_pair_study_prompt/results.json` | Union baseline reference |

## Files allowed to change

- `/workspace/experiments/predict_keep_remove_jev_gepa_2026_09_23/RESULTS.md`
- `/workspace/experiments/predict_keep_remove_jev_gepa_2026_09_23/SETUP.md`
- `/workspace/experiments/predict_keep_remove_jev_gepa_2026_09_23/jev_gepa_rebuilt/README.md`
- `/workspace/CHANGELOG.md` (repo root) or `/workspace/experiments/predict_keep_remove_jev_gepa_2026_09_23/CHANGELOG.md` if that is the project convention (use whichever file already has experiment entries; grep first)
- `/workspace/experiments/predict_keep_remove_jev_gepa_2026_09_23/jev_gepa_rebuilt/summarize_results.py` (new, build table rows from outputs)
- `/workspace/experiments/predict_keep_remove_jev_gepa_2026_09_23/jev_gepa_rebuilt/tests/test_summarize_results.py` (new)
- `/workspace/experiments/predict_keep_remove_jev_gepa_2026_09_23/analysis/run_rebuilt.py` (new, thin wrapper) **or** extend `analysis/run.py` with `--rebuilt-r1` flag (prefer new file to avoid Stage B coupling)

## Files forbidden to change

- `/workspace/docs/plans/2026-09-24_rebuilt_gepa_union_66a982/plan.md`
- `/workspace/docs/plans/2026-09-24_rebuilt_gepa_union_66a982/design.md`
- `/workspace/docs/plans/2026-09-24_rebuilt_gepa_union_66a982/steps/step1.md` through `step6.md`

## Contracts

### `summarize_results.py`

```python
def load_ablation_summary(ablation_id: str, outputs_root: Path) -> dict:
    """Merge dev_selection, stop_reason, gepa_result, test_results, reflection totals."""

def format_results_markdown_table(rows: list[dict], baseline_a1_test_f1: float = 0.538) -> str:
    """Markdown table for RESULTS.md section."""
```

Row fields:

| Column | Source |
|--------|--------|
| Ablation | `ablation_id` |
| dev-A F1 | `dev_selection.json` `dev_a_f1` |
| dev-B F1 | `dev_selection.json` `dev_b_f1` |
| test F1 | `test_results.json` at dev-A threshold |
| test F1 @0.5 | `test_results.json` at 0.5 |
| iterations | `len(gepa_result.candidates) - 1` or logged proposal count |
| accept rate | accepted / (accepted + rejected) from smoke log extended in production log `acceptance_log.jsonl` |
| stop reason | `stop_reason.json` |
| reflection USD | `dev_selection.json` or sum `reflection_usage.jsonl` |
| prompt chars | length of selected `study_instruction` |

Baseline row (read-only cite): **A1_pair_study_prompt** union test F1 **0.538** (do not re-run).

### RESULTS.md section template

Insert after **Stage A on Part 2 + Part 3 union** (or new `## Rebuilt GEPA (jev_gepa_rebuilt)`):

- Headline: state whether R1 beats A1 0.538 on test at the dev-A threshold.
- Table for R1, R2, R3, R4, R5, R6, R7 (omit rows not run).
- Spend summary: sum reflection USD and Jev USD from `test_results` and optimize logs, then compare the total to the plan ceiling of about $40 to $60.
- Link Wandb group `jev_gepa_rebuilt` and S3 prefix.

### Optional error clustering (R1 vs union A1)

```bash
export AWS_ACCESS_KEY_ID="$LAB_AWS_ACCESS_KEY_ID"
export AWS_SECRET_ACCESS_KEY="$LAB_AWS_ACCESS_KEY_SECRET"
PYTHONPATH=. uv run python experiments/predict_keep_remove_jev_gepa_2026_09_23/analysis/run_rebuilt.py \
  --baseline-ablation A1_pair_study_prompt \
  --gepa-ablation R1_gepa_pair \
  --split test
```

Wrapper calls `run_cluster_analysis` with:

- Baseline predictions: `jev_baseline/outputs_union/A1_pair_study_prompt/labels.parquet` (or union path from RESULTS.md)
- GEPA predictions: `jev_gepa_rebuilt/outputs/R1_gepa_pair/labels.parquet` from evaluate step

Upload under `experiments/predict_keep_remove_jev_gepa_2026_09_23/analysis/outputs/rebuilt_r1_vs_a1/`. If you run clustering, add 2 to 3 sentences in RESULTS.md on the largest topic deltas (optional).

### SETUP.md additions

- Data: `cohort_union_splits.parquet`, `data/dev_ab_split.json` generation command from Step 4.
- Secrets: `OPENAI_API_KEY`, Jev credentials, `HF_TOKEN` if needed, AWS export lines from AGENTS.md.
- Approval flag for R7.

### README (`jev_gepa_rebuilt/README.md`)

Expand beyond Step 1 stub: pointer to plan folder, smoke commands from Step 5, production commands from Step 6, evaluate command.

### CHANGELOG

One entry, date 2026-09-24, bullet: rebuilt GEPA on union cohort (`jev_gepa_rebuilt`), study-instruction optimization, ablations R1 to R7.

## Tests to write first

### `tests/test_summarize_results.py`

Class `TestSummarizeResults`.

```text
given fixture dev_selection test_results stop_reason json files in tmp ablation dir
when load_ablation_summary R1_gepa_pair
then test_f1 matches fixture and reflection_usd > 0

when format_results_markdown_table with one row and baseline 0.538
then markdown contains R1_gepa_pair and 0.538
```

## Implementation order

1. `summarize_results.py` + tests with fixtures
2. Generate markdown via CLI `--write-results-md` dry-run to stdout for review
3. Paste into RESULTS.md manually or via guarded `--update-results` flag
4. SETUP.md, README, CHANGELOG
5. Optional `run_rebuilt.py` clustering

## Commands

```bash
cd /workspace
PYTHONPATH=. uv run pytest experiments/predict_keep_remove_jev_gepa_2026_09_23/jev_gepa_rebuilt/tests/test_summarize_results.py -q
```

Expected: exit 0.

```bash
PYTHONPATH=. uv run python experiments/predict_keep_remove_jev_gepa_2026_09_23/jev_gepa_rebuilt/summarize_results.py \
  --ablation-ids R1_gepa_pair R2_majority_weighted R3_gepa_pair_terra \
  --baseline-test-f1 0.538
```

Expected: markdown table printed to stdout with dev-A, dev-B, test F1 columns.

```bash
PYTHONPATH=. uv run python experiments/predict_keep_remove_jev_gepa_2026_09_23/jev_gepa_rebuilt/summarize_results.py \
  --ablation-ids R1_gepa_pair --write-results-md \
  --results-path experiments/predict_keep_remove_jev_gepa_2026_09_23/RESULTS.md
```

Expected: RESULTS.md contains `## Rebuilt GEPA` section; exit 0.

Optional clustering:

```bash
PYTHONPATH=. uv run python experiments/predict_keep_remove_jev_gepa_2026_09_23/analysis/run_rebuilt.py --gepa-ablation R1_gepa_pair --baseline-ablation A1_pair_study_prompt
```

Expected: `analysis/outputs/rebuilt_r1_vs_a1/cluster_errors/` artifacts exist.

## Must pass

- RESULTS.md rebuilt section cites union A1 **0.538** baseline and reports dev-A/dev-B/test for each run ablation.
- Summarize script matches on-disk JSON artifacts (no hand-entered F1).
- SETUP.md documents union parquet and dev-A/B sidecar.
- CHANGELOG entry added.

## Must fail

- Claiming test F1 without `test_results.json` on disk.
- Overwriting Stage A union tables or Part 3-only numbers.

## Commit message

`document rebuilt gepa union results setup and optional r1 vs a1 clustering`

## Done check

- `test_summarize_results.py` green.
- RESULTS.md section present with ablation table, iteration/accept/stop/reflection columns.
- README and SETUP updated; CHANGELOG entry committed.
- If clustering run: RESULTS.md mentions output path under `analysis/outputs/rebuilt_r1_vs_a1/`.
