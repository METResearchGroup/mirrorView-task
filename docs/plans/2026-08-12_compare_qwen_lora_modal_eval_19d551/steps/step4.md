# Step 4: Run remote inference and write RESULTS.md

## Goal

Sync existing baseline and modal prediction CSVs, submit the unanimous adapter SageMaker inference job against the modal chat splits, download the new arm, and write `experiments/compare_qwen_lora_modal_eval_2026_08_12/RESULTS.md` with the three-arm comparison tables.

## Caller / unit of work

Operator sequence from repo root with AWS credentials exported as standard keys:

```bash
export AWS_ACCESS_KEY_ID="$LAB_AWS_ACCESS_KEY_ID"
export AWS_SECRET_ACCESS_KEY="$LAB_AWS_ACCESS_KEY_SECRET"
export AWS_DEFAULT_REGION=us-east-2
export SAGEMAKER_ROLE_ARN=arn:aws:iam::517478598677:role/mirrorview-qwen-finetune-sm-exec

PYTHONPATH=. uv run --extra finetune-qwen-2026-08-08 python \
  experiments/compare_qwen_lora_modal_eval_2026_08_12/sync_existing_preds.py \
  --preds-dir experiments/compare_qwen_lora_modal_eval_2026_08_12/preds \
  --force

PYTHONPATH=. uv run --extra finetune-qwen-2026-08-08 python \
  experiments/compare_qwen_lora_modal_eval_2026_08_12/launch_sagemaker.py \
  --mode infer_unanimous_adapter \
  --wait

PYTHONPATH=. uv run --extra finetune-qwen-2026-08-08 python \
  experiments/compare_qwen_lora_modal_eval_2026_08_12/sync_existing_preds.py \
  --preds-dir experiments/compare_qwen_lora_modal_eval_2026_08_12/preds \
  --include-unanimous \
  --force

PYTHONPATH=. uv run --extra finetune-qwen-2026-08-08 python \
  experiments/compare_qwen_lora_modal_eval_2026_08_12/evaluate.py \
  --preds-dir experiments/compare_qwen_lora_modal_eval_2026_08_12/preds \
  --write-results experiments/compare_qwen_lora_modal_eval_2026_08_12/RESULTS.md
```

If `--include-unanimous` is awkward, a separate download helper or an optional flag on sync is fine. The required end state is six local CSVs and one RESULTS.md.

## Files to inspect (read-only)

| Path | Why |
|------|-----|
| `/workspace/experiments/larger_finetune_qwen_model_2026_08_08/RESULTS.md` | Known baseline and modal numbers to cross-check |
| `/workspace/experiments/compare_qwen_lora_modal_eval_2026_08_12/README.md` | Run record section to fill |

## Files allowed to change

- `/workspace/experiments/compare_qwen_lora_modal_eval_2026_08_12/RESULTS.md` (create)
- `/workspace/experiments/compare_qwen_lora_modal_eval_2026_08_12/preds/**` (local artifacts; may be gitignored or committed as small CSVs if the repo convention for this experiment prefers commit)
- `/workspace/experiments/compare_qwen_lora_modal_eval_2026_08_12/README.md` (fill Run record with job id and URIs)
- `/workspace/experiments/compare_qwen_lora_modal_eval_2026_08_12/sync_existing_preds.py` only if a unanimous download flag is still missing
- `/workspace/CHANGELOG.md`

## Files forbidden to change

- `/workspace/experiments/finetune_qwen_model_2026_08_08/RESULTS.md`
- `/workspace/experiments/larger_finetune_qwen_model_2026_08_08/RESULTS.md`
- `/workspace/shared/**`
- Do not retrain either adapter

## Contracts

### Cross-check

After sync, baseline and modal test metrics from the new RESULTS.md must match the larger experiment RESULTS.md within rounding to four decimals:

- baseline test F1 `0.7210`
- modal fine-tuned test F1 `0.6962`

### RESULTS.md content

Must state:

1. Shared eval set is the frozen modal balanced splits from `experiments/larger_finetune_qwen_model_2026_08_08/data/`.
2. Arms and their training sources (none / unanimous min-3 / modal labels).
3. Train and test tables with three rows each.
4. SageMaker job name for the unanimous infer run.

### Pred CSV commit policy

Prefer committing the six prediction CSVs if they are small enough for git (they should be, based on prior sizes under 300 KB each). If the team convention is to leave preds local only, keep them untracked and document the S3 URIs in the README Run record. Either way, RESULTS.md must be committed.

## Pass / fail

Pass:

```bash
test -f experiments/compare_qwen_lora_modal_eval_2026_08_12/RESULTS.md
grep -q 'unanimous_lora' experiments/compare_qwen_lora_modal_eval_2026_08_12/RESULTS.md
grep -q 'modal_lora' experiments/compare_qwen_lora_modal_eval_2026_08_12/RESULTS.md
grep -q '0.7210' experiments/compare_qwen_lora_modal_eval_2026_08_12/RESULTS.md
test -f experiments/compare_qwen_lora_modal_eval_2026_08_12/preds/unanimous_lora/test_labels.csv
```

Fail if RESULTS.md only has two arms, or if baseline test F1 does not match `0.7210`.

## Out of scope

Hyperparameter sweeps, prompt changes, retraining, evaluating on the unanimous min-3 CSV instead of the modal frozen splits.
