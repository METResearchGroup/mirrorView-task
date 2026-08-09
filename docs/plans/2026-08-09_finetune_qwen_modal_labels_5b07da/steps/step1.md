# Step 1: Scaffold the modal-labels experiment as thin wrappers

## Goal

Create `experiments/finetune_qwen_model_modal_labels_2026_08_09/` with a design-frozen README and a thin package tree whose modules **import** from `experiments.finetune_qwen_model_2026_08_08` rather than copying implementations. Reuse the existing optional-deps group `finetune-qwen-2026-08-08` (do not add a duplicate extra unless a hard packaging conflict appears).

Do **not** freeze data, train, build Docker, or submit SageMaker jobs in this step.

## Caller / unit of work

**Main caller:** a human operator reading the new README and importing the package.

1. Write README as the operational source of truth for the modal-label variant.
2. Create package markers and stub/wrapper modules listed below.
3. Confirm `uv sync --extra finetune-qwen-2026-08-08` still installs the train/infer stack used by both experiments.

**Out of scope:** writing `data/*`; implementing real train/infer bodies; Dockerfile; live AWS/HF calls; editing shared transforms; rewriting the prior experiment’s README or RESULTS.

## Files to inspect (read-only)

| Path | Why |
|------|-----|
| `/workspace/experiments/finetune_qwen_model_2026_08_08/README.md` | Contracts to clone except dataset/identity/counts |
| `/workspace/experiments/finetune_qwen_model_2026_08_08/src/build_splits.py` | Import surface for balance/split helpers |
| `/workspace/experiments/finetune_qwen_model_2026_08_08/src/create_chat_dataset.py` | Import surface for chat helpers |
| `/workspace/experiments/finetune_qwen_model_2026_08_08/src/prompt.py` | Must be reused, not re-vendored |
| `/workspace/shared/data/registry.py` | `STUDY_PHASE_2_PART_2_KEEP_REMOVE_LABELS` |
| `/workspace/docs/plans/2026-08-09_finetune_qwen_modal_labels_5b07da/plan.md` | Approved plan |
| `/workspace/pyproject.toml` | Existing optional group `finetune-qwen-2026-08-08` |
| `/workspace/docs/runbooks/CODING_GUIDES.md` | Run-from-root / `PYTHONPATH=.` docstring rule |

## Files allowed to change

- `/workspace/experiments/finetune_qwen_model_modal_labels_2026_08_09/README.md` (create)
- `/workspace/experiments/finetune_qwen_model_modal_labels_2026_08_09/IMPLEMENTATION_DETAILS.md` (optional one-line pointer to README / prior experiment)
- `/workspace/experiments/finetune_qwen_model_modal_labels_2026_08_09/__init__.py`
- `/workspace/experiments/finetune_qwen_model_modal_labels_2026_08_09/src/__init__.py`
- `/workspace/experiments/finetune_qwen_model_modal_labels_2026_08_09/src/build_splits.py` (stub/wrapper shell only)
- `/workspace/experiments/finetune_qwen_model_modal_labels_2026_08_09/src/create_chat_dataset.py` (stub/wrapper shell only)
- `/workspace/experiments/finetune_qwen_model_modal_labels_2026_08_09/train.py` (stub/wrapper shell only)
- `/workspace/experiments/finetune_qwen_model_modal_labels_2026_08_09/inference.py` (stub/wrapper shell only)
- `/workspace/experiments/finetune_qwen_model_modal_labels_2026_08_09/evaluate.py` (stub/wrapper shell only)
- `/workspace/experiments/finetune_qwen_model_modal_labels_2026_08_09/launch_sagemaker.py` (stub/wrapper shell only)
- `/workspace/experiments/finetune_qwen_model_modal_labels_2026_08_09/Dockerfile` (placeholder OK; real image in Step 4)
- `/workspace/experiments/finetune_qwen_model_modal_labels_2026_08_09/entrypoint.sh` (placeholder OK)
- `/workspace/CHANGELOG.md` (one bullet noting the new experiment plan/scaffold if the repo convention requires it for this PR slice)

## Files forbidden to change

- `/workspace/shared/**`
- `/workspace/experiments/finetune_qwen_model_2026_08_08/data/**`
- `/workspace/experiments/finetune_qwen_model_2026_08_08/RESULTS.md`
- `/workspace/experiments/llm_prompt_engineering_*/**`
- Do not create `data/` artifacts yet
- Do not duplicate `finetune-qwen-2026-08-08` into a second optional-deps group unless sync fails for a documented reason

## Contracts to freeze

### README must state (exact facts)

| Topic | Value |
|-------|-------|
| Goal | Teachability prelim on **modal** keep/remove labels; exploratory; no numeric F1 bar |
| Prior reference | Reuses `experiments/finetune_qwen_model_2026_08_08` (PR #54) via imports |
| Model | `Qwen/Qwen3-4B-Instruct-2507` |
| Data source | `STUDY_PHASE_2_PART_2_KEEP_REMOVE_LABELS` via `shared/data/registry.py` |
| Balance | all removes + equal keeps; `seed=1` (current data: 2813 + 2813 = 5626) |
| Split | 80/20; both splits 1:1 keep/remove; `seed=1` (current: train 4500 / test 1126) |
| Local outputs | `data/train.csv`, `data/test.csv`, `data/chat_train.jsonl`, `data/chat_test.jsonl` |
| Prompt | Same vendored rubric as prior experiment (import; do not re-copy text) |
| Train stack | TRL `SFTTrainer` + PEFT LoRA; assistant-only loss; bf16 LoRA (not QLoRA) |
| LoRA | `r=16`, `alpha=32`, `dropout=0.05`, attn+MLP targets |
| Hyperparams | 3 epochs; lr `2e-4`; cosine + 3–5% warmup; batch 1 × grad accum 8; `max_seq_length=2048`; seed `1` |
| SageMaker | Custom Docker; modes `train` / `infer_baseline` / `infer_adapter`; `ml.g5.xlarge`; `us-east-2` |
| ECR | `mirrorview-finetune_qwen_model_modal_labels_2026_08_09` |
| S3 | bucket `mirrorview-experimental-artifacts`; prefix `mirrorview-finetune_qwen_model_modal_labels_2026_08_09/` with `data/`, `adapters/<run_id>/`, `preds/{baseline,fine_tuned}/` |
| W&B | project `mirrorview-finetune-qwen-modal-labels-2026-08-09` |
| Env | `HF_TOKEN` (required remote), `WANDB_API_KEY` via `EnvVarsContainer`, `SAGEMAKER_ROLE_ARN` for launch |
| Metrics | Local `evaluate.py` → `RESULTS.md`; positive class = remove |
| Deps install | `uv sync --extra finetune-qwen-2026-08-08` |

README must **not** claim the unanimous-min3 registry, n=308, or the prior S3/ECR names as this experiment’s identity.

### DRY rule for stubs

Each new Python module docstring must include a run-from-root command under the **new** experiment path. Stub bodies either:

- `raise NotImplementedError` with a comment naming the Step that fills them, **or**
- already show the intended import from `experiments.finetune_qwen_model_2026_08_08...` with a thin `main()` that is still incomplete.

Do not paste prior function bodies into the new tree in this step.

## Exact commands

```bash
cd /workspace

uv sync --extra finetune-qwen-2026-08-08

PYTHONPATH=. uv run --extra finetune-qwen-2026-08-08 python -c "
from pathlib import Path
root = Path('experiments/finetune_qwen_model_modal_labels_2026_08_09')
required = [
    root / 'README.md',
    root / 'train.py',
    root / 'inference.py',
    root / 'evaluate.py',
    root / 'launch_sagemaker.py',
    root / 'src' / 'build_splits.py',
    root / 'src' / 'create_chat_dataset.py',
]
missing = [str(p) for p in required if not p.is_file()]
assert not missing, missing
text = (root / 'README.md').read_text(encoding='utf-8')
assert 'STUDY_PHASE_2_PART_2_KEEP_REMOVE_LABELS' in text
assert 'UNANIMOUS_MIN3' not in text
assert 'chat_train.jsonl' in text and 'chat_test.jsonl' in text
assert 'mirrorview-finetune_qwen_model_modal_labels_2026_08_09' in text
assert 'Qwen/Qwen3-4B-Instruct-2507' in text
assert 'finetune-qwen-2026-08-08' in text
assert 'finetune_qwen_model_2026_08_08' in text  # prior import / reference
print('step1 scaffold OK')
"
```

### Expected pass / fail

| Check | Pass | Fail |
|-------|------|------|
| README | Modal registry + new identity + prior-reuse note | Unanimous facts or prior S3/ECR as this run’s identity |
| Tree | All listed files exist | Missing path |
| Deps | Reuses `finetune-qwen-2026-08-08`; sync exits 0 | New duplicate extra without justification |
| DRY | No copied TRL/PEFT/eval bodies | Large paste from prior experiment |
| Forbidden | Prior `data/` / `RESULTS.md` / `shared/` untouched | Diff under those paths |

## Done when

1. New experiment README matches the modal-label design freeze.
2. Stub/wrapper files exist under the new experiment path.
3. Optional-deps group from the prior experiment remains the install path.
4. No data artifacts and no remote jobs yet.
