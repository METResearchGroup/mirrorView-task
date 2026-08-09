# Step 8: Upload data, run remote jobs, produce RESULTS.md

## Goal

Execute the end-to-end remote teachability run: upload frozen local data to S3, ensure the ECR image from Step 6 is pushed, submit train then both inference jobs via the Step 7 launcher, sync prediction CSVs locally, and write `experiments/finetune_qwen_model_2026_08_08/RESULTS.md`.

**Hard gate:** do not start the paid `ml.g5.xlarge` train job until the user explicitly approves after confirming image push + data upload succeeded.

## Caller / unit of work

**Main caller:** operator checklist (commands below), not a new mega-script (thin `scripts` helpers allowed only if they wrap existing CLIs without new behavior).

Sequence:

1. Confirm Step 2 data files exist locally and match contracts.
2. Upload `experiments/finetune_qwen_model_2026_08_08/data/` → `s3://mirrorview-experimental-artifacts/mirrorview-finetune_qwen_model_2026_08_08/data/`.
3. Confirm ECR image `:latest` (or pinned tag) exists in `us-east-2`.
4. **STOP for user approval** to spend GPU.
5. Launch `--mode train --run-id <RUN_ID> --wait` (or poll until complete).
6. Launch `--mode infer_baseline --run-id <RUN_ID> --wait`.
7. Launch `--mode infer_adapter --run-id <RUN_ID> --wait`.
8. Sync `preds/` locally under `experiments/finetune_qwen_model_2026_08_08/preds/`.
9. Run `evaluate.py --write-results .../RESULTS.md`.
10. Commit only if user asks (preds/RESULTS may be large — prefer committing `RESULTS.md` + README notes; ask before adding large CSVs).

**Out of scope:** changing hyperparams; re-freezing data; redesigning prompts; local GPU train as substitute for the SageMaker acceptance path.

## Files to inspect (read-only)

| Path | Why |
|------|-----|
| `/workspace/experiments/finetune_qwen_model_2026_08_08/README.md` | Operator commands |
| `/workspace/experiments/finetune_qwen_model_2026_08_08/launch_sagemaker.py` | Launch interface |
| `/workspace/experiments/finetune_qwen_model_2026_08_08/evaluate.py` | RESULTS writer |
| `/workspace/AGENTS.md` | AWS cred notes (`LAB_*` vs profile) |

## Files allowed to change

- `/workspace/experiments/finetune_qwen_model_2026_08_08/preds/**` (synced artifacts)
- `/workspace/experiments/finetune_qwen_model_2026_08_08/RESULTS.md`
- `/workspace/experiments/finetune_qwen_model_2026_08_08/README.md` (record run_id / job names / S3 URIs)
- Optional small upload helper under the experiment if it only wraps `aws s3 sync`

## Files forbidden to change

- `/workspace/shared/**`
- Locked training hyperparams / prompt text (no “quick fixes” mid-run without plan revision)
- Other experiments’ trees

## Contracts to freeze

### Upload

```bash
aws s3 sync experiments/finetune_qwen_model_2026_08_08/data/ \
  s3://mirrorview-experimental-artifacts/mirrorview-finetune_qwen_model_2026_08_08/data/ \
  --region us-east-2
```

After sync, `aws s3 ls` must show all four filenames.

### Approval gate text (required)

Before train submit, stop and ask the user to approve GPU spend. Do not proceed on silence.

### Run ordering

`train` → `infer_baseline` → `infer_adapter` (adapter infer must see adapter objects on S3).

### RESULTS

Must exist at `experiments/finetune_qwen_model_2026_08_08/RESULTS.md` with train and test tables filled from the four pred CSVs (not placeholders).

## Exact commands

```bash
cd /workspace

# Creds (local profile OR cloud LAB_* export per AGENTS.md)
# export AWS_ACCESS_KEY_ID="$LAB_AWS_ACCESS_KEY_ID"
# export AWS_SECRET_ACCESS_KEY="$LAB_AWS_ACCESS_KEY_SECRET"

aws s3 sync experiments/finetune_qwen_model_2026_08_08/data/ \
  s3://mirrorview-experimental-artifacts/mirrorview-finetune_qwen_model_2026_08_08/data/ \
  --region us-east-2

aws s3 ls s3://mirrorview-experimental-artifacts/mirrorview-finetune_qwen_model_2026_08_08/data/ \
  --region us-east-2

# Verify ECR image present (account-specific URI)
aws ecr describe-images \
  --repository-name mirrorview-finetune_qwen_model_2026_08_08 \
  --region us-east-2

# >>> USER APPROVAL REQUIRED HERE <<<

RUN_ID=$(date -u +%Y_%m_%d-%H%M%S)

PYTHONPATH=. uv run --extra finetune-qwen-2026-08-08 python \
  experiments/finetune_qwen_model_2026_08_08/launch_sagemaker.py \
  --mode train --run-id "$RUN_ID" --wait

PYTHONPATH=. uv run --extra finetune-qwen-2026-08-08 python \
  experiments/finetune_qwen_model_2026_08_08/launch_sagemaker.py \
  --mode infer_baseline --run-id "$RUN_ID" --wait

PYTHONPATH=. uv run --extra finetune-qwen-2026-08-08 python \
  experiments/finetune_qwen_model_2026_08_08/launch_sagemaker.py \
  --mode infer_adapter --run-id "$RUN_ID" --wait

mkdir -p experiments/finetune_qwen_model_2026_08_08/preds
aws s3 sync \
  s3://mirrorview-experimental-artifacts/mirrorview-finetune_qwen_model_2026_08_08/preds/ \
  experiments/finetune_qwen_model_2026_08_08/preds/ \
  --region us-east-2

PYTHONPATH=. uv run --extra finetune-qwen-2026-08-08 python \
  experiments/finetune_qwen_model_2026_08_08/evaluate.py \
  --preds-dir experiments/finetune_qwen_model_2026_08_08/preds \
  --write-results experiments/finetune_qwen_model_2026_08_08/RESULTS.md

# Sanity: RESULTS has both sections and four numeric cells per table minimum
python -c "
from pathlib import Path
t = Path('experiments/finetune_qwen_model_2026_08_08/RESULTS.md').read_text(encoding='utf-8')
assert '## Train' in t and '## Test' in t
assert 'baseline' in t and 'fine-tuned' in t
print('RESULTS OK')
"
```

### Expected pass / fail

| Check | Pass | Fail |
|-------|------|------|
| Data on S3 | Four objects listed | Missing chat/csv |
| Approval | User explicitly approved before train | Train submitted without approval |
| Train job | Completed; adapter prefix non-empty | Failed/OOM without triage note |
| Infer jobs | Four pred CSVs on S3/local | Missing arm/split |
| RESULTS.md | Filled metrics tables | Empty placeholders |
| Design freeze | Hyperparams/prompt unchanged mid-run | Silent recipe drift |

## Done when

1. Remote train + both infer modes completed for one `run_id`.
2. Local `preds/` mirrors S3 preds for baseline and fine_tuned.
3. `RESULTS.md` written with real metrics.
4. README notes the `run_id` and artifact locations.
5. Plan packet “done” criteria in `plan.md` are satisfied.
