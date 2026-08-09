# Step 3: Implement training entrypoint (TRL + PEFT LoRA)

## Goal

Implement `experiments/finetune_qwen_model_2026_08_08/train.py` so it can fine-tune LoRA adapters on `data/chat_train.jsonl` with the locked hyperparams, assistant-only loss, bf16, and W&B logging. The same entrypoint must be usable as the SageMaker container `train` mode (paths via CLI/env).

Do **not** require a successful full GPU train on the developer laptop for step acceptance if no GPU is available; unit-test config wiring and a dry-run/path-validation path. Full remote train is Step 8.

## Caller / unit of work

**Main caller:** `train.py` CLI.

```text
PYTHONPATH=. uv run --extra finetune-qwen-2026-08-08 python \
  experiments/finetune_qwen_model_2026_08_08/train.py \
  --train-jsonl experiments/finetune_qwen_model_2026_08_08/data/chat_train.jsonl \
  --output-dir /tmp/qwen_lora_out \
  [--dry-run]
```

Happy path (non-dry-run):

1. Fail fast if `HF_TOKEN` missing/empty when loading the model (same rule as remote).
2. Set seeds to `1` (python/random/numpy/torch).
3. Load tokenizer + `Qwen/Qwen3-4B-Instruct-2507` in bf16.
4. Attach PEFT LoRA with frozen config.
5. Load **only** `chat_train.jsonl` (never chat_test).
6. Train with TRL `SFTTrainer` / `SFTConfig`: assistant-only loss; 3 epochs; lr `2e-4`; cosine schedule; warmup ratio in `[0.03, 0.05]`; per-device batch `1`; grad accum `8`; `max_seq_length=2048`.
7. Log to W&B project `mirrorview-finetune-qwen-2026-08-08` using `WANDB_API_KEY` from `lib.load_env_vars.EnvVarsContainer` (required for non-dry-run).
8. Save adapter (+ tokenizer files as needed) under `--output-dir`.

**Out of scope:** inference; evaluation; Docker; SageMaker submit; using test JSONL for early stopping or training.

## Files to inspect (read-only)

| Path | Why |
|------|-----|
| `/workspace/experiments/predict_keep_remove_2026_07_01/HOW_TO_DO_LLM_FINETUNING.md` | PEFT target modules + `alpha=2*r` + assistant masking note |
| `/workspace/lib/load_env_vars.py` | `EnvVarsContainer.get_env_var` |
| `/workspace/experiments/predict_keep_remove_2026_07_01/models/modernbert/train.py` | Precedent for HF Trainer entrypoint style / run-from-root |
| `/workspace/experiments/finetune_qwen_model_2026_08_08/data/chat_train.jsonl` | From Step 2 |
| TRL docs for assistant masking / `SFTConfig` (via Context7 or current TRL version in the extra) | Exact kwarg names for completion-only loss |

## Files allowed to change

- `/workspace/experiments/finetune_qwen_model_2026_08_08/train.py`
- `/workspace/experiments/finetune_qwen_model_2026_08_08/src/` helpers strictly for training (e.g. `src/train_config.py`) if needed
- `/workspace/experiments/finetune_qwen_model_2026_08_08/tests/` for config/seed/path tests
- `/workspace/experiments/finetune_qwen_model_2026_08_08/README.md` (train CLI docs only)
- `/workspace/pyproject.toml` only if a missing dep blocks TRL/PEFT (prefer fixing Step 1 group)

## Files forbidden to change

- `/workspace/shared/**`
- `/workspace/experiments/llm_prompt_engineering_*/**`
- `/workspace/experiments/predict_keep_remove_2026_07_01/**`
- `/workspace/experiments/finetune_qwen_model_2026_08_08/data/**` (do not regenerate as part of train)
- `/workspace/experiments/finetune_qwen_model_2026_08_08/inference.py` / `evaluate.py` / `launch_sagemaker.py` (except trivial import-safe touch — prefer untouched)

## Contracts to freeze

### Model / LoRA

| Name | Value |
|------|-------|
| `MODEL_ID` | `Qwen/Qwen3-4B-Instruct-2507` |
| Precision | bf16 weights; no 4-bit quant |
| `r` | `16` |
| `lora_alpha` | `32` |
| `lora_dropout` | `0.05` |
| `bias` | `none` |
| `task_type` | `CAUSAL_LM` |
| `target_modules` | `q_proj`, `k_proj`, `v_proj`, `o_proj`, `gate_proj`, `up_proj`, `down_proj` |

### Trainer

| Name | Value |
|------|-------|
| Epochs | `3` |
| Learning rate | `2e-4` |
| LR schedule | cosine |
| Warmup | ratio in 3–5% of steps |
| `per_device_train_batch_size` | `1` |
| `gradient_accumulation_steps` | `8` |
| `max_seq_length` | `2048` |
| Seed | `1` |
| Train file | chat_train only |
| Loss | assistant / completion tokens only (verify TRL setting explicitly in code comments + test that the flag is set) |
| Early stopping on test | **forbidden** |

### Auth / logging

- Missing `HF_TOKEN` → exit non-zero before download.
- Missing `WANDB_API_KEY` on real train → exit non-zero (dry-run may skip).
- W&B project name exactly `mirrorview-finetune-qwen-2026-08-08`.

### `--dry-run`

Validates paths, prints resolved config (model id, loRA, hyperparams, train path row count), does not download the full model if avoidable; must exit 0 when `chat_train.jsonl` exists.

## Exact commands

```bash
cd /workspace

# Requires Step 2 data:
test -f experiments/finetune_qwen_model_2026_08_08/data/chat_train.jsonl

PYTHONPATH=. uv run --extra finetune-qwen-2026-08-08 python \
  experiments/finetune_qwen_model_2026_08_08/train.py \
  --train-jsonl experiments/finetune_qwen_model_2026_08_08/data/chat_train.jsonl \
  --output-dir /tmp/qwen_lora_dry \
  --dry-run

# Optional local GPU smoke (not required for step gate if no GPU):
# PYTHONPATH=. uv run --extra finetune-qwen-2026-08-08 python \
#   experiments/finetune_qwen_model_2026_08_08/train.py \
#   --train-jsonl experiments/finetune_qwen_model_2026_08_08/data/chat_train.jsonl \
#   --output-dir /tmp/qwen_lora_out \
#   --max-steps 2
```

Unit tests (preferred):

```bash
PYTHONPATH=. uv run --extra finetune-qwen-2026-08-08 pytest \
  experiments/finetune_qwen_model_2026_08_08/tests/test_train_config.py -q
```

### Expected pass / fail

| Check | Pass | Fail |
|-------|------|------|
| Dry-run | exit 0; prints locked hyperparams | Crash / wrong defaults |
| HF_TOKEN | Real train path refuses empty token | Silent anonymous fail later |
| Data isolation | Trainer dataset built from chat_train only | chat_test included |
| LoRA config | Matches table | Divergent r/alpha/targets |
| Assistant loss | Explicit TRL completion/assistant masking enabled | Full-sequence loss only |
| W&B project | Exact project string | Wrong/missing project |

## Done when

1. `train.py` implements the locked training contract.
2. Dry-run + config tests pass.
3. No inference/eval/Docker work claimed done.
