# Step 1: Scaffold the larger experiment as thin wrappers

## Goal

Create `experiments/larger_finetune_qwen_model_2026_08_08/` with a README that locks the design facts, and with a small package tree whose modules import from `experiments.finetune_qwen_model_2026_08_08` instead of copying implementations. Reuse the existing optional dependency group `finetune-qwen-2026-08-08`. Do not add a second optional group unless sync fails for a documented reason.

Do not freeze data, train a model, build Docker, or submit SageMaker jobs in this step.

## Caller / unit of work

The main caller is a person reading the new README and importing the package.

1. Write the README so it is the place an operator looks for how this experiment works.
2. Create the package markers and stub or wrapper modules listed below.
3. Confirm `uv sync --extra finetune-qwen-2026-08-08` still installs the train and infer stack used by both experiments.

Work that is out of scope includes writing `data/*`, implementing real train or infer bodies, writing the Dockerfile, making live AWS or Hugging Face calls, editing shared transforms, and rewriting the earlier experiment's README or RESULTS.

## Files to inspect (read-only)

| Path | Why |
|------|-----|
| `/workspace/experiments/finetune_qwen_model_2026_08_08/README.md` | Contracts to copy, except dataset, cloud names, and counts |
| `/workspace/experiments/finetune_qwen_model_2026_08_08/src/build_splits.py` | Import surface for balance and split helpers |
| `/workspace/experiments/finetune_qwen_model_2026_08_08/src/create_chat_dataset.py` | Import surface for chat helpers |
| `/workspace/experiments/finetune_qwen_model_2026_08_08/src/prompt.py` | Must be reused, not copied again |
| `/workspace/shared/data/registry.py` | `STUDY_PHASE_2_PART_2_KEEP_REMOVE_LABELS` |
| `/workspace/docs/plans/2026-08-09_finetune_qwen_modal_labels_5b07da/plan.md` | Approved plan |
| `/workspace/pyproject.toml` | Existing optional group `finetune-qwen-2026-08-08` |
| `/workspace/docs/runbooks/CODING_GUIDES.md` | Run-from-root and `PYTHONPATH=.` docstring rule |

## Files allowed to change

- `/workspace/experiments/larger_finetune_qwen_model_2026_08_08/README.md` (create)
- `/workspace/experiments/larger_finetune_qwen_model_2026_08_08/IMPLEMENTATION_DETAILS.md` (optional one-line pointer to the README or the earlier experiment)
- `/workspace/experiments/larger_finetune_qwen_model_2026_08_08/__init__.py`
- `/workspace/experiments/larger_finetune_qwen_model_2026_08_08/src/__init__.py`
- `/workspace/experiments/larger_finetune_qwen_model_2026_08_08/src/build_splits.py` (stub or wrapper shell only)
- `/workspace/experiments/larger_finetune_qwen_model_2026_08_08/src/create_chat_dataset.py` (stub or wrapper shell only)
- `/workspace/experiments/larger_finetune_qwen_model_2026_08_08/train.py` (stub or wrapper shell only)
- `/workspace/experiments/larger_finetune_qwen_model_2026_08_08/inference.py` (stub or wrapper shell only)
- `/workspace/experiments/larger_finetune_qwen_model_2026_08_08/evaluate.py` (stub or wrapper shell only)
- `/workspace/experiments/larger_finetune_qwen_model_2026_08_08/launch_sagemaker.py` (stub or wrapper shell only)
- `/workspace/experiments/larger_finetune_qwen_model_2026_08_08/Dockerfile` (placeholder is fine; the real image comes in Step 4)
- `/workspace/experiments/larger_finetune_qwen_model_2026_08_08/entrypoint.sh` (placeholder is fine)
- `/workspace/CHANGELOG.md` (one bullet noting the new experiment plan or scaffold if the repo convention requires it for this pull request slice)

## Files forbidden to change

- `/workspace/shared/**`
- `/workspace/experiments/finetune_qwen_model_2026_08_08/data/**`
- `/workspace/experiments/finetune_qwen_model_2026_08_08/RESULTS.md`
- `/workspace/experiments/llm_prompt_engineering_*/**`
- Do not create `data/` artifacts yet
- Do not duplicate `finetune-qwen-2026-08-08` into a second optional dependency group unless sync fails for a documented reason

## Contracts to freeze

### README must state (exact facts)

| Topic | Value |
|-------|-------|
| Goal | Early teachability check on modal keep/remove labels, with no numeric F1 success bar |
| Prior reference | Reuses `experiments/finetune_qwen_model_2026_08_08` (pull request 54) via imports |
| Model | `Qwen/Qwen3-4B-Instruct-2507` |
| Data source | `STUDY_PHASE_2_PART_2_KEEP_REMOVE_LABELS` via `shared/data/registry.py` |
| Balance | All removes plus an equal number of keeps, with `seed=1` (on current data, 2813 + 2813 = 5626) |
| Split | 80/20, both splits equal keep and remove, with `seed=1` (on current data, train 4500 and test 1126) |
| Local outputs | `data/train.csv`, `data/test.csv`, `data/chat_train.jsonl`, `data/chat_test.jsonl` |
| Prompt | Same vendored rubric as the earlier experiment (import it; do not copy the text again) |
| Train stack | TRL `SFTTrainer` plus PEFT LoRA, assistant-only loss, bf16 LoRA (not QLoRA) |
| LoRA | `r=16`, `alpha=32`, `dropout=0.05`, attention and MLP targets |
| Hyperparams | 1 epoch, learning rate `2e-4`, cosine schedule with 3% to 5% warmup, batch 1 with gradient accumulation 8, `max_seq_length=2048`, seed `1` |
| SageMaker | Custom Docker, modes `train`, `infer_baseline`, and `infer_adapter`, instance `ml.g5.xlarge`, region `us-east-2` |
| ECR | `mirrorview-larger_finetune_qwen_model_2026_08_08` |
| S3 | Bucket `mirrorview-experimental-artifacts`, prefix `mirrorview-larger_finetune_qwen_model_2026_08_08/` with `data/`, `adapters/<run_id>/`, and `preds/{baseline,fine_tuned}/` |
| W&B | Project `mirrorview-larger-finetune-qwen-2026-08-08` |
| Env | `HF_TOKEN` required on remote runs, `WANDB_API_KEY` via `EnvVarsContainer`, `SAGEMAKER_ROLE_ARN` for launch |
| Metrics | Local `evaluate.py` writes `RESULTS.md`, with remove as the positive class |
| Deps install | `uv sync --extra finetune-qwen-2026-08-08` |

The README must not claim the unanimous min-3 registry, the n=308 size, or the earlier S3 or ECR names as this experiment's own cloud names.

### DRY rule for stubs

Each new Python module docstring must include a run-from-root command under the new experiment path. Stub bodies may either raise `NotImplementedError` with a comment that names the later step that fills them, or already show the intended import from `experiments.finetune_qwen_model_2026_08_08` with a thin `main()` that is still incomplete.

Do not paste earlier function bodies into the new tree in this step.

## Exact commands

```bash
cd /workspace

uv sync --extra finetune-qwen-2026-08-08

PYTHONPATH=. uv run --extra finetune-qwen-2026-08-08 python -c "
from pathlib import Path
root = Path('experiments/larger_finetune_qwen_model_2026_08_08')
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
assert 'mirrorview-larger_finetune_qwen_model_2026_08_08' in text
assert 'Qwen/Qwen3-4B-Instruct-2507' in text
assert 'finetune-qwen-2026-08-08' in text
assert 'finetune_qwen_model_2026_08_08' in text  # prior import / reference
print('step1 scaffold OK')
"
```

### Expected pass / fail

| Check | Pass | Fail |
|-------|------|------|
| README | Names the modal registry, the new cloud names, and reuse of the earlier package | Uses unanimous facts or the earlier S3 or ECR names as this run's own names |
| Tree | All listed files exist | A required path is missing |
| Deps | Reuses `finetune-qwen-2026-08-08` and sync exits 0 | Adds a duplicate optional group without a documented reason |
| DRY | No copied TRL, PEFT, or evaluate bodies | A large paste from the earlier experiment |
| Forbidden | Earlier `data/`, `RESULTS.md`, and `shared/` stay untouched | A diff under those paths |

## Done when

1. The new experiment README matches the modal-label design facts above.
2. Stub or wrapper files exist under the new experiment path.
3. The optional dependency group from the earlier experiment remains the install path.
4. There are still no data artifacts and no remote jobs.
