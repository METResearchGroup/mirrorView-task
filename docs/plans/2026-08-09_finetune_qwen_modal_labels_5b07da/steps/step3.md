# Step 3: Wire train, inference, and evaluate wrappers

## Goal

Provide `train.py`, `inference.py`, and `evaluate.py` under `experiments/larger_finetune_qwen_model_2026_08_08/` that expose the **same CLIs and scientific behavior** as the prior experiment, with defaults pointed at the new experiment paths and W&B project name. Prefer calling into `experiments.finetune_qwen_model_2026_08_08` rather than copying TRL/PEFT/generation/metric code.

Do **not** require a full local GPU train for acceptance; dry-run / import / config tests are enough. Remote train is Step 6.

## Caller / unit of work

**Main callers:**

```bash
PYTHONPATH=. uv run --extra finetune-qwen-2026-08-08 python \
  experiments/larger_finetune_qwen_model_2026_08_08/train.py \
  --train-jsonl experiments/larger_finetune_qwen_model_2026_08_08/data/chat_train.jsonl \
  --output-dir /tmp/qwen_lora_modal_dry \
  --dry-run

PYTHONPATH=. uv run --extra finetune-qwen-2026-08-08 python \
  experiments/larger_finetune_qwen_model_2026_08_08/inference.py \
  --chat-jsonl experiments/larger_finetune_qwen_model_2026_08_08/data/chat_test.jsonl \
  --output-csv /tmp/modal_test_labels.csv \
  --mode baseline \
  --help

PYTHONPATH=. uv run --extra finetune-qwen-2026-08-08 python \
  experiments/larger_finetune_qwen_model_2026_08_08/evaluate.py \
  --help
```

**Happy path (non-dry-run train — remote later):** identical to prior experiment: bf16 LoRA on `Qwen/Qwen3-4B-Instruct-2507`, assistant-only loss, frozen hyperparams, W&B project `mirrorview-larger-finetune-qwen-2026-08-08`.

**Out of scope:** Docker; SageMaker submit; regenerating data; changing LoRA rank / lr / epochs.

## Files to inspect (read-only)

| Path | Why |
|------|-----|
| `/workspace/experiments/finetune_qwen_model_2026_08_08/train.py` | Import / wrap surface |
| `/workspace/experiments/finetune_qwen_model_2026_08_08/inference.py` | Import / wrap surface |
| `/workspace/experiments/finetune_qwen_model_2026_08_08/evaluate.py` | Metrics + RESULTS writer |
| `/workspace/experiments/finetune_qwen_model_2026_08_08/src/train_config.py` | Hyperparams / `MODEL_ID` |
| `/workspace/experiments/finetune_qwen_model_2026_08_08/src/parse_prediction.py` | Parser to reuse |
| `/workspace/experiments/finetune_qwen_model_2026_08_08/tests/` | Patterns to mirror thinly |

## Files allowed to change

- `/workspace/experiments/larger_finetune_qwen_model_2026_08_08/train.py`
- `/workspace/experiments/larger_finetune_qwen_model_2026_08_08/inference.py`
- `/workspace/experiments/larger_finetune_qwen_model_2026_08_08/evaluate.py`
- `/workspace/experiments/larger_finetune_qwen_model_2026_08_08/src/` only for thin re-exports (e.g. `train_config.py` that imports prior hyperparams and overrides `WANDB_PROJECT`)
- `/workspace/experiments/larger_finetune_qwen_model_2026_08_08/tests/` (dry-run / import / metric wiring)
- `/workspace/experiments/larger_finetune_qwen_model_2026_08_08/README.md` (CLI docs)
- `/workspace/experiments/finetune_qwen_model_2026_08_08/train.py` / `inference.py` / `evaluate.py` / `src/train_config.py` **only** for minimal extractions that make identity-free helpers importable (prior CLI defaults and W&B project for the unanimous experiment must remain unchanged)

## Files forbidden to change

- `/workspace/shared/**`
- `/workspace/experiments/finetune_qwen_model_2026_08_08/data/**`
- `/workspace/experiments/finetune_qwen_model_2026_08_08/RESULTS.md`
- Hyperparam values (`r`, `alpha`, lr, epochs, seq length, batch/accum)
- Prompt text

## Contracts to freeze

### Scientific (must match prior)

| Item | Value |
|------|-------|
| Model | `Qwen/Qwen3-4B-Instruct-2507` |
| LoRA | `r=16`, `alpha=32`, `dropout=0.05` |
| Precision | bf16 LoRA (not QLoRA) |
| Epochs / lr / schedule | 3 / `2e-4` / cosine + 3–5% warmup |
| Batch | 1 × grad accum 8 |
| `max_seq_length` | 2048 |
| Seed | 1 |
| Train JSONL | only `chat_train.jsonl` (never test) |
| Infer parse | same `parse_generation`; invalid → `__invalid__` |
| Metrics | accuracy / precision / recall / F1; positive = remove; invalid never correct |

### Identity overrides (new experiment only)

| Item | Value |
|------|-------|
| Default data paths | under `experiments/larger_finetune_qwen_model_2026_08_08/` |
| W&B project | `mirrorview-larger-finetune-qwen-2026-08-08` |
| RESULTS path | `experiments/larger_finetune_qwen_model_2026_08_08/RESULTS.md` |

### DRY gate

New `train.py` / `inference.py` / `evaluate.py` must not contain a second copy of the TRL trainer setup, PEFT target module list, generation loop, or sklearn metric block. Acceptable patterns:

1. Import and call prior `main()` / helpers with overridden argv/defaults, or
2. Import prior pure functions and supply new path/W&B constants in a <~40-line wrapper.

If prior modules cannot be imported without executing unanimous-specific defaults incorrectly, extract a small callable in the prior package (e.g. `run_train(...)`) **without** changing the prior CLI’s default paths or W&B project when invoked as that experiment’s `__main__`.

## Exact commands

```bash
cd /workspace

PYTHONPATH=. uv run --extra finetune-qwen-2026-08-08 python \
  experiments/larger_finetune_qwen_model_2026_08_08/train.py \
  --train-jsonl experiments/larger_finetune_qwen_model_2026_08_08/data/chat_train.jsonl \
  --output-dir /tmp/qwen_lora_modal_dry \
  --dry-run

PYTHONPATH=. uv run --extra finetune-qwen-2026-08-08 pytest \
  experiments/larger_finetune_qwen_model_2026_08_08/tests/ \
  -q

# Prior experiment still imports cleanly
PYTHONPATH=. uv run --extra finetune-qwen-2026-08-08 python -c "
from experiments.finetune_qwen_model_2026_08_08.src.train_config import WANDB_PROJECT, MODEL_ID
assert MODEL_ID == 'Qwen/Qwen3-4B-Instruct-2507'
assert WANDB_PROJECT == 'mirrorview-finetune-qwen-2026-08-08'
print('prior identity intact')
"
```

### Expected pass / fail

| Check | Pass | Fail |
|-------|------|------|
| Dry-run train | Exits 0; validates paths/config | Requires GPU download for dry-run |
| Wrapper size | Thin; imports prior logic | Large duplicated trainer/infer bodies |
| Prior identity | Unanimous W&B/project defaults unchanged | Prior defaults rewritten to modal names |
| Tests | New and prior test suites still meaningful | Broken prior tests |

## Done when

1. New train/infer/eval CLIs exist and dry-run/help succeed.
2. Scientific knobs match PR #54; only paths/W&B identity differ.
3. No duplicated TRL/PEFT/eval implementation in the new tree.
4. No SageMaker submit yet.
