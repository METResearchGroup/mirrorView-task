# Step 8: Optional gated apply

## Goal

Only after Steps 1–6 pass and a human explicitly approves: apply Terraform and smoke the live assignment endpoint. This step is **out of merge criteria**; treat it as a separate release gate with a named rollback owner.

## Caller / unit of work

**Main caller:** Human release owner after reviewing Step 6 plan.

**In scope:** Explicit approval checklist, `terraform apply`, curl smoke of live assignment URL.

**Out of scope:** Required for merge; implementing `testing/smoke_tests` for real; S3 full site re-upload unless separately approved.

## Prep references

- [ROLLOUT_PLAN.md](../ROLLOUT_PLAN.md) § Phase 5
- Live assignment URL (must match `webapp/public/config.js`):  
  `https://bgdxga8s91.execute-api.us-east-2.amazonaws.com/prod/get-post-assignments`

## Gate checklist (all must be true before apply)

- [ ] Steps 1–6 passed (Step 5 may be credentials-documented skip with path proof; Step 6 plan reviewed).
- [ ] Step 7 docs ideally already merged or in-flight — not required to apply, but preferred so operators are not confused.
- [ ] A named human acknowledges prod Lambda/API may refresh.
- [ ] Rollback owner named; pre-reorg SHA from Step 1 recorded.
- [ ] Step 6 plan does **not** show bucket/API destroy/replace.

If any box is unchecked: **stop**. Do not apply.

## Files to inspect

| Path | Why |
|------|-----|
| `/tmp/webapp-reorg-tf.plan.txt` | Last reviewed plan |
| `webapp/public/config.js` | URL equality for smoke |
| `webapp/infra/` | Apply working directory |
| `webapp/testing/smoke_tests/` | Stub only — do not treat as coverage |

## Files allowed to change

- Remote AWS resources via `terraform apply` (only after gate)
- Local Terraform state as managed by backend (expected)

## Files forbidden to change

- Local source rewrites “to make apply work” without re-running Steps 3–6
- S3 website object deletes under `data/`
- API URL changes in config.js

## Exact commands (gated)

```bash
cd /Users/mark/src/work/mirrorView-task/webapp/infra

# Re-read plan one more time
terraform plan -input=false -no-color | tee /tmp/webapp-reorg-tf.plan.before-apply.txt
# Human must confirm plan still matches reviewed Step 6 expectations

terraform apply -input=false   # ONLY after explicit human approval

# Smoke live assignment (same URL as config.js — must not change)
curl -sS -X POST \
  'https://bgdxga8s91.execute-api.us-east-2.amazonaws.com/prod/get-post-assignments' \
  -H 'content-type: application/json' \
  -d '{"prolificId":"TEST_SMOKE","partyGroup":"democrat","studyId":"mirrorview","studyIterationId":"mirrorview_scaled_2026_06_18"}' \
  | head -c 500; echo
```

### Smoke stub note

`webapp/testing/smoke_tests/` remains a stub (`LAMBDA_URL = ""`, `main` is `pass`). Do **not** treat pytest there as coverage. Prefer curl / browser against production URLs already in `config.js`.

A pure Terraform lambda apply does not require re-uploading static assets if `webapp/public/` bytes are unchanged.

## Pass / fail

### Pass

1. Apply succeeds.
2. Assignment endpoint returns expected JSON shape (non-empty assignment payload / success status as today’s API does).
3. `config.js` URLs still match the live API base.
4. No accidental S3 key layout change (no upload in this step unless separately approved).

### Fail / rollback

```bash
cd /Users/mark/src/work/mirrorView-task/webapp/infra
# Prefer: redeploy previous lambda zip from prior git revision via terraform
# Coordinate with tree layout (lambdas under webapp/lambdas/):
git checkout <pre-reorg-sha> -- ../lambdas/lambda-get-post-assignments.mjs ../lambdas/lambda-save-jspsych-data.mjs
terraform apply -input=false
# Or revert the merge commit and apply from known-good tree
```

If apply changed only packaging paths with identical source, rollback is usually unnecessary.

## Merge criteria reminder

This step is **not** required for “done” / merge. Steps 1–7 define mergeable completion per plan.md What "done" looks like.

## Done when

Either (a) human explicitly skips this step and documents “apply deferred,” or (b) gate checklist + apply + curl smoke all pass with named rollback owner.
