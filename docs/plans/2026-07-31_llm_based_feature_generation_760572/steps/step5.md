# Step 5: 1% pilot run and RESULTS.md

## Goal

Execute the **1% pilot** against live `gpt-5.4-nano` using repo `.env` credentials. Write `RESULTS.md` with pilot themes and a clear gate on the 50% run. Tiny-sample verification is already covered by `smoke_tests/` (Step 4); this step is the substantive 1% pilot.

## Caller / unit of work

**Main caller:**

```bash
PYTHONPATH=. uv run python -m experiments.llm_based_feature_generation_2026_07_31.main \
  --sample-fraction 0.01 --seed 42
```

**In scope:** live 1% pilot, `RESULTS.md`, optional README note that smoke is the tiny-sample path and pilot is 1%.

**Out of scope:** committing; running the 50% corpus; changing `shared/schemas.py`; re-adding a `tests/` package.

## Files to inspect (read-only)

| Path | Why |
|------|-----|
| `/Users/mark/src/work/mirrorview-wt/experiments/llm_based_feature_generation_2026_07_31/main.py` | CLI entry |
| `/Users/mark/src/work/mirrorview-wt/experiments/llm_based_feature_generation_2026_07_31/smoke_tests/run_smoke.py` | Tiny-sample verification path (already done in Step 4) |
| `/Users/mark/src/work/mirrorview-wt/experiments/llm_based_feature_generation_2026_07_31/README.md` | Run instructions |

## Files allowed to change

- `/Users/mark/src/work/mirrorview-wt/experiments/llm_based_feature_generation_2026_07_31/RESULTS.md` (create after pilot)
- `/Users/mark/src/work/mirrorview-wt/experiments/llm_based_feature_generation_2026_07_31/README.md` (minor clarification only if needed)
- `/Users/mark/src/work/mirrorview-wt/experiments/llm_based_feature_generation_2026_07_31/outputs/**` (pilot runtime artifacts)

## Files forbidden to change

- `/Users/mark/src/work/mirrorview-wt/shared/schemas.py`
- `/Users/mark/src/work/mirrorview-wt/experiments/followup_model_error_analysis_2026_07_15/**`
- Do **not** create `experiments/llm_based_feature_generation_2026_07_31/tests/`
- Do not `git commit` unless the parent later asks

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

# 1% pilot (live) — not the smoke; smoke uses 1e-6 + 1+1 batches
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
| Verification split | Smoke remains the tiny-sample path; pilot is documented as 1% | Pilot confused with smoke flags |
| No commit | Working tree may have new files; no new commit created by this step | Unexpected commit |

## Done when

- CLI runs the 1% pilot end-to-end.
- `RESULTS.md` exists with pilot themes and 50% gate.
- Duplicate-prevention rules remain documented in README.
- `shared/schemas.py` still untouched for feature/theme schemas.
