# Step 6: Upload data, run remote jobs, and write RESULTS.md

## Goal

Run the full remote teachability path for the larger modal-label experiment. Upload the frozen local data, make sure the ECR image is pushed, submit train and then both inference jobs, sync prediction CSVs, and write `experiments/larger_finetune_qwen_model_2026_08_08/RESULTS.md` with the same table shape as pull request 54.

Do not start the paid `ml.g5.xlarge` train job until the user explicitly approves after confirming that image push and data upload succeeded.

## Caller / unit of work

The caller is an operator following the checklist below. Prefer reusing earlier CLIs through the new wrappers. Do not invent a parallel mega-script.

Sequence:

1. Confirm Step 2 data files exist and match contracts.
2. Upload `experiments/larger_finetune_qwen_model_2026_08_08/data/` to `s3://mirrorview-experimental-artifacts/mirrorview-larger_finetune_qwen_model_2026_08_08/data/`.
3. Build, tag, and push the ECR image `mirrorview-larger_finetune_qwen_model_2026_08_08:latest` in `us-east-2`.
4. Confirm Step 5 IAM allow list is applied.
5. Stop for user approval to spend GPU time.
6. Launch `--mode train --run-id <RUN_ID> --wait`.
7. Launch `--mode infer_baseline --run-id <RUN_ID> --wait`.
8. Launch `--mode infer_adapter --run-id <RUN_ID> --wait`.
9. Sync preds locally under `experiments/larger_finetune_qwen_model_2026_08_08/preds/`.
10. Run `evaluate.py --write-results .../RESULTS.md`.
11. Record run_id, job names, and S3 URIs in the new README run record.

Work that is out of scope includes changing hyperparameters mid-run, re-freezing with a new seed, editing the unanimous experiment's RESULTS, and using a local GPU as a substitute for SageMaker acceptance.

## Files to inspect (read-only)

| Path | Why |
|------|-----|
| `/workspace/experiments/larger_finetune_qwen_model_2026_08_08/README.md` | Operator commands |
| `/workspace/experiments/larger_finetune_qwen_model_2026_08_08/launch_sagemaker.py` | Launch interface |
| `/workspace/experiments/larger_finetune_qwen_model_2026_08_08/evaluate.py` | RESULTS writer |
| `/workspace/experiments/finetune_qwen_model_2026_08_08/RESULTS.md` | Table shape to match |
| `/workspace/AGENTS.md` | `LAB_*` AWS credential export |

## Files allowed to change

- `/workspace/experiments/larger_finetune_qwen_model_2026_08_08/preds/**` (synced artifacts)
- `/workspace/experiments/larger_finetune_qwen_model_2026_08_08/RESULTS.md`
- `/workspace/experiments/larger_finetune_qwen_model_2026_08_08/README.md` (run record)
- `/workspace/CHANGELOG.md` (completion note)

## Files forbidden to change

- `/workspace/shared/**`
- `/workspace/experiments/finetune_qwen_model_2026_08_08/RESULTS.md`
- `/workspace/experiments/finetune_qwen_model_2026_08_08/data/**`
- Locked training hyperparameters and prompt text

## Contracts to freeze

### Upload

```bash
export AWS_ACCESS_KEY_ID="$LAB_AWS_ACCESS_KEY_ID"
export AWS_SECRET_ACCESS_KEY="$LAB_AWS_ACCESS_KEY_SECRET"
export AWS_DEFAULT_REGION=us-east-2

aws s3 sync experiments/larger_finetune_qwen_model_2026_08_08/data/ \
  s3://mirrorview-experimental-artifacts/mirrorview-larger_finetune_qwen_model_2026_08_08/data/ \
  --region us-east-2

aws s3 ls s3://mirrorview-experimental-artifacts/mirrorview-larger_finetune_qwen_model_2026_08_08/data/
# must show train.csv test.csv chat_train.jsonl chat_test.jsonl
```

### ECR push

Use the same login, tag, and push pattern as the earlier README, with repository name `mirrorview-larger_finetune_qwen_model_2026_08_08`.

### Launch

```bash
PYTHONPATH=. uv run --extra finetune-qwen-2026-08-08 python \
  experiments/larger_finetune_qwen_model_2026_08_08/launch_sagemaker.py \
  --mode train --run-id <RUN_ID> --wait

PYTHONPATH=. uv run --extra finetune-qwen-2026-08-08 python \
  experiments/larger_finetune_qwen_model_2026_08_08/launch_sagemaker.py \
  --mode infer_baseline --run-id <RUN_ID> --wait

PYTHONPATH=. uv run --extra finetune-qwen-2026-08-08 python \
  experiments/larger_finetune_qwen_model_2026_08_08/launch_sagemaker.py \
  --mode infer_adapter --run-id <RUN_ID> --wait
```

Required env vars are `SAGEMAKER_ROLE_ARN` and `HF_TOKEN`. `WANDB_API_KEY` is required for train.

### RESULTS.md

`RESULTS.md` must include train and test tables for baseline versus fine-tuned with accuracy, precision, recall, and F1, with remove as the positive class, plus invalid-parse counts. Match the structure of `/workspace/experiments/finetune_qwen_model_2026_08_08/RESULTS.md`.

### Cost and size note

The modal balanced set is about 18 times larger than the unanimous n=308 run (5626 versus 308). Expect longer train and infer wall time and higher GPU cost. Still use `ml.g5.xlarge` unless the user explicitly revises the instance type in a plan amendment.

## Exact commands (post-job evaluate)

```bash
aws s3 sync \
  s3://mirrorview-experimental-artifacts/mirrorview-larger_finetune_qwen_model_2026_08_08/preds/ \
  experiments/larger_finetune_qwen_model_2026_08_08/preds/ \
  --region us-east-2

PYTHONPATH=. uv run --extra finetune-qwen-2026-08-08 python \
  experiments/larger_finetune_qwen_model_2026_08_08/evaluate.py \
  --preds-dir experiments/larger_finetune_qwen_model_2026_08_08/preds \
  --write-results experiments/larger_finetune_qwen_model_2026_08_08/RESULTS.md
```

### Expected pass / fail

| Check | Pass | Fail |
|-------|------|------|
| Upload | Four data objects listed on the new prefix | Wrote to the unanimous prefix |
| Jobs | Train and both inference jobs Complete | Failed, wrong image, or PassRole error |
| RESULTS | Tables present, remove as positive | Missing arms or splits |
| Isolation | Earlier RESULTS and data untouched | Accidental edits to pull request 54 artifacts |

## Done when

1. Remote train and both inference jobs completed for a recorded `run_id`.
2. `RESULTS.md` exists under the larger experiment with the required tables.
3. The README run record lists job names and S3 and ECR URIs for this experiment only.
4. Unanimous experiment artifacts remain unchanged.
