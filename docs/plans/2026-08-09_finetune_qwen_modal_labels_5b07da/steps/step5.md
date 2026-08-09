# Step 5: Extend SageMaker IAM for the new S3 and ECR names

## Goal

Update IAM so the existing SageMaker execution role used by the Qwen LoRA experiments can read and write the new experiment S3 prefix and pull the new ECR repository, without recreating PassRole from scratch. Prefer extending `/workspace/experiments/finetune_qwen_model_2026_08_08/infra/main.tf`, or adding a small Terraform overlay under the new experiment that references the same role. Pick one approach and document it in the new README.

Do not run the paid train job in this step. Applying Terraform needs credentials that can write IAM. If apply is blocked in the agent environment, document the exact apply commands and stop for an operator to apply them.

## Caller / unit of work

The main caller is an operator who applies Terraform with IAM-write credentials, then checks that the launcher still resolves `SAGEMAKER_ROLE_ARN`.

```bash
# Example if extending the earlier infra module in place:
cd experiments/finetune_qwen_model_2026_08_08/infra
# after editing locals / policy statements for the new prefix + ECR
terraform plan
# apply only with explicit approval
```

Work that is out of scope includes changing instance type or region, opening S3 to the whole bucket, and remote train.

## Files to inspect (read-only)

| Path | Why |
|------|-----|
| `/workspace/experiments/finetune_qwen_model_2026_08_08/infra/main.tf` | Current role, S3 prefix condition, ECR repo allow list, and PassRole user policy |
| `/workspace/experiments/larger_finetune_qwen_model_2026_08_08/launch_sagemaker.py` | Expected ECR and S3 names from Step 4 |
| `/workspace/AGENTS.md` | Cloud Agent AWS credential notes |

## Files allowed to change

- `/workspace/experiments/finetune_qwen_model_2026_08_08/infra/main.tf` (preferred). Add the second prefix and ECR to the allow lists, and keep the existing unanimous prefix working.
- Or `/workspace/experiments/larger_finetune_qwen_model_2026_08_08/infra/main.tf` (create). Attach additional inline policy to the existing role `mirrorview-qwen-finetune-sm-exec`. Do not create a second competing PassRole user policy name that fights the first.
- `/workspace/experiments/larger_finetune_qwen_model_2026_08_08/README.md` (IAM and apply notes)
- `/workspace/CHANGELOG.md` (brief note)

## Files forbidden to change

- `/workspace/shared/**`
- Earlier experiment training code, data, and RESULTS
- Wide-open IAM such as `Resource: "*"` for S3 objects beyond the two experiment prefixes

## Contracts to freeze

### Names that must be allowed

| Resource | Value |
|----------|-------|
| Execution role name | `mirrorview-qwen-finetune-sm-exec` (reuse) |
| S3 bucket | `mirrorview-experimental-artifacts` |
| S3 prefixes | Both `mirrorview-finetune_qwen_model_2026_08_08` and `mirrorview-larger_finetune_qwen_model_2026_08_08` |
| ECR repos | Both `mirrorview-finetune_qwen_model_2026_08_08` and `mirrorview-larger_finetune_qwen_model_2026_08_08` |
| Launcher user | `mark_iam_credentials` PassRole to the same execution role (already present; do not break it) |

### Security

- Keep prefix-conditioned `s3:ListBucket` and object read and write limited to the listed prefixes.
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
terraform plan -no-color | tee /tmp/qwen_larger_iam_plan.txt

# Apply only with explicit approval:
# terraform apply -auto-approve

# Check that the role still resolves
aws iam get-role --role-name mirrorview-qwen-finetune-sm-exec --region us-east-2 \
  --query 'Role.Arn' --output text
```

### Expected pass / fail

| Check | Pass | Fail |
|-------|------|------|
| Plan | Shows additive allow for the new prefix and ECR, and keeps the old ones | Destroys the role or drops the unanimous prefix |
| Scope | Least-privilege prefixes only | Bucket-wide `*` object access |
| PassRole | Still limited to the execution role ARNs already intended | New unbounded PassRole |

## Done when

1. Terraform, or a documented overlay, includes the new S3 prefix and ECR repository.
2. Existing unanimous experiment IAM access remains intact in the plan.
3. The README tells the operator how to apply and which role ARN to export as `SAGEMAKER_ROLE_ARN`.
4. No training jobs are launched in this step.
