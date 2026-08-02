# Step 4: CLI entry and smoke_tests harness

## Goal

Add a CLI that selects sample fraction and batch sizes, runs stage 1 then stage 2, and documents duplicate-prevention. Add an operable smoke harness under `smoke_tests/` that drives the **real** CLI on a **very small** sample (~1 stage-1 batch of 1 keep + 1 remove). This is the **tiny smoke validation** only; the 50% production run is Step 5 after approval. This is not a pytest unit suite.

## Caller / unit of work

**Main callers:**

```bash
# Full CLI (example flags; production 50% is Step 5 only after approval)
PYTHONPATH=. uv run python -m experiments.llm_based_feature_generation_2026_07_31.main \
  --sample-fraction 0.50 --seed 42

# Smoke (tiny live sample)
PYTHONPATH=. uv run python \
  experiments/llm_based_feature_generation_2026_07_31/smoke_tests/run_smoke.py
```

**In scope:** `main.py`, `smoke_tests/run_smoke.py`, README run instructions (smoke → **user approval** → 50% run).

**Out of scope:** 50% RESULTS write-up (Step 5); starting the 50% corpus in this step; creating/overwriting `experiments/llm_based_feature_generation_2026_07_31/data/sampled_subset.csv` (frozen 50% subset is **Step 5 only**); changing `shared/schemas.py`; any `tests/` package.

## Approval gate (mandatory)

**Do not start Step 5 until the user explicitly approves after reviewing Step 4 smoke results.**

This step ends when smoke passes and results are presented for human review. Implementers / operators must **stop** here: do not launch `--sample-fraction 0.50` (or otherwise begin Step 5) until that explicit approval is given. This is a **process gate for humans**, not necessarily a code lock — but the README must state the gate clearly so it cannot be missed.

## Files to inspect (read-only)

| Path | Why |
|------|-----|
| `/Users/mark/src/work/mirrorview-wt/experiments/llm_based_feature_generation_2026_07_31/stage1.py` | Stage-1 entry (includes tqdm progress from Step 2) |
| `/Users/mark/src/work/mirrorview-wt/experiments/llm_based_feature_generation_2026_07_31/stage2.py` | Stage-2 entry (includes tqdm progress from Step 3) |
| `/Users/mark/src/work/mirrorview-wt/experiments/llm_based_feature_generation_2026_07_31/batching.py` | Sampling / exclude ids; ceil behavior for tiny fractions; must load via `shared/data/` |
| `/Users/mark/src/work/mirrorview-wt/shared/data/dataloader.py` | Confirm smoke/CLI still go through shared Part 2 load (no 07_01 dataloader) |
| `/Users/mark/src/work/mirrorview-wt/.venv/lib/python3.12/site-packages/research_tools/env.py` | How `OPENAI_API_KEY` is loaded |
| `/Users/mark/src/work/mirrorview-wt/AGENTS.md` | `PYTHONPATH=.` convention |

## Files allowed to change

- `/Users/mark/src/work/mirrorview-wt/experiments/llm_based_feature_generation_2026_07_31/main.py` (create)
- `/Users/mark/src/work/mirrorview-wt/experiments/llm_based_feature_generation_2026_07_31/smoke_tests/run_smoke.py` (create)
- `/Users/mark/src/work/mirrorview-wt/experiments/llm_based_feature_generation_2026_07_31/README.md` (update run instructions only)
- `/Users/mark/src/work/mirrorview-wt/experiments/llm_based_feature_generation_2026_07_31/outputs/**` (smoke runtime artifacts)

## Files forbidden to change

- `/Users/mark/src/work/mirrorview-wt/shared/schemas.py`
- `/Users/mark/src/work/mirrorview-wt/shared/data/**`
- `/Users/mark/src/work/mirrorview-wt/experiments/followup_model_error_analysis_2026_07_15/**`
- `/Users/mark/src/work/mirrorview-wt/experiments/predict_keep_remove_2026_07_01/**`
- Do **not** create or overwrite `/Users/mark/src/work/mirrorview-wt/experiments/llm_based_feature_generation_2026_07_31/data/sampled_subset.csv` (Step 5 owns the frozen 50% subset)
- Do **not** create `experiments/llm_based_feature_generation_2026_07_31/tests/`
- Do not `git commit` unless the parent later asks

## CLI contracts

Required flags / defaults:

| Flag | Default | Meaning |
|------|---------|---------|
| `--sample-fraction` | `0.50` | Fraction of Part 2 modal keep/remove posts to sample for live/ad-hoc runs (**do not run 0.50 until user approval after smoke**; smoke overrides to a tiny fraction). The **frozen** 50% corpus file `data/sampled_subset.csv` is created/reused only in Step 5 — smoke must not write it. |
| `--seed` | `42` | Deterministic sample (for live fraction sampling / first-time Step 5 write only) |
| `--keep-per-batch` | `10` | Keep posts per stage-1 batch |
| `--remove-per-batch` | `10` | Remove posts per stage-1 batch |
| `--model` | `gpt-5.4-nano` | Model id |
| `--exclude-ids-from` | unset | Optional path to a prior stage-1 `metadata.json` or a JSON list of message ids; those ids are excluded before sampling |
| `--stage1-only` / `--stage2-only` | unset | Optional stage selectors; `--stage2-only` requires `--stage1-dir` |

Duplicate-prevention behavior to document in README:

1. Within a run: sampling without replacement; assert unique `message_id` across batches before calling the runner.
2. Across re-runs: `research_tools.llm.runner.run` always creates a **new** `outputs/{timestamp}/` folder (no resume/skip of already-written items). Operators avoid double-processing by (a) fixed seed + recorded ids in metadata, and/or (b) `--exclude-ids-from` pointing at a prior run’s processed id list.

README must also document:

1. Exact smoke command.
2. That smoke is the cheap validation path; after smoke comes **explicit user approval**, then Step 5’s frozen 50% run (no intermediate sample-size step).
3. **Do not start Step 5 until the user explicitly approves after reviewing Step 4 smoke results.**
4. Exact 50% command for Step 5 (after approval), including that Step 5 persists/reuses `data/sampled_subset.csv` and smoke must not write that file.

## Smoke contracts

`smoke_tests/run_smoke.py` must:

1. Call into existing `main` (or equivalent shared stage runners) — **do not** duplicate pipeline logic.
2. Use a tiny **live** sample that yields ~1 stage-1 batch (fraction params remain for smoke; do **not** use or write the frozen 50% subset):
   - `--sample-fraction 1e-6` (ceil still yields ≥1 row per class)
   - `--keep-per-batch 1 --remove-per-batch 1`
   - `--seed 42`
3. Still respect without-replacement / no-duplicate-labels (same batching path as the CLI).
4. Require `OPENAI_API_KEY` from repo-root `.env` (via `research_tools`).
5. Exit 0 and print `smoke: ok` when stage 1 and stage 2 both complete with output dirs under the experiment `outputs/` tree.
6. Inherit tqdm progress from stage1/stage2 (even if only one item, the bar should appear and complete).
7. **Must not** create or overwrite `experiments/llm_based_feature_generation_2026_07_31/data/sampled_subset.csv`. That file is Step 5’s frozen 50% corpus only.

## Exact commands

```bash
cd /Users/mark/src/work/mirrorview-wt

# Confirm key present (do not print the key)
PYTHONPATH=. uv run python -c "
from research_tools.env import EnvVarsContainer
k = EnvVarsContainer.get_env_var('OPENAI_API_KEY', required=True)
assert k and k.strip()
print('OPENAI_API_KEY ok')
"

# Tiny end-to-end smoke (1 keep + 1 remove → stage1 + stage2)
PYTHONPATH=. uv run python \
  experiments/llm_based_feature_generation_2026_07_31/smoke_tests/run_smoke.py
# Expect: prints smoke argv, corpus/sample/batches summary, stage1_dir=..., stage2_dir=...,
#         n_themes=..., and finally 'smoke: ok'
# Expect: new folders under experiments/llm_based_feature_generation_2026_07_31/outputs/
#         each with metadata.json and >=1 result JSON
```

Equivalent flags if invoking the CLI directly:

```bash
PYTHONPATH=. uv run python -m experiments.llm_based_feature_generation_2026_07_31.main \
  --sample-fraction 1e-6 \
  --keep-per-batch 1 \
  --remove-per-batch 1 \
  --seed 42
```

### Expected pass / fail

| Check | Pass | Fail |
|-------|------|------|
| Smoke | Exit 0; `smoke: ok`; both stages write under experiment `outputs/` | Auth/model errors; crash; zero batches |
| Batch uniqueness | Smoke run uses same batching path; 1 batch with 2 unique ids | Duplicate ids / silent re-use |
| No frozen subset | `data/sampled_subset.csv` absent or unchanged by smoke | Smoke created/overwrote the Step 5 50% subset file |
| Gate documented | README states: do not start Step 5 until user explicitly approves after reviewing Step 4 smoke results | Missing approval gate / implies auto-run 50% |
| Scale framing | Smoke is tiny validation; next is user approval then frozen 50% (Step 5) | Inserts an intermediate sample-size step between smoke and 50% |
| No unit tests | `tests/` absent under the experiment | Pytest suite present |
| README | Documents the exact smoke command with `PYTHONPATH=.` | Smoke undocumented / points at pytest |
| No commit | Working tree may have new files; no new commit created by this step | Unexpected commit |

## Done when

- CLI exists and can run both stages.
- `smoke_tests/run_smoke.py` exercises the real pipeline on a very small **live** sample (fraction params OK; no `sampled_subset.csv`).
- README documents smoke, the **explicit user approval gate**, and the post-approval 50% command (including frozen subset owned by Step 5).
- This step does **not** start the 50% run and does **not** write `data/sampled_subset.csv`.
- No `tests/` package under the experiment.
- `shared/schemas.py` untouched.
