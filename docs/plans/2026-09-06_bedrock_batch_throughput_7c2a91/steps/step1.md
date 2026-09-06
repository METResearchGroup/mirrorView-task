# Step 1: Confirm the Bedrock path in this account

Record whether Nova Micro Converse works with the environment AWS credentials, and whether native Bedrock batch jobs can be submitted without creating an IAM service role.

## Caller / unit of work

**Main caller:** `/workspace/experiments/bedrock_batch_parallelization_2026_09_06/write_findings.py` `main()`.

**Slice:** export standard AWS env vars from the lab credentials → one Nova Micro Converse call → list batch jobs → one expected-to-fail `CreateModelInvocationJob` probe → write `FINDINGS.md`.

**Out of scope:** creating or deleting IAM roles, the Bedrock engine, the 100-post smoke, pytest (this folder is experimental code).

## Files to inspect (read-only)

| Path | Why |
|------|-----|
| `/workspace/lib/constants.py` | `BEDROCK_REGION` is `us-east-2` |
| `/workspace/AGENTS.md` | Export `LAB_AWS_ACCESS_KEY_ID` as `AWS_ACCESS_KEY_ID` |
| `/workspace/data_platform/generate_features/OPENAI_BATCH_SMOKE_RESULTS.md` | OpenAI token rates for comparison |
| `/workspace/docs/plans/2026-09-06_bedrock_batch_throughput_7c2a91/plan.md` | Approved decisions |

## Files allowed to change

- `/workspace/experiments/bedrock_batch_parallelization_2026_09_06/write_findings.py` (create)
- `/workspace/experiments/bedrock_batch_parallelization_2026_09_06/FINDINGS.md` (create from the live run)
- `/workspace/lib/constants.py` (add `DEFAULT_BEDROCK_NOVA_MICRO = "us.amazon.nova-micro-v1:0"` only)

## Files forbidden to change

- `/workspace/data_platform/generate_features/engines/openai_engine.py`
- `/workspace/data_platform/generate_features/registry.py`
- Any IAM role in AWS. Do not call `iam.CreateRole`, `iam.PutRolePolicy`, `iam.AttachRolePolicy`, or `iam.DeleteRole`.

## Contracts to lock

```text
MODEL_ID = "us.amazon.nova-micro-v1:0"
REGION = BEDROCK_REGION  # us-east-2
ON_DEMAND_INPUT_USD_PER_MILLION = 0.035
ON_DEMAND_OUTPUT_USD_PER_MILLION = 0.14
BATCH_INPUT_USD_PER_MILLION = 0.0175
BATCH_OUTPUT_USD_PER_MILLION = 0.07
PROBE_USER_TEXT = "The Federal Reserve raised interest rates by 25 basis points today."
MAX_TOKENS = 16
TEMPERATURE = 0.0
FINDINGS_PATH = experiments/bedrock_batch_parallelization_2026_09_06/FINDINGS.md
```

`write_findings.py` must:

1. Set `AWS_ACCESS_KEY_ID` from `LAB_AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY` from `LAB_AWS_ACCESS_KEY_SECRET` when those lab names are present and the standard names are empty.
2. Call `bedrock-runtime.converse` in `us-east-2` with `MODEL_ID`, `PROBE_USER_TEXT`, `MAX_TOKENS`, and `TEMPERATURE`.
3. Call `bedrock.list_model_invocation_jobs(maxResults=1)`.
4. Call `bedrock.create_model_invocation_job` with a non-existent role ARN. Expect `AccessDeniedException` mentioning `iam:PassRole`. Do not retry with a real role.
5. Write `FINDINGS.md` with:
   - Model id and region
   - Converse result text and token usage
   - On-demand and batch Ohio prices
   - The batch-job error code and message
   - The sentence "No IAM service role was created."
6. Exit 0 when Converse succeeded, even if the batch probe failed as expected.

## Pass / fail

Must pass:

```bash
export AWS_ACCESS_KEY_ID="$LAB_AWS_ACCESS_KEY_ID"
export AWS_SECRET_ACCESS_KEY="$LAB_AWS_ACCESS_KEY_SECRET"
PYTHONPATH=. uv run python experiments/bedrock_batch_parallelization_2026_09_06/write_findings.py
```

Expected: exit 0. `FINDINGS.md` exists. Converse classified the probe sentence. The file records that batch job creation failed with `iam:PassRole`. No new IAM role exists because of this script.

Must fail the step if:

- Converse fails.
- The script creates or updates an IAM role.
- `FINDINGS.md` claims batch jobs work in this account.

## Commands with expected output

```bash
PYTHONPATH=. uv run python experiments/bedrock_batch_parallelization_2026_09_06/write_findings.py
```

Stdout includes `Wrote experiments/bedrock_batch_parallelization_2026_09_06/FINDINGS.md`. Exit code 0.
