# Step 2: Implement feature-generation stage on the research_tools runner

## Goal

Wire stage 1 so each keep/remove batch is one `research_tools.llm.runner.run` item: prompt → structured feature schema → JSON row under the experiment `outputs/{timestamp}/` tree. Model id is exactly `gpt-5.4-nano`. No unit-test file; live verification is via `smoke_tests/` (Step 4).

## Caller / unit of work

**Main caller:** a `run_stage1(batches, *, output_base_path, model, seed, sample_fraction, ...)` function that returns the output folder path. Invoked later from the CLI (Step 4); this step may include a thin import check without requiring API keys.

**In scope:** `stage1.py` (and tiny helpers only if required to keep `stage1.py` readable).

**Out of scope:** stage 2, CLI flags, live API pilot, LangChain clients, edits to `shared/schemas.py`, any `tests/` package.

## Files to inspect (read-only)

| Path | Why |
|------|-----|
| `/Users/mark/src/work/mirrorview-wt/.venv/lib/python3.12/site-packages/research_tools/llm/recipes/runner.py` | Canonical call-site pattern |
| `/Users/mark/src/work/mirrorview-wt/.venv/lib/python3.12/site-packages/research_tools/llm/runner.py` | `run(...)` signature and output layout |
| `/Users/mark/src/work/mirrorview-wt/.venv/lib/python3.12/site-packages/research_tools/config/models.yaml` | Confirm `gpt-5.4-nano` registry entry (temperature 1) |
| `/Users/mark/src/work/mirrorview-wt/experiments/llm_based_feature_generation_2026_07_31/schemas.py` | Stage-1 response model |
| `/Users/mark/src/work/mirrorview-wt/experiments/llm_based_feature_generation_2026_07_31/prompts.py` | Stage-1 prompt builder |
| `/Users/mark/src/work/mirrorview-wt/experiments/llm_based_feature_generation_2026_07_31/batching.py` | Batch dict shape |

## Files allowed to change

- `/Users/mark/src/work/mirrorview-wt/experiments/llm_based_feature_generation_2026_07_31/stage1.py` (create)

## Files forbidden to change

- `/Users/mark/src/work/mirrorview-wt/shared/schemas.py`
- `/Users/mark/src/work/mirrorview-wt/experiments/followup_model_error_analysis_2026_07_15/extract/extract_features.py`
- `/Users/mark/src/work/mirrorview-wt/.venv/**` (do not patch installed research_tools)
- Do **not** create `experiments/llm_based_feature_generation_2026_07_31/tests/`

## Contracts

Match the recipe pattern in `research_tools.llm.recipes.runner`:

1. `prompt_fn(item) -> list[dict]` with chat messages; item is one batch dict from `form_batches`.
2. `response_model` = experiment stage-1 schema.
3. `writer_map_fn(item, result) -> dict` must include: `batch_id`, sorted list of `message_ids`, keep/remove counts, and the structured result dumped to a JSON-serializable dict (`model_dump()`).
4. `run(..., model="gpt-5.4-nano", output_base_path=<experiment root>, run_metadata={...})`.
5. Do **not** pass `temperature=0.0` (registry forces temperature 1 for this model). Omit temperature or pass `1`.
6. `run_metadata` must record at least: `stage="feature_generation"`, `sample_fraction`, `seed`, `model`, and the full list of `message_ids` processed in this stage (flat, unique).

## Exact commands

```bash
cd /Users/mark/src/work/mirrorview-wt

PYTHONPATH=. uv run python -c "
from experiments.llm_based_feature_generation_2026_07_31 import stage1
from research_tools.llm.runner import run as _run
assert hasattr(stage1, 'run_stage1')
assert hasattr(stage1, 'prompt_fn')
assert hasattr(stage1, 'writer_map_fn')
print('stage1 wiring OK')
"
# Expect: prints 'stage1 wiring OK'
```

### Expected pass / fail

| Check | Pass | Fail |
|-------|------|------|
| Imports | stage1 imports `run` from `research_tools.llm.runner` | Imports LangChain extract client |
| Model default | default model string is exactly `gpt-5.4-nano` | Other id |
| Wiring check | exit 0; prints `stage1 wiring OK` | ImportError / missing attrs |
| No shared schema edit | `git diff -- shared/schemas.py` empty | Diff present |

## Done when

- `stage1.py` exposes `run_stage1` using the research_tools runner recipe.
- Offline import/wiring check passes.
- No LangChain extract path is imported.
- No `tests/` package under the experiment.
