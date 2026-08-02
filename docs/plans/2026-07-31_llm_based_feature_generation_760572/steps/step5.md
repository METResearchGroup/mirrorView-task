# Step 5: 50% production run and RESULTS.md

## Goal

Execute the **50% production run** against live `gpt-5.4-nano` using repo `.env` credentials, run both stages to completion, and write `RESULTS.md` with the theme list. Tiny-sample verification is already covered by `smoke_tests/` (Step 4).

**Frozen 50% subset (this step only):** sample 50% of posts **once**, persist them to `experiments/llm_based_feature_generation_2026_07_31/data/sampled_subset.csv`, and on subsequent 50% runs **reuse that file if present** so posts/labels do not reshuffle. Step 4 smoke must **not** create or overwrite this file.

## Approval gate (mandatory — fail/stop if unmet)

**Do not start Step 5 until the user explicitly approves after reviewing Step 4 smoke results.**

Before any 50% CLI invocation:

1. Confirm Step 4 smoke completed successfully (`smoke: ok`).
2. Confirm the user has **explicitly approved** proceeding to the 50% run after reviewing those smoke results.
3. If approval has **not** been given: **stop**. Do not run `--sample-fraction 0.50`. Do not write `RESULTS.md` as if the production run happened. Do not create or overwrite `sampled_subset.csv`. This is a **process gate for humans** (not necessarily a code lock), but implementers must treat missing approval as a hard stop.

## Caller / unit of work

**Main caller:**

```bash
PYTHONPATH=. uv run python -m experiments.llm_based_feature_generation_2026_07_31.main \
  --sample-fraction 0.50 --seed 42
```

**In scope:** live 50% run to completion (with frozen-subset load-or-create), `RESULTS.md`, optional README note that smoke is the tiny-sample path and Step 5 is the 50% production run (after approval).

**Out of scope:** committing; inserting an intermediate sample-size run between smoke and 50%; changing `shared/schemas.py`; re-adding a `tests/` package; starting without user approval; letting smoke create/overwrite `sampled_subset.csv`.

## Frozen sampled-subset contract (exact)

**Exact path:**

`/Users/mark/src/work/mirrorview-wt/experiments/llm_based_feature_generation_2026_07_31/data/sampled_subset.csv`

**Behavior (Step 5 / 50% production path only):**

1. Before forming batches for the 50% run, check whether `sampled_subset.csv` exists at the path above.
2. **If it exists:** load it and use those rows as the production corpus. Do **not** re-sample. Do **not** overwrite the file. Seed is irrelevant for subset membership on this path (seed may still apply only if other RNG exists downstream; subset membership is frozen by the CSV).
3. **If it does not exist:** perform the 50% stratified sample **without replacement** (same rules as Step 1 / batching: no duplicate labels / each post id at most once; stratified by keep/remove). Use `--seed` **only for this first-time sample**. Write the result to `sampled_subset.csv` (create `data/` if needed), then proceed with that subset.
4. Re-runs of the 50% pipeline **must** use the frozen subset so labels/posts do not reshuffle across production attempts. New timestamped folders under `outputs/` are still fine; the **input subset** stays fixed.
5. This logic is **part of Step 5 only**. Step 4 smoke uses a tiny live sample via `--sample-fraction` / tiny batch sizes and must **never** create or overwrite `sampled_subset.csv`.

## Files to inspect (read-only)

| Path | Why |
|------|-----|
| `/Users/mark/src/work/mirrorview-wt/experiments/llm_based_feature_generation_2026_07_31/main.py` | CLI entry; wire load-or-create for 50% path |
| `/Users/mark/src/work/mirrorview-wt/experiments/llm_based_feature_generation_2026_07_31/batching.py` | Stratified sample without replacement (first-time write only) |
| `/Users/mark/src/work/mirrorview-wt/experiments/llm_based_feature_generation_2026_07_31/stage1.py` | Confirm tqdm progress is wired for the long stage-1 run |
| `/Users/mark/src/work/mirrorview-wt/experiments/llm_based_feature_generation_2026_07_31/stage2.py` | Confirm tqdm progress is wired for stage 2 |
| `/Users/mark/src/work/mirrorview-wt/experiments/llm_based_feature_generation_2026_07_31/smoke_tests/run_smoke.py` | Confirm smoke does **not** write `data/sampled_subset.csv` |
| `/Users/mark/src/work/mirrorview-wt/experiments/llm_based_feature_generation_2026_07_31/README.md` | Run instructions + approval gate |

## Files allowed to change

- `/Users/mark/src/work/mirrorview-wt/experiments/llm_based_feature_generation_2026_07_31/RESULTS.md` (create after 50% run)
- `/Users/mark/src/work/mirrorview-wt/experiments/llm_based_feature_generation_2026_07_31/README.md` (minor clarification only if needed)
- `/Users/mark/src/work/mirrorview-wt/experiments/llm_based_feature_generation_2026_07_31/data/sampled_subset.csv` (create on first 50% sample only; load on subsequent 50% runs; never overwritten once present)
- `/Users/mark/src/work/mirrorview-wt/experiments/llm_based_feature_generation_2026_07_31/main.py` and/or `/Users/mark/src/work/mirrorview-wt/experiments/llm_based_feature_generation_2026_07_31/batching.py` (only as needed to implement load-or-create for the 50% path)
- `/Users/mark/src/work/mirrorview-wt/experiments/llm_based_feature_generation_2026_07_31/outputs/**` (50% runtime artifacts)

## Files forbidden to change

- `/Users/mark/src/work/mirrorview-wt/shared/schemas.py`
- `/Users/mark/src/work/mirrorview-wt/shared/data/**`
- `/Users/mark/src/work/mirrorview-wt/experiments/followup_model_error_analysis_2026_07_15/**`
- `/Users/mark/src/work/mirrorview-wt/experiments/predict_keep_remove_2026_07_01/**`
- `/Users/mark/src/work/mirrorview-wt/experiments/llm_based_feature_generation_2026_07_31/smoke_tests/**` (smoke must stay tiny-live-sample; must not write `sampled_subset.csv`)
- Do **not** create `experiments/llm_based_feature_generation_2026_07_31/tests/`
- Do not `git commit` unless the parent later asks
- Do **not** let Step 4 / smoke create or overwrite `experiments/llm_based_feature_generation_2026_07_31/data/sampled_subset.csv`

## Exact commands

```bash
cd /Users/mark/src/work/mirrorview-wt

# STOP unless user has explicitly approved after reviewing Step 4 smoke results.

# Confirm key present (do not print the key)
PYTHONPATH=. uv run python -c "
from research_tools.env import EnvVarsContainer
k = EnvVarsContainer.get_env_var('OPENAI_API_KEY', required=True)
assert k and k.strip()
print('OPENAI_API_KEY ok')
"

# 50% production run (live) — not the smoke; smoke uses 1e-6 + 1+1 batches
# First run: creates data/sampled_subset.csv if missing (seed applies to that first sample only).
# Later runs: loads data/sampled_subset.csv and must not reshuffle membership.
PYTHONPATH=. uv run python -m experiments.llm_based_feature_generation_2026_07_31.main \
  --sample-fraction 0.50 \
  --seed 42
# Expect: tqdm progress during stage 1 and stage 2; prints stage-1 output dir, stage-2 output dir;
#         both contain metadata.json and >=1 result JSON; run completes fully;
#         experiments/llm_based_feature_generation_2026_07_31/data/sampled_subset.csv exists
```

### Expected pass / fail

| Check | Pass | Fail |
|-------|------|------|
| Approval | User explicitly approved after Step 4 smoke before this command | 50% started without approval |
| Frozen subset first run | If CSV absent: 50% stratified sample without replacement written to `data/sampled_subset.csv`; seed used for that sample | CSV missing after claimed first 50% run; duplicates; wrong fraction path |
| Frozen subset re-run | If CSV present: loaded and used; file not overwritten; same post ids as prior 50% corpus | Re-sampled / reshuffled labels or posts; CSV rewritten |
| Smoke isolation | Step 4 smoke never creates/overwrites `data/sampled_subset.csv` | Smoke wrote or clobbered the 50% subset file |
| Production run | Both stages finish on the frozen 50% subset; theme JSON has a non-empty themes list or explicit empty with note | Auth/model errors after one retry with corrected model id; early abort treated as success |
| Progress | tqdm advances across stage-1 batches (and stage-2 items) during the run | Silent long hang with no progress UI |
| Outputs | Under `experiments/llm_based_feature_generation_2026_07_31/outputs/` | Written elsewhere |
| RESULTS.md | Records 50% themes, sample fraction 0.50, model, output paths, and notes the frozen subset path | Invents results / omits fraction or subset path |
| Verification split | Smoke remains the tiny-sample path; Step 5 owns the frozen 50% subset | Step 5 confused with smoke flags or an intermediate sample-size run |
| No commit | Working tree may have new files; no new commit created by this step | Unexpected commit |

## Done when

- Explicit user approval after Step 4 smoke was obtained before the run.
- `data/sampled_subset.csv` exists from the first 50% sample (or was already present and reused).
- CLI runs the 50% corpus end-to-end to completion on that frozen subset (with tqdm progress).
- Re-running the 50% command reuses the same subset (no reshuffle).
- `RESULTS.md` exists with the 50% run themes (fraction 0.50, model, output paths, frozen subset path).
- Duplicate-prevention rules remain documented in README; smoke still does not write the frozen subset file.
- `shared/schemas.py` still untouched for feature/theme schemas.
