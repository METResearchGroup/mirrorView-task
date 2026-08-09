# Step 5: Extend SageMaker IAM for the new S3/ECR identity

## Goal

Update IAM so the existing SageMaker execution role used by the Qwen LoRA experiments can read/write the **new** experiment S3 prefix and pull the **new** ECR repository, without recreating PassRole plumbing from scratch. Prefer extending `/workspace/experiments/finetune_qwen_model_2026_08_08/infra/main.tf` **or** adding a small adjacent Terraform overlay under the new experiment that references the same role — pick one approach and document it in the new README.

Do **not** run the paid train job in this step. Applying Terraform requires credentials that can write IAM; if apply is blocked in-agent, document the exact apply commands and stop for operator apply.

## Caller / unit of work

**Main caller:** operator applying Terraform with IAM-write credentials, then verifying the launcher still resolves `SAGEMAKER_ROLE_ARN`.

```bash
# Example if extending the prior infra module in place:
cd experiments/finetune_qwen_model_2026_08_08/infra
# after editing locals / policy statements for the new prefix + ECR
terraform plan
# apply only with explicit approval
```

**Out of scope:** changing instance type/region; broadening S3 to the whole bucket; remote train.

## Files to inspect (read-only)

| Path | Why |
|------|-----|
| `/workspace/experiments/finetune_qwen_model_2026_08_08/infra/main.tf` | Current role, S3 prefix condition, ECR repo allow-list, PassRole user policy |
| `/workspace/experiments/larger_finetune_qwen_model_2026_08_08/launch_sagemaker.py` | Expected ECR/S3 names from Step 4 |
| `/workspace/AGENTS.md` | Cloud Agent AWS credential notes |

## Files allowed to change

- `/workspace/experiments/finetune_qwen_model_2026_08_08/infra/main.tf` (preferred: add second prefix + ECR to allow-lists; keep existing unanimous prefix working)
- **or** `/workspace/experiments/larger_finetune_qwen_model_2026_08_08/infra/main.tf` (create) that attaches additional inline policy to the existing role `mirrorview-qwen-finetune-sm-exec` — must not create a second competing PassRole user policy name that fights the first
- `/workspace/experiments/larger_finetune_qwen_model_2026_08_08/README.md` (IAM/apply notes)
- `/workspace/CHANGELOG.md` (brief note)

## Files forbidden to change

- `/workspace/shared/**`
- Prior experiment training code/data/RESULTS
- Wild-open IAM (`Resource: "*"` for S3 objects beyond the two experiment prefixes)

## Contracts to freeze

### Identities that must be allowed

| Resource | Value |
|----------|-------|
| Execution role name | `mirrorview-qwen-finetune-sm-exec` (reuse) |
| S3 bucket | `mirrorview-experimental-artifacts` |
| S3 prefixes | **both** `mirrorview-finetune_qwen_model_2026_08_08` and `mirrorview-larger_finetune_qwen_model_2026_08_08` |
| ECR repos | **both** `mirrorview-finetune_qwen_model_2026_08_08` and `mirrorview-larger_finetune_qwen_model_2026_08_08` |
| Launcher user | `mark_iam_credentials` PassRole to the same execution role (already present; do not break it) |

### Security

- Keep prefix-conditioned `s3:ListBucket` / object read-write limited to the listed prefixes.
- Do not grant `iam:PassRole` on `*`.
- Do not disable ECR auth or make repositories public.

## Exact commands

```bash
cd /workspace

# After Terraform edit, from the chosen infra directory:
export AWS_ACCESS_KEY_ID="$LAB_AWS_ACCESS_KEY_ID"
export AWS_SECRET_ACCESS_KEY="$LAB_AWS_ACCESS_KEY_SECRET"
export AWS_DEFAULT_REGION=us-east-2
# unset AWS_SESSION_TOKEN if a stale session token breaks IAM user calls

terraform init
terraform plan -no-color | tee /tmp/qwen_modal_iam_plan.txt

# Apply only with explicit approval:
# terraform apply -auto-approve

# Sanity: role still resolvable
aws iam get-role --role-name mirrorview-qwen-finetune-sm-exec --region us-east-2 \
  --query 'Role.Arn' --output text
```

### Expected pass / fail

| Check | Pass | Fail |
|-------|------|------|
| Plan | Shows additive allow for new prefix/ECR; keeps old | Destroys role or drops unanimous prefix |
| Scope | Least-privilege prefixes only | Bucket-wide `*` object access |
| PassRole | Still limited to the execution role ARN(s) already intended | New unbounded PassRole |

## Done when

1. Terraform (or documented overlay) includes the new S3 prefix and ECR repo.
2. Existing unanimous experiment IAM access remains intact in the plan.
3. README tells the operator how to apply and which role ARN to export as `SAGEMAKER_ROLE_ARN`.
4. No training jobs launched in this step.
