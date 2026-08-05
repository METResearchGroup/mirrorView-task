# Step 2: Implement the dual-arm classifier runner

## Goal

Add `experiments/llm_prompt_engineering_2026_08_05/run_classifier.py` so one module can classify subset rows under either the **control** arm (study prompt only) or the **tuned** arm (study prompt + keep/remove feature addendum), via `research_tools.llm.runner.run`, model `gpt-5.4-nano`, and response schema `shared.schemas.IsRemoveResult`.

This step implements the runner wiring and a dry import/CLI parse check. A live multi-row smoke is Step 4. Do **not** write production `RESULTS.md` here.

## Caller / unit of work

**Main caller:** `run_classifier.py` CLI:

1. Load `experiments/llm_prompt_engineering_2026_08_05/subset_labels.csv` (must exist from Step 1).
2. Optionally limit to the first `N` rows (`--limit`) for smoke; default = all rows.
3. For each selected row, build one runner item: `message_id`, gold fields, `original_text`, `mirror_text`, `arm`.
4. Call `research_tools.llm.runner.run` once per arm requested (`control`, `tuned`, or `both`).
5. Persist under `experiments/llm_prompt_engineering_2026_08_05/outputs/{arm}/` (runner creates `outputs/{timestamp}/`).

**In scope:** `run_classifier.py` only (plus README CLI notes).

**Out of scope:** metrics / `evaluate.py`, `RESULTS.md`, prompt text edits, `shared/schemas.py` edits, production 500×2 run.

## Files to inspect (read-only)

| Path | Why |
|------|-----|
| `/Users/mark/src/work/mirrorView-task/experiments/llm_prompt_engineering_2026_08_05/generate_prompt.py` | `generate_prompt(..., add_keep_remove_features_addendum=...)` |
| `/Users/mark/src/work/mirrorView-task/experiments/llm_prompt_engineering_2026_08_05/prompt.py` | Control vs addendum content (do not edit) |
| `/Users/mark/src/work/mirrorView-task/shared/schemas.py` | `IsRemoveResult.is_remove: bool` |
| `/Users/mark/src/work/mirrorView-task/experiments/create_llm_features_2026_08_05/src/llm_generate_features.py` | Runner call-site + tqdm-wrapped `writer_map_fn` |
| `/Users/mark/src/work/mirrorView-task/experiments/llm_based_feature_generation_2026_07_31/stage1.py` | Same runner pattern |
| `/Users/mark/src/work/mirrorView-task/experiments/predict_keep_remove_2026_07_01/models/llm_finetuning/api_baselines/runner.py` | How `is_remove` maps to predicted label `0/1` |

## Files allowed to change

- `/Users/mark/src/work/mirrorView-task/experiments/llm_prompt_engineering_2026_08_05/run_classifier.py` (create)
- `/Users/mark/src/work/mirrorView-task/experiments/llm_prompt_engineering_2026_08_05/README.md` (append classifier CLI only)
- Runtime dirs under `experiments/llm_prompt_engineering_2026_08_05/outputs/` (created by runner; may remain empty until Step 4)

## Files forbidden to change

- `/Users/mark/src/work/mirrorView-task/shared/**`
- `/Users/mark/src/work/mirrorView-task/experiments/llm_prompt_engineering_2026_08_05/prompt.py`
- `/Users/mark/src/work/mirrorView-task/experiments/llm_prompt_engineering_2026_08_05/generate_prompt.py`
- `/Users/mark/src/work/mirrorView-task/experiments/llm_prompt_engineering_2026_08_05/subset_labels.csv` (read-only here)
- `/Users/mark/src/work/mirrorView-task/pyproject.toml`
- Do **not** create `evaluate.py` or `RESULTS.md` in this step

## Contracts to freeze

### Arms

| `--arm` value | `add_keep_remove_features_addendum` | Output base |
|---------------|--------------------------------------|-------------|
| `control` | `False` | `experiments/llm_prompt_engineering_2026_08_05/outputs/control` |
| `tuned` | `True` | `experiments/llm_prompt_engineering_2026_08_05/outputs/tuned` |
| `both` | run control then tuned sequentially | both bases above |

### Post text order

- `post_1_text` = `original_text`
- `post_2_text` = `mirror_text`
- No Post 1/Post 2 shuffle in this experiment (YAGNI; README does not require it).

### Prompt messages

`prompt_fn(item) -> list[dict]` must return chat messages the runner accepts. Use a single user message whose content is the string from `generate_prompt(...)` (same shape as sibling experiments that pass `[{"role": "user", "content": ...}]`).

### Response model

- Exactly `shared.schemas.IsRemoveResult`.
- Do **not** define a parallel local schema.

### Writer row (minimum fields)

Each JSON row written by `writer_map_fn` must include:

| Field | Source |
|-------|--------|
| `message_id` | item |
| `arm` | `"control"` or `"tuned"` |
| `keep_remove_label` | gold int from subset (`0` keep / `1` remove) |
| `decision` | gold string from subset |
| `predicted_is_remove` | `bool(result.is_remove)` |
| `predicted_label` | `int(result.is_remove)` (1 = remove, 0 = keep) |
| `result` | `result.model_dump()` |

### Runner wiring

Match `experiments/create_llm_features_2026_08_05/src/llm_generate_features.py`:

1. One subset row = one runner item (do **not** batch multiple posts into one LLM call).
2. `model="gpt-5.4-nano"` default. Do **not** pass `temperature=0.0` (registry forces temperature 1).
3. `output_base_path` = arm root above → runner writes `{arm_root}/outputs/{timestamp}/` with `metadata.json` + per-item JSON.
4. tqdm via wrapped `writer_map_fn` (`total=len(items)`); close in `finally`.
5. `run_metadata` must include: `arm`, `model`, `n_items`, `subset_path`, `limit` (or `null` if full), `seed` unused for sampling here but record subset provenance note `"subset_seed": 42`.

### CLI

```text
PYTHONPATH=. uv run python experiments/llm_prompt_engineering_2026_08_05/run_classifier.py \
  --arm {control|tuned|both} [--limit N] [--model gpt-5.4-nano] \
  [--subset experiments/llm_prompt_engineering_2026_08_05/subset_labels.csv]
```

- Default `--subset`: experiment `subset_labels.csv`.
- Default `--limit`: no limit (all rows).
- Require subset file exists; raise `FileNotFoundError` with the path if missing.
- `--limit` must be positive when set; raise `ValueError` otherwise.

## Exact commands (this step — no live LLM required)

```bash
cd /Users/mark/src/work/mirrorView-task

# subset must already exist from Step 1
test -f experiments/llm_prompt_engineering_2026_08_05/subset_labels.csv

PYTHONPATH=. uv run python -c "
from experiments.llm_prompt_engineering_2026_08_05 import run_classifier
from experiments.llm_prompt_engineering_2026_08_05.generate_prompt import generate_prompt
from shared.schemas import IsRemoveResult
assert hasattr(run_classifier, 'prompt_fn')
assert hasattr(run_classifier, 'writer_map_fn')
assert run_classifier.DEFAULT_MODEL == 'gpt-5.4-nano'
# control prompt must not contain the keep-feature addendum header language
ctrl = generate_prompt(post_1_text='a', post_2_text='b', add_keep_remove_features_addendum=False)
tuned = generate_prompt(post_1_text='a', post_2_text='b', add_keep_remove_features_addendum=True)
assert 'Imperative policy or punishment demands' not in ctrl
assert 'Imperative policy or punishment demands' in tuned
print('runner module + prompt arms OK')
"

PYTHONPATH=. uv run python experiments/llm_prompt_engineering_2026_08_05/run_classifier.py --help
```

### Expected pass / fail

| Check | Pass | Fail |
|-------|------|------|
| Import | module imports; `DEFAULT_MODEL == gpt-5.4-nano` | Import error / wrong model |
| Schema | uses `shared.schemas.IsRemoveResult` | Local duplicate schema |
| Prompt wiring | control omits addendum; tuned includes it | Arms identical |
| CLI | `--help` exits 0; `--arm` choices documented | Missing flags |
| No evaluate | no metrics table written | Premature `RESULTS.md` |

## Done when

1. `run_classifier.py` is importable and exposes `prompt_fn`, `writer_map_fn`, and a `main` CLI.
2. Control and tuned differ only by the existing addendum flag on `generate_prompt`.
3. Runner wiring matches the sibling `research_tools.llm.runner.run` call-site (model, response model, tqdm writer wrap, metadata).
4. README documents the classifier CLI.
5. No live production run and no `RESULTS.md` in this step.
