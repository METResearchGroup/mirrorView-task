# Step 3: Implement thematic-commonality stage on the same runner

## Goal

Wire stage 2 so aggregated stage-1 feature JSON becomes one (or more) runner items whose structured output is the thematic commonality list. Same runner interface and output layout as stage 1. Prompt must not use FP/TN overrepresentation framing.

## Caller / unit of work

**Main caller:** `run_stage2(stage1_output_dir, *, output_base_path, model, ...)` that reads all `*.json` result files from a stage-1 output folder (skipping `metadata.json`), builds theme-synthesis item(s), calls `research_tools.llm.runner.run`, and returns the stage-2 output folder path.

**In scope:** `stage2.py`, offline wiring tests, optional tiny aggregator helper colocated in `stage2.py`.

**Out of scope:** live pilot, CLI, editing stage-1 prompts, `shared/schemas.py`.

## Files to inspect (read-only)

| Path | Why |
|------|-----|
| `/Users/mark/src/work/mirrorview-wt/.venv/lib/python3.12/site-packages/research_tools/llm/recipes/runner.py` | Call-site pattern |
| `/Users/mark/src/work/mirrorview-wt/experiments/llm_based_feature_generation_2026_07_31/stage1.py` | Output row shape to consume |
| `/Users/mark/src/work/mirrorview-wt/experiments/llm_based_feature_generation_2026_07_31/schemas.py` | Theme response model |
| `/Users/mark/src/work/mirrorview-wt/experiments/llm_based_feature_generation_2026_07_31/prompts.py` | Stage-2 prompt |
| `/Users/mark/src/work/mirrorview-wt/experiments/followup_model_error_analysis_2026_07_15/extract/prompts.py` | `CLUSTERING_PROMPT` lineage (what to avoid: FP/TN language) |

## Files allowed to change

- `/Users/mark/src/work/mirrorview-wt/experiments/llm_based_feature_generation_2026_07_31/stage2.py` (create)
- (no unit-test file; verify via `smoke_tests/run_smoke.py` once CLI exists)

## Files forbidden to change

- `/Users/mark/src/work/mirrorview-wt/shared/schemas.py`
- `/Users/mark/src/work/mirrorview-wt/experiments/followup_model_error_analysis_2026_07_15/**`
- Installed `research_tools` under `.venv/`

## Contracts

1. Load stage-1 result JSONs from a given directory; ignore `metadata.json`.
2. Build a single stage-2 item for the pilot path (YAGNI: no shard merge unless a single payload is impractical; for 1% pilot one item is required).
3. `prompt_fn` embeds the aggregated feature corpus JSON into the stage-2 prompt.
4. `response_model` = experiment theme-synthesis schema.
5. `writer_map_fn` persists `model_dump()` of the theme result plus `source_stage1_dir` and `n_stage1_batches`.
6. Default model `gpt-5.4-nano`; do not pass `temperature=0.0`.
7. `run_metadata` includes `stage="theme_synthesis"` and `source_stage1_dir`.

## Exact commands

```bash
cd /Users/mark/src/work/mirrorview-wt

PYTHONPATH=. uv run python -c "
from experiments.llm_based_feature_generation_2026_07_31 import stage2
assert hasattr(stage2, 'run_stage2')
assert hasattr(stage2, 'load_stage1_results')
print('stage2 wiring OK')
"

# Prompt hygiene
PYTHONPATH=. uv run python -c "
from experiments.llm_based_feature_generation_2026_07_31.prompts import THEME_SYNTHESIS_PROMPT
forbidden = ['FP', 'false positive', 'TN', 'false negative', 'over-represent', 'overrepresent']
low = THEME_SYNTHESIS_PROMPT.lower()
hits = [f for f in forbidden if f.lower() in low]
assert not hits, hits
print('theme prompt OK')
"
```

### Expected pass / fail

| Check | Pass | Fail |
|-------|------|------|
| Aggregator | Loads fixture JSON dir with 2 fake stage-1 files; returns list length 2 | Crash / includes metadata |
| Wiring check | exit 0 offline | ImportError |
| Prompt hygiene | no forbidden substrings | AssertionError with hits |

## Done when

- `stage2.py` can consume a stage-1 output folder and expose `run_stage2` on the research_tools runner.
- Offline tests pass; theme prompt has no FP/TN overrepresentation framing.
