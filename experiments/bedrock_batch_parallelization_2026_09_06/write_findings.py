"""Record whether Nova Micro Converse and Bedrock batch jobs work in this account.

Run from the repository root:

    PYTHONPATH=. uv run python \\
        experiments/bedrock_batch_parallelization_2026_09_06/write_findings.py
"""

from __future__ import annotations

import json
import os
from typing import Any

import boto3
from botocore.exceptions import ClientError

from lib.constants import BEDROCK_REGION, DEFAULT_BEDROCK_NOVA_MICRO, REPO_ROOT

MODEL_ID = DEFAULT_BEDROCK_NOVA_MICRO
ON_DEMAND_INPUT_USD_PER_MILLION = 0.035
ON_DEMAND_OUTPUT_USD_PER_MILLION = 0.14
BATCH_INPUT_USD_PER_MILLION = 0.0175
BATCH_OUTPUT_USD_PER_MILLION = 0.07
PROBE_USER_TEXT = (
    "The Federal Reserve raised interest rates by 25 basis points today."
)
PROBE_SYSTEM_TEXT = (
    "Classify the text as news, opinion, or neither. Reply with one word."
)
MAX_TOKENS = 16
TEMPERATURE = 0.0
LIST_JOBS_MAX_RESULTS = 1
MISSING_ROLE_ARN = "arn:aws:iam::517478598677:role/does-not-exist"
PROBE_JOB_NAME = "nova-micro-passrole-probe"
PROBE_INPUT_S3_URI = (
    "s3://mirrorview-experimental-artifacts/bedrock-batch-probe/input.jsonl"
)
PROBE_OUTPUT_S3_URI = (
    "s3://mirrorview-experimental-artifacts/bedrock-batch-probe/output/"
)
FINDINGS_PATH = (
    REPO_ROOT
    / "experiments"
    / "bedrock_batch_parallelization_2026_09_06"
    / "FINDINGS.md"
)
WROTE_PREFIX = "Wrote "


def apply_lab_aws_credentials() -> None:
    """Copy lab AWS keys onto the standard boto3 names when those names are empty."""
    if not os.environ.get("AWS_ACCESS_KEY_ID"):
        lab_access = os.environ.get("LAB_AWS_ACCESS_KEY_ID", "")
        if lab_access:
            os.environ["AWS_ACCESS_KEY_ID"] = lab_access
    if not os.environ.get("AWS_SECRET_ACCESS_KEY"):
        lab_secret = os.environ.get("LAB_AWS_ACCESS_KEY_SECRET", "")
        if lab_secret:
            os.environ["AWS_SECRET_ACCESS_KEY"] = lab_secret


def converse_probe(runtime: Any) -> dict[str, Any]:
    """Return text and token usage from one Nova Micro Converse call."""
    response = runtime.converse(
        modelId=MODEL_ID,
        system=[{"text": PROBE_SYSTEM_TEXT}],
        messages=[
            {"role": "user", "content": [{"text": PROBE_USER_TEXT}]},
        ],
        inferenceConfig={"maxTokens": MAX_TOKENS, "temperature": TEMPERATURE},
    )
    text = response["output"]["message"]["content"][0]["text"]
    usage = response.get("usage", {})
    return {
        "text": text,
        "input_tokens": int(usage.get("inputTokens", 0)),
        "output_tokens": int(usage.get("outputTokens", 0)),
        "stop_reason": response.get("stopReason", ""),
    }


def list_jobs_probe(control: Any) -> dict[str, Any]:
    """Return whether listing Bedrock batch jobs succeeded."""
    response = control.list_model_invocation_jobs(maxResults=LIST_JOBS_MAX_RESULTS)
    jobs = response.get("invocationJobSummaries", [])
    return {"ok": True, "listed_job_count": len(jobs)}


def create_job_probe(control: Any) -> dict[str, Any]:
    """Return the expected PassRole denial from CreateModelInvocationJob."""
    try:
        control.create_model_invocation_job(
            jobName=PROBE_JOB_NAME,
            modelId=MODEL_ID,
            roleArn=MISSING_ROLE_ARN,
            inputDataConfig={"s3InputDataConfig": {"s3Uri": PROBE_INPUT_S3_URI}},
            outputDataConfig={"s3OutputDataConfig": {"s3Uri": PROBE_OUTPUT_S3_URI}},
        )
    except ClientError as error:
        details = error.response.get("Error", {})
        return {
            "ok": False,
            "code": str(details.get("Code", "")),
            "message": str(details.get("Message", "")),
        }
    return {"ok": True, "code": "", "message": "unexpected success"}


def render_findings(
    converse: dict[str, Any],
    list_jobs: dict[str, Any],
    create_job: dict[str, Any],
) -> str:
    """Return FINDINGS.md text for the live probes."""
    return (
        "# Bedrock path findings\n\n"
        f"The model is `{MODEL_ID}`.\n\n"
        f"The region is `{BEDROCK_REGION}`.\n\n"
        "Credentials are the environment AWS keys. Copy `LAB_AWS_ACCESS_KEY_ID` "
        "onto `AWS_ACCESS_KEY_ID` when needed, and copy "
        "`LAB_AWS_ACCESS_KEY_SECRET` onto `AWS_SECRET_ACCESS_KEY` the same way.\n\n"
        "No IAM service role was created.\n\n"
        "## Converse\n\n"
        f'The probe text is "{PROBE_USER_TEXT}"\n\n'
        f'The model text is "{converse["text"]}".\n\n'
        f"The input token count is {converse['input_tokens']}.\n\n"
        f"The output token count is {converse['output_tokens']}.\n\n"
        f"The stop reason is {converse['stop_reason']}.\n\n"
        "## Prices (US East Ohio, AWS Price List 2026-09-01)\n\n"
        "- On-demand prices are "
        f"${ON_DEMAND_INPUT_USD_PER_MILLION} per million input tokens, "
        f"and ${ON_DEMAND_OUTPUT_USD_PER_MILLION} per million output tokens.\n"
        "- Batch prices are "
        f"${BATCH_INPUT_USD_PER_MILLION} per million input tokens, "
        f"and ${BATCH_OUTPUT_USD_PER_MILLION} per million output tokens.\n\n"
        "## Native batch jobs\n\n"
        f"Listing jobs succeeded, and the listed job count was "
        f"{list_jobs['listed_job_count']}.\n\n"
        "CreateModelInvocationJob failed when the role ARN was missing, "
        "which is the outcome we expected.\n\n"
        f"Error code: `{create_job['code']}`\n\n"
        f"Error message: {create_job['message']}\n\n"
        "The labeling in this experiment uses Converse on-demand. Native batch "
        "jobs need the `iam:PassRole` permission and a Bedrock service role. "
        "This work must not create that role.\n"
    )


def main() -> None:
    """Run the probes and write FINDINGS.md."""
    apply_lab_aws_credentials()
    runtime = boto3.client("bedrock-runtime", region_name=BEDROCK_REGION)
    control = boto3.client("bedrock", region_name=BEDROCK_REGION)
    converse = converse_probe(runtime)
    list_jobs = list_jobs_probe(control)
    create_job = create_job_probe(control)
    if create_job["ok"]:
        raise RuntimeError("CreateModelInvocationJob unexpectedly succeeded")
    FINDINGS_PATH.write_text(
        render_findings(converse, list_jobs, create_job),
        encoding="utf-8",
    )
    print(f"{WROTE_PREFIX}{FINDINGS_PATH.relative_to(REPO_ROOT)}")
    print(json.dumps({"converse": converse, "create_job_code": create_job["code"]}))


if __name__ == "__main__":
    main()
