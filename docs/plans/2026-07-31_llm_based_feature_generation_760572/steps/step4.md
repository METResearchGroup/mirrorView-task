# Step 4: CLI entry, 1% pilot run, and RESULTS.md

## Goal

Add a CLI that selects sample fraction (default **0.01** for pilot; **0.50** for the gated full target), runs stage 1 then stage 2, and documents how duplicate post processing is avoided. Execute the **1% pilot** against live `gpt-5.4-nano` using repo `.env` credentials. Write `RESULTS.md` with pilot themes and a clear gate on the 50% run.

## Caller / unit of work

**Main caller:**

```bash
PYTHONPATH=. uv run python -m experiments.llm_based_feature_generation_2026_07_31.main --sample-fraction 0.01 --seed 42
```

**In scope:** `main.py`, README run instructions update, live 1% pilot, `RESULTS.md`.

**Out of scope:** committing; running the 50% corpus; changing `shared/schemas.py`.

## Files to inspect (read-only)

| Path | Why |
|------|-----|
| `/Users/mark/src/work/mirrorview-wt/experiments/llm_based_feature_generation_2026_07_31/stage1.py` | Stage-1 entry |
| `/Users/mark/src/work/mirrorview-wt/experiments/llm_based_feature_generation_2026_07_31/stage2.py` | Stage-2 entry |
| `/Users/mark/src/work/mirrorview-wt/experiments/llm_based_feature_generation_2026_07_31/batching.py` | Sampling / exclude ids |
| `/Users/mark/src/work/mirrorview-wt/.venv/lib/python3.12/site-packages/research_tools/env.py` | How `OPENAI_API_KEY` is loaded |
| `/Users/mark/src/work/mirrorview-wt/AGENTS.md` | `PYTHONPATH=.` convention |

## Files allowed to change

- `/Users/mark/src/work/mirrorview-wt/experiments/llm_based_feature_generation_2026_07_31/main.py` (create)
- `/Users/mark/src/work/mirrorview-wt/experiments/llm_based_feature_generation_2026_07_31/README.md` (update run instructions only)
- `/Users/mark/src/work/mirrorview-wt/experiments/llm_based_feature_generation_2026_07_31/RESULTS.md` (create after pilot)
- `/Users/mark/src/work/mirrorview-wt/experiments/llm_based_feature_generation_2026_07_31/outputs/**` (runtime artifacts; gitignored if repo ignores them — do not force-add secrets)

## Files forbidden to change

- `/Users/mark/src/work/mirrorview-wt/shared/schemas.py`
- `/Users/mark/src/work/mirrorview-wt/experiments/followup_model_error_analysis_2026_07_15/**`
- Do not `git commit` unless the parent later asks

## CLI contracts

Required flags / defaults:

| Flag | Default | Meaning |
|------|---------|---------|
| `--sample-fraction` | `0.01` | Fraction of Study 2 posts to sample (use `0.50` only after pilot + cost gate) |
| `--seed` | `42` | Deterministic sample |
| `--keep-per-batch` | `10` | Keep posts per stage-1 batch |
| `--remove-per-batch` | `10` | Remove posts per stage-1 batch |
| `--model` | `gpt-5.4-nano` | Model id |
| `--exclude-ids-from` | unset | Optional path to a prior stage-1 `metadata.json` or a JSON list of message ids; those ids are excluded before sampling |
| `--stage1-only` / `--stage2-only` | unset | Optional stage selectors; `--stage2-only` requires `--stage1-dir` |

Duplicate-prevention behavior to document in README and RESULTS:

1. Within a run: sampling without replacement; assert unique `message_id` across batches before calling the runner.
2. Across re-runs: `research_tools.llm.runner.run` always creates a **new** `outputs/{timestamp}/` folder (no resume/skip of already-written items). Operators avoid double-processing by (a) fixed seed + recorded ids in metadata, and/or (b) `--exclude-ids-from` pointing at a prior run’s processed id list.

## Exact commands

```bash
cd /Users/mark/src/work/mirrorview-wt

# Tiny end-to-end smoke (1 keep + 1 remove)
PYTHONPATH=. uv run python \
  experiments/llm_based_feature_generation_2026_07_31/smoke_tests/run_smoke.py

# Confirm key present (do not print the key)
PYTHONPATH=. uv run python -c "
from research_tools.env import EnvVarsContainer
k = EnvVarsContainer.get_env_var('OPENAI_API_KEY', required=True)
assert k and k.strip()
print('OPENAI_API_KEY ok')
"

# 1% pilot (live)
PYTHONPATH=. uv run python -m experiments.llm_based_feature_generation_2026_07_31.main \
  --sample-fraction 0.01 \
  --seed 42
# Expect: prints stage-1 output dir, stage-2 output dir; both contain metadata.json and >=1 result JSON
```

### Expected pass / fail

| Check | Pass | Fail |
|-------|------|------|
| Pilot | Both stages finish; theme JSON has a non-empty themes list or explicit empty with note | Auth/model errors after one retry with corrected model id |
| Outputs | Under `experiments/llm_based_feature_generation_2026_07_31/outputs/` | Written elsewhere |
| RESULTS.md | Records pilot themes, sample fraction 0.01, model, output paths; states 50% gated | Missing gate note / invents 50% results |
| No commit | Working tree may have new files; no new commit created by this step | Unexpected commit |

## Done when

- CLI runs the 1% pilot end-to-end.
- `RESULTS.md` exists with pilot themes and 50% gate.
- Duplicate-prevention rules are documented in README.
- `shared/schemas.py` still untouched for feature/theme schemas.
