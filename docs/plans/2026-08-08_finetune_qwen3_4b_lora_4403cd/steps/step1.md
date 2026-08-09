# Step 1: Align README and scaffold the experiment tree

## Goal

Rewrite `experiments/finetune_qwen_model_2026_08_08/README.md` to match the confirmed design, and scaffold the experiment package layout plus a dedicated optional dependency group so later steps can install TRL/PEFT/SageMaker without implementing train/infer yet.

Do **not** implement data freeze, training, inference, Docker, or SageMaker launch in this step.

## Caller / unit of work

**Main caller:** a human operator reading the README and syncing deps.

1. Update README so it is the single source of operational truth for this experiment.
2. Create empty/stub modules listed below (docstrings + `raise NotImplementedError` or empty package markers only).
3. Add `pyproject.toml` optional-dependencies group `finetune-qwen-2026-08-08` with the libraries later steps need.

**Out of scope:** writing `data/*`; implementing `train.py` / `inference.py` / `evaluate.py` / `launch_sagemaker.py` bodies; Dockerfile; live AWS/HF calls; editing shared transforms or prompt-engineering experiments.

## Files to inspect (read-only)

| Path | Why |
|------|-----|
| `/workspace/experiments/finetune_qwen_model_2026_08_08/README.md` | Current draft to replace |
| `/workspace/experiments/finetune_qwen_model_2026_08_08/IMPLEMENTATION_DETAILS.md` | Confirmed design dump to mirror in README |
| `/workspace/docs/plans/2026-08-08_finetune_qwen3_4b_lora_4403cd/plan.md` | Approved plan |
| `/workspace/pyproject.toml` | Optional-deps group shape (`modernbert-training`) |
| `/workspace/docs/runbooks/CODING_GUIDES.md` | Run-from-root / `PYTHONPATH=.` docstring rule |
| `/workspace/experiments/predict_keep_remove_2026_07_01/models/modernbert/README.md` | Precedent for SageMaker + W&B env docs |

## Files allowed to change

- `/workspace/experiments/finetune_qwen_model_2026_08_08/README.md`
- `/workspace/experiments/finetune_qwen_model_2026_08_08/IMPLEMENTATION_DETAILS.md` (optional: one-line pointer to README if kept; do not diverge)
- `/workspace/experiments/finetune_qwen_model_2026_08_08/__init__.py` (create empty)
- `/workspace/experiments/finetune_qwen_model_2026_08_08/src/__init__.py` (create empty)
- `/workspace/experiments/finetune_qwen_model_2026_08_08/src/prompt.py` (stub only)
- `/workspace/experiments/finetune_qwen_model_2026_08_08/src/create_chat_dataset.py` (stub only)
- `/workspace/experiments/finetune_qwen_model_2026_08_08/src/build_splits.py` (stub only)
- `/workspace/experiments/finetune_qwen_model_2026_08_08/train.py` (stub only)
- `/workspace/experiments/finetune_qwen_model_2026_08_08/inference.py` (stub only)
- `/workspace/experiments/finetune_qwen_model_2026_08_08/evaluate.py` (stub only)
- `/workspace/experiments/finetune_qwen_model_2026_08_08/launch_sagemaker.py` (stub only)
- `/workspace/experiments/finetune_qwen_model_2026_08_08/Dockerfile` (placeholder comment-only file OK, or defer create to Step 6 — prefer create empty stub with `# Step 6` note)
- `/workspace/pyproject.toml` (add optional-deps group only)

## Files forbidden to change

- `/workspace/shared/**`
- `/workspace/experiments/llm_prompt_engineering_2026_08_05/**`
- `/workspace/experiments/llm_prompt_engineering_v2_2026_08_05/**`
- `/workspace/experiments/predict_keep_remove_2026_07_01/**`
- `/workspace/docs/plans/**` (except if correcting this plan packet after review)
- Do not create `data/` artifacts yet
- Do not `git commit` unless the user asks

## Contracts to freeze

### README must state (exact facts)

| Topic | Value |
|-------|-------|
| Goal | Teachability prelim; exploratory; no numeric F1 bar |
| Model | `Qwen/Qwen3-4B-Instruct-2507` |
| Data source | `STUDY_PHASE_2_PART_2_KEEP_REMOVE_LABELS_UNANIMOUS_MIN3` via `shared/data/registry.py` |
| Balance | all 154 removes + 154 keeps; `seed=1` |
| Split | 80/20; both splits 1:1; `seed=1` |
| Local outputs | `data/train.csv`, `data/test.csv`, `data/chat_train.jsonl`, `data/chat_test.jsonl` |
| Prompt | Vendored rubric; closing asks for `keep`/`remove`; original=Post 1, mirror=Post 2 |
| Train stack | TRL `SFTTrainer` + PEFT LoRA; assistant-only loss; bf16 (not QLoRA) |
| LoRA | `r=16`, `alpha=32`, `dropout=0.05`, attn+MLP targets |
| Hyperparams | 3 epochs; lr `2e-4`; cosine + 3–5% warmup; batch 1 × grad accum 8; `max_seq_length=2048`; seed `1` |
| SageMaker | Custom Docker; modes `train` / `infer_baseline` / `infer_adapter`; `ml.g5.xlarge`; `us-east-2` |
| ECR | `mirrorview-finetune_qwen_model_2026_08_08` |
| S3 | bucket `mirrorview-experimental-artifacts`; prefix `mirrorview-finetune_qwen_model_2026_08_08/` with `data/`, `adapters/<run_id>/`, `preds/{baseline,fine_tuned}/` |
| Env | `HF_TOKEN` (required remote), `WANDB_API_KEY` via `EnvVarsContainer`, `SAGEMAKER_ROLE_ARN` for launch |
| Metrics | Local `evaluate.py` → `RESULTS.md`; positive class = remove |

README must **not** say “quantization (bf16)” or a single `chat_dataset.jsonl`.

### Optional dependency group

Add to `/workspace/pyproject.toml` under `[project.optional-dependencies]`:

Group name: `finetune-qwen-2026-08-08`

Must include at least: `torch`, `transformers`, `datasets`, `accelerate`, `peft`, `trl`, `scikit-learn`, `wandb`, `pyyaml`, `sagemaker` (`>=2.240.0,<3`), `boto3`, `pandas` (if not already sufficient from base — base already has pandas).

Do not remove or alter `modernbert-training`.

### Stub modules

Each Python stub docstring must include: `Run from root: PYTHONPATH=. uv run python ...` (per `CODING_GUIDES.md`). Bodies: `raise NotImplementedError` until later steps.

## Exact commands

```bash
cd /workspace

# After editing pyproject.toml:
uv sync --extra finetune-qwen-2026-08-08

# Stub imports resolve (expect NotImplementedError only if executed as main):
PYTHONPATH=. uv run --extra finetune-qwen-2026-08-08 python -c "
from pathlib import Path
root = Path('experiments/finetune_qwen_model_2026_08_08')
required = [
    root / 'README.md',
    root / 'train.py',
    root / 'inference.py',
    root / 'evaluate.py',
    root / 'launch_sagemaker.py',
    root / 'src' / 'prompt.py',
    root / 'src' / 'build_splits.py',
    root / 'src' / 'create_chat_dataset.py',
]
missing = [str(p) for p in required if not p.is_file()]
assert not missing, missing
text = (root / 'README.md').read_text(encoding='utf-8')
assert 'chat_train.jsonl' in text
assert 'chat_test.jsonl' in text
assert 'chat_dataset.jsonl' not in text
assert 'Qwen/Qwen3-4B-Instruct-2507' in text
assert 'ml.g5.xlarge' in text
assert 'quantization' not in text.lower() or 'bf16' in text
print('step1 scaffold OK')
"
```

### Expected pass / fail

| Check | Pass | Fail |
|-------|------|------|
| README | Matches contracts table; no `chat_dataset.jsonl` | Stale README facts |
| Tree | All listed stub files exist | Missing path |
| Deps | `uv sync --extra finetune-qwen-2026-08-08` exits 0 | Sync failure |
| Scope | No train/infer logic; stubs raise or are empty | Premature implementation |
| Forbidden trees | Unchanged | Diff under shared/ or other experiments |

## Done when

1. README matches the confirmed design.
2. Stub entrypoints and `src/` modules exist.
3. Optional-deps group is syncable.
4. No data artifacts, no SageMaker jobs, no Docker build required yet.
