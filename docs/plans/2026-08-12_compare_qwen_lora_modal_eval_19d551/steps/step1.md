# Step 1: Scaffold the comparison experiment

## Goal

Create `experiments/compare_qwen_lora_modal_eval_2026_08_12/` with a README that locks the design facts, plus stub modules for sync, SageMaker launch, and three-arm evaluate. Reuse optional dependency group `finetune-qwen-2026-08-08`. Do not sync preds, submit SageMaker, or write RESULTS.md in this step.

## Caller / unit of work

The main caller is a person reading the new README.

1. Write the README so it is the place an operator looks for how this comparison works.
2. Create package markers and stub modules listed below.
3. Confirm `uv sync --extra finetune-qwen-2026-08-08` still installs.

## Files to inspect (read-only)

| Path | Why |
|------|-----|
| `/workspace/experiments/larger_finetune_qwen_model_2026_08_08/README.md` | Modal data contracts and S3 layout to reuse |
| `/workspace/experiments/finetune_qwen_model_2026_08_08/README.md` | Unanimous adapter run id and metric conventions |
| `/workspace/experiments/larger_finetune_qwen_model_2026_08_08/RESULTS.md` | Two-arm table shape to extend |
| `/workspace/shared/data/registry.py` | Registry name for modal labels |
| `/workspace/docs/plans/2026-08-12_compare_qwen_lora_modal_eval_19d551/plan.md` | Approved plan |
| `/workspace/pyproject.toml` | Existing optional group `finetune-qwen-2026-08-08` |

## Files allowed to change

- `/workspace/experiments/compare_qwen_lora_modal_eval_2026_08_12/README.md`
- `/workspace/experiments/compare_qwen_lora_modal_eval_2026_08_12/__init__.py`
- `/workspace/experiments/compare_qwen_lora_modal_eval_2026_08_12/evaluate.py` (stub only)
- `/workspace/experiments/compare_qwen_lora_modal_eval_2026_08_12/launch_sagemaker.py` (stub only)
- `/workspace/experiments/compare_qwen_lora_modal_eval_2026_08_12/sync_existing_preds.py` (stub only)
- `/workspace/CHANGELOG.md` (one bullet for this experiment)

## Files forbidden to change

- `/workspace/shared/**`
- `/workspace/experiments/finetune_qwen_model_2026_08_08/**`
- `/workspace/experiments/larger_finetune_qwen_model_2026_08_08/data/**`
- `/workspace/experiments/larger_finetune_qwen_model_2026_08_08/RESULTS.md`
- Do not create a second optional dependency group
- Do not add a new Dockerfile in this step

## Contracts to freeze

### README must state (exact facts)

| Topic | Value |
|-------|-------|
| Goal | Compare three keep/remove arms on one modal-label eval set |
| Arms | `baseline` (no LoRA), `unanimous_lora` (pull request 54 adapter `passrole_probe3`), `modal_lora` (pull request 57 adapter `modal_larger_1ep_2026_08_09`) |
| Model | `Qwen/Qwen3-4B-Instruct-2507` |
| Eval data source | `STUDY_PHASE_2_PART_2_KEEP_REMOVE_LABELS` via frozen files in `experiments/larger_finetune_qwen_model_2026_08_08/data/` |
| Eval rows | Same balanced 1:1 modal splits as the larger experiment: train 4500 / test 1126; seed 1 |
| No train | Do not retrain adapters |
| Pred layout | `preds/{baseline,unanimous_lora,modal_lora}/{train,test}_labels.csv` |
| Metrics | Accuracy, precision, recall, F1; positive class = remove |
| Remote image | Reuse ECR `mirrorview-larger_finetune_qwen_model_2026_08_08:latest` |
| Unanimous adapter S3 | `s3://mirrorview-experimental-artifacts/mirrorview-finetune_qwen_model_2026_08_08/adapters/passrole_probe3/` |
| Modal data S3 | `s3://mirrorview-experimental-artifacts/mirrorview-larger_finetune_qwen_model_2026_08_08/data/` |
| Existing preds S3 | `s3://mirrorview-experimental-artifacts/mirrorview-larger_finetune_qwen_model_2026_08_08/preds/{baseline,fine_tuned}/` |
| New preds S3 | `s3://mirrorview-experimental-artifacts/mirrorview-larger_finetune_qwen_model_2026_08_08/preds/unanimous_lora/` |
| Deps | `uv sync --extra finetune-qwen-2026-08-08` |

### Stub modules

Each stub must import or define a `main` that raises `NotImplementedError` with a one-line message naming the step that will fill it in, or print help text only. Prefer empty `main` that documents the intended CLI in the module docstring.

## Pass / fail

Pass:

```bash
test -f experiments/compare_qwen_lora_modal_eval_2026_08_12/README.md
grep -q 'unanimous_lora' experiments/compare_qwen_lora_modal_eval_2026_08_12/README.md
grep -q 'STUDY_PHASE_2_PART_2_KEEP_REMOVE_LABELS' experiments/compare_qwen_lora_modal_eval_2026_08_12/README.md
grep -q 'passrole_probe3' experiments/compare_qwen_lora_modal_eval_2026_08_12/README.md
uv sync --extra finetune-qwen-2026-08-08
```

Fail if the README invents a new train recipe, a new balanced split, or a new Docker image name.

## Out of scope

Implementing real evaluate or launch logic, downloading S3 objects, submitting SageMaker jobs, editing IAM Terraform.
