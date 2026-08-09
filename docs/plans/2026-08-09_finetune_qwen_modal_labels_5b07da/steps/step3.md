# Step 3: Wire train, inference, and evaluate wrappers

## Goal

Provide `train.py`, `inference.py`, and `evaluate.py` under `experiments/larger_finetune_qwen_model_2026_08_08/` so they expose the same command line interfaces and scientific behavior as the earlier experiment, with defaults pointed at the new experiment paths and Weights and Biases project name. Prefer calling into `experiments.finetune_qwen_model_2026_08_08` rather than copying TRL, PEFT, generation, or metric code.

Do not require a full local GPU train for acceptance. Dry-run, import, and config tests are enough. Remote train is Step 6.

## Caller / unit of work

The main callers are these CLIs.

```bash
PYTHONPATH=. uv run --extra finetune-qwen-2026-08-08 python \
  experiments/larger_finetune_qwen_model_2026_08_08/train.py \
  --train-jsonl experiments/larger_finetune_qwen_model_2026_08_08/data/chat_train.jsonl \
  --output-dir /tmp/qwen_lora_larger_dry \
  --dry-run

PYTHONPATH=. uv run --extra finetune-qwen-2026-08-08 python \
  experiments/larger_finetune_qwen_model_2026_08_08/inference.py \
  --chat-jsonl experiments/larger_finetune_qwen_model_2026_08_08/data/chat_test.jsonl \
  --output-csv /tmp/larger_test_labels.csv \
  --mode baseline \
  --help

PYTHONPATH=. uv run --extra finetune-qwen-2026-08-08 python \
  experiments/larger_finetune_qwen_model_2026_08_08/evaluate.py \
  --help
```

A real train (not dry-run) later uses the same settings as the earlier experiment. That means bf16 LoRA on `Qwen/Qwen3-4B-Instruct-2507`, assistant-only loss, the frozen hyperparameters, and Weights and Biases project `mirrorview-larger-finetune-qwen-2026-08-08`.

Work that is out of scope includes Docker, SageMaker submit, regenerating data, and changing LoRA rank, learning rate, or epochs.

## Files to inspect (read-only)

| Path | Why |
|------|-----|
| `/workspace/experiments/finetune_qwen_model_2026_08_08/train.py` | Import or wrap surface |
| `/workspace/experiments/finetune_qwen_model_2026_08_08/inference.py` | Import or wrap surface |
| `/workspace/experiments/finetune_qwen_model_2026_08_08/evaluate.py` | Metrics and RESULTS writer |
| `/workspace/experiments/finetune_qwen_model_2026_08_08/src/train_config.py` | Hyperparameters and `MODEL_ID` |
| `/workspace/experiments/finetune_qwen_model_2026_08_08/src/parse_prediction.py` | Parser to reuse |
| `/workspace/experiments/finetune_qwen_model_2026_08_08/tests/` | Patterns to mirror thinly |

## Files allowed to change

- `/workspace/experiments/larger_finetune_qwen_model_2026_08_08/train.py`
- `/workspace/experiments/larger_finetune_qwen_model_2026_08_08/inference.py`
- `/workspace/experiments/larger_finetune_qwen_model_2026_08_08/evaluate.py`
- `/workspace/experiments/larger_finetune_qwen_model_2026_08_08/src/` only for thin re-exports, e.g. a `train_config.py` that imports earlier hyperparameters and overrides `WANDB_PROJECT`
- `/workspace/experiments/larger_finetune_qwen_model_2026_08_08/tests/` (dry-run, import, and metric wiring)
- `/workspace/experiments/larger_finetune_qwen_model_2026_08_08/README.md` (CLI docs)
- `/workspace/experiments/finetune_qwen_model_2026_08_08/train.py`, `inference.py`, `evaluate.py`, and `src/train_config.py` only for minimal extractions that make helpers without experiment-specific names importable. The earlier CLI defaults and Weights and Biases project for the unanimous experiment must stay unchanged.

## Files forbidden to change

- `/workspace/shared/**`
- `/workspace/experiments/finetune_qwen_model_2026_08_08/data/**`
- `/workspace/experiments/finetune_qwen_model_2026_08_08/RESULTS.md`
- Hyperparameter values (`r`, `alpha`, learning rate, epochs, sequence length, batch size, and gradient accumulation)
- Prompt text

## Contracts to freeze

### Scientific settings that must match the earlier experiment

| Item | Value |
|------|-------|
| Model | `Qwen/Qwen3-4B-Instruct-2507` |
| LoRA | `r=16`, `alpha=32`, `dropout=0.05` |
| Precision | bf16 LoRA (not QLoRA) |
| Epochs, learning rate, and schedule | 3 epochs, `2e-4`, cosine with 3% to 5% warmup |
| Batch | 1 with gradient accumulation 8 |
| `max_seq_length` | 2048 |
| Seed | 1 |
| Train JSONL | Only `chat_train.jsonl` (never the test file) |
| Infer parse | Same `parse_generation`, and invalid text becomes `__invalid__` |
| Metrics | Accuracy, precision, recall, and F1, with remove as the positive class, and invalid never counted as correct |

### Cloud and path names for the new experiment only

| Item | Value |
|------|-------|
| Default data paths | Under `experiments/larger_finetune_qwen_model_2026_08_08/` |
| W&B project | `mirrorview-larger-finetune-qwen-2026-08-08` |
| RESULTS path | `experiments/larger_finetune_qwen_model_2026_08_08/RESULTS.md` |

### DRY gate

The new `train.py`, `inference.py`, and `evaluate.py` must not contain a second copy of the TRL trainer setup, PEFT target module list, generation loop, or sklearn metric block. One acceptable pattern is to import and call an earlier `main()` or helper with overridden argv or defaults. Another is to import earlier pure functions and supply new path and Weights and Biases constants in a short wrapper of about 40 lines or fewer.

If earlier modules cannot be imported without using unanimous-specific defaults incorrectly, extract a small callable in the earlier package, e.g. `run_train(...)`, without changing the earlier CLI's default paths or Weights and Biases project when that package is run as `__main__`.

## Exact commands

```bash
cd /workspace

PYTHONPATH=. uv run --extra finetune-qwen-2026-08-08 python \
  experiments/larger_finetune_qwen_model_2026_08_08/train.py \
  --train-jsonl experiments/larger_finetune_qwen_model_2026_08_08/data/chat_train.jsonl \
  --output-dir /tmp/qwen_lora_larger_dry \
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
| Dry-run train | Exits 0 and validates paths and config | Requires a GPU model download for dry-run |
| Wrapper size | Thin, and imports earlier logic | Large duplicated trainer or infer bodies |
| Earlier cloud names | Unanimous Weights and Biases defaults unchanged | Earlier defaults rewritten to the larger-experiment names |
| Tests | New and earlier test suites still meaningful | Broken earlier tests |

## Done when

1. The new train, infer, and evaluate CLIs exist, and dry-run and help succeed.
2. The scientific settings match pull request 54, and only paths and Weights and Biases names differ.
3. There is no duplicated TRL, PEFT, or evaluate implementation in the new tree.
4. No SageMaker job has been submitted yet.
