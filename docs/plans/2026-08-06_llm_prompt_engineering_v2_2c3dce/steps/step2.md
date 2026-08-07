# Step 2: Wire dual-arm classifier defaults for v2 (Qwen 3.6)

## Goal

Add `experiments/llm_prompt_engineering_v2_2026_08_05/run_classifier.py` that **imports** prompt/writer/item helpers from v1 and runs the same dual-arm classifier via `research_tools.llm.runner.run`, with defaults pointed at the **v2 subset**, **v2 outputs tree**, and model id **`qwen/qwen3.6-plus`** (research_tools Bedrock registration for latest Qwen 3.6).

This step is wiring + dry import/CLI checks only. Live smoke is Step 4. Do **not** write production `RESULTS.md`.

## Caller / unit of work

**Main caller:** `run_classifier.py` CLI under the v2 tree:

1. Load `experiments/llm_prompt_engineering_v2_2026_08_05/subset_labels.csv` (from Step 1).
2. Optional `--limit` for smoke; default = all 1000 rows.
3. Import from v1: `Arm`, `ARM_ADDENDUM`, `prompt_fn`, `writer_map_fn`, `load_subset`, `rows_to_items`, `resolve_arms`, `_wrap_writer_with_progress` (and any other pure helpers needed).
4. Locally redefine only what must change: `DEFAULT_MODEL = "qwen/qwen3.6-plus"`, `DEFAULT_SUBSET_PATH`, `OUTPUTS_ROOT`, `arm_output_base`, `run_arm`, `parse_args`, `main`.
5. Call `research_tools.llm.runner.run` once per concrete arm with v2 `output_base_path`.

**In scope:** v2 `run_classifier.py` + README classifier CLI notes.

**Out of scope:** metrics / `evaluate.py`, `RESULTS.md`, prompt text edits, `shared/**` edits, production 1000×2 run, edits to v1 modules.

## Files to inspect (read-only)

| Path | Why |
|------|-----|
| `/workspace/experiments/llm_prompt_engineering_2026_08_05/run_classifier.py` | Import helpers; mirror `run_arm` shape with new defaults |
| `/workspace/experiments/llm_prompt_engineering_2026_08_05/generate_prompt.py` | Still used transitively via v1 `prompt_fn` |
| `/workspace/shared/schemas.py` | `IsRemoveResult` (via v1 writer) |
| research_tools `config/models.yaml` + `providers/bedrock_provider.py` | Public model id `qwen/qwen3.6-plus` resolves to Bedrock |
| `/workspace/AGENTS.md` | AWS creds for Bedrock in cloud env (`LAB_AWS_*` → `AWS_*`) |

## Files allowed to change

- `/workspace/experiments/llm_prompt_engineering_v2_2026_08_05/run_classifier.py` (create)
- `/workspace/experiments/llm_prompt_engineering_v2_2026_08_05/README.md` (append classifier CLI only)

## Files forbidden to change

- `/workspace/shared/**`
- `/workspace/experiments/llm_prompt_engineering_2026_08_05/**`
- `/workspace/experiments/llm_prompt_engineering_v2_2026_08_05/subset_labels.csv` (read-only here)
- `/workspace/pyproject.toml`
- Do **not** create `evaluate.py` or `RESULTS.md` in this step

## Contracts to freeze

### Defaults (exact)

| Name | Value |
|------|-------|
| `DEFAULT_MODEL` | `qwen/qwen3.6-plus` |
| Default subset | `experiments/llm_prompt_engineering_v2_2026_08_05/subset_labels.csv` |
| Control output base | `experiments/llm_prompt_engineering_v2_2026_08_05/outputs/control` |
| Tuned output base | `experiments/llm_prompt_engineering_v2_2026_08_05/outputs/tuned` |
| `subset_seed` in metadata | `42` |

### Arms

Same as v1: `control` / `tuned` / `both`. Control omits feature addendum; tuned includes it — via imported `prompt_fn` / `ARM_ADDENDUM`.

### Response model

Exactly `shared.schemas.IsRemoveResult` (do not define a local schema).

### Writer row

Reuse v1 `writer_map_fn` unchanged (same fields).

### Runner wiring

Match v1 `run_arm`:

1. One subset row = one runner item.
2. `model` default `qwen/qwen3.6-plus`.
3. `output_base_path` = v2 arm root → runner writes `{arm_root}/outputs/{timestamp}/`.
4. tqdm via wrapped `writer_map_fn`; close in `finally`.
5. `run_metadata` includes: `arm`, `model`, `n_items`, `subset_path`, `limit`, `subset_seed=42`, plus `"experiment": "llm_prompt_engineering_v2_2026_08_05"`.

### CLI

```text
PYTHONPATH=. uv run python experiments/llm_prompt_engineering_v2_2026_08_05/run_classifier.py \
  --arm {control|tuned|both} [--limit N] [--model qwen/qwen3.6-plus] \
  [--subset experiments/llm_prompt_engineering_v2_2026_08_05/subset_labels.csv]
```

## Exact commands (this step — no live LLM required)

```bash
cd /workspace

test -f experiments/llm_prompt_engineering_v2_2026_08_05/subset_labels.csv

PYTHONPATH=. uv run python -c "
from experiments.llm_prompt_engineering_v2_2026_08_05 import run_classifier as v2
from experiments.llm_prompt_engineering_2026_08_05 import run_classifier as v1
assert v2.DEFAULT_MODEL == 'qwen/qwen3.6-plus'
assert v1.DEFAULT_MODEL == 'gpt-5.4-nano'
assert hasattr(v2, 'prompt_fn') or hasattr(v1, 'prompt_fn')
# v2 must not hardcode gpt-5.4-nano as default
assert 'gpt-5.4-nano' not in str(v2.DEFAULT_MODEL)
assert 'llm_prompt_engineering_v2_2026_08_05' in str(v2.DEFAULT_SUBSET_PATH)
print('v2 classifier defaults OK')
"

PYTHONPATH=. uv run python experiments/llm_prompt_engineering_v2_2026_08_05/run_classifier.py --help
```

### Expected pass / fail

| Check | Pass | Fail |
|-------|------|------|
| Import | module imports; `DEFAULT_MODEL == qwen/qwen3.6-plus` | Import error / wrong model |
| Paths | defaults under `.../llm_prompt_engineering_v2_2026_08_05/` | Points at v1 paths |
| Prompt wiring | reuses v1 `prompt_fn` (control ≠ tuned) | Local prompt rewrite |
| Schema | uses `shared.schemas.IsRemoveResult` | Local duplicate schema |
| CLI | `--help` exits 0; `--arm` choices documented | Missing flags |
| No evaluate | no metrics table written | Premature `RESULTS.md` |

## Done when

1. v2 `run_classifier.py` is importable with Qwen 3.6 + v2 path defaults.
2. Prompt/writer/item logic is imported from v1, not copied wholesale.
3. README documents the classifier CLI with the Qwen model id.
4. No live production run and no `RESULTS.md` in this step.
