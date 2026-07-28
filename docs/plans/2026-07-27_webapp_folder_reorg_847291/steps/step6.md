# Step 6: Terraform plan only

## Goal

From the moved infra module, confirm Lambda source files resolve on disk and run `terraform plan`. Accept empty or zip-hash-only churn with identical source; fail hard on missing files or destroy/replace of bucket or API. Do not apply in this step.

## Caller / unit of work

**Main caller:**

```bash
cd /Users/mark/src/work/mirrorView-task/webapp/infra
terraform plan -input=false
```

**In scope:** On-disk path proof for archive inputs; `terraform init` if needed; `terraform plan` review.

**Out of scope:** `terraform apply` (Step 8 only); S3 website upload; changing study/Lambda business logic.

## Prep references

- [ROLLOUT_PLAN.md](../ROLLOUT_PLAN.md) § Phase 4
- Path fix from Step 3: `file("${path.module}/../lambdas/lambda-*.mjs")`

## Files to inspect

| Path | Why |
|------|-----|
| `webapp/infra/main.tf` | `file()` paths, resources |
| `webapp/lambdas/lambda-get-post-assignments.mjs` | Archive input |
| `webapp/lambdas/lambda-save-jspsych-data.mjs` | Archive input |
| `/tmp/webapp-reorg-tf.plan.txt` | Plan capture (created by this step) |

## Files allowed to change

- Terraform local init artifacts under `webapp/infra/` if `terraform init` creates `.terraform/` (already typically gitignored)
- Plan output file under `/tmp/` (not committed)
- **No** intentional edits to `main.tf` in this step unless plan proves Step 3 path strings wrong — then fix path only and re-plan

## Files forbidden to change

- Lambda `.mjs` business logic
- `webapp/public/config.js`
- AWS via apply
- Bucket / API Gateway resource definitions for “cleanup”

## Exact commands

```bash
cd /Users/mark/src/work/mirrorView-task/webapp/infra

# Always: confirm zip inputs resolve before plan
python3 - <<'PY'
from pathlib import Path
mod = Path(".").resolve()
for name in ("lambda-get-post-assignments.mjs", "lambda-save-jspsych-data.mjs"):
    p = mod / ".." / "lambdas" / name
    assert p.is_file(), p
    print("OK", p.resolve())
PY

rg -n 'file\("\$\{path\.module\}' main.tf
# Expect:
#   file("${path.module}/../lambdas/lambda-get-post-assignments.mjs")
#   file("${path.module}/../lambdas/lambda-save-jspsych-data.mjs")

terraform init -input=false   # if not already initialized; may need backend creds
terraform plan -input=false -no-color | tee /tmp/webapp-reorg-tf.plan.txt
```

### Plan inspection checklist

Read `/tmp/webapp-reorg-tf.plan.txt` (or plan stdout) and confirm:

1. **No** destroy/replace of `aws_s3_bucket.site` (or equivalent site bucket resource).
2. **No** replace of API Gateway REST API / stage that would change URLs.
3. No changes to route paths `/get-post-assignments`, `/save-jspsych-data`.
4. Lambda `source_code_hash` / zip rebuild: empty plan **or** hash/zip metadata only with identical source content — acceptable.
5. No surprise env var changes that alter study behavior (if present, treat as unrelated drift — stop and review separately from reorg).

## Pass / fail

### Pass (with credentials)

1. On-disk path proof printed `OK` for both lambdas.
2. `terraform plan` completes.
3. Plan is empty **or** limited to expected hash/zip metadata; no bucket/API destroy/replace.

### Pass (credentials/backend blocked)

1. On-disk path proof still passes.
2. Plan fails only with a clear credentials/backend auth message.
3. Document: “Step 6 plan blocked on credentials; archive paths proven on disk.”
4. Missing-file errors are **not** a credentials skip.

### Fail

| Symptom | Action |
|---------|--------|
| `Invalid value for "path" ... file does not exist` | Step 3 path wrong — fix `main.tf`; do not apply |
| Plan wants to replace API / bucket | **Stop**; do not apply; investigate state vs config |
| Plan updates Lambda env that changes study behavior | Unrelated drift — separate from reorg |
| `terraform apply` was run | Violates this step; treat as Step 8 without approval |

## Rollback

No apply → no cloud rollback. Fix paths locally; re-plan.

## Done when

Path-correct plan reviewed (or credentials-blocked with on-disk proof). Merge criteria do **not** require apply. Proceed to Step 7 docs. Step 8 remains optional and gated.
