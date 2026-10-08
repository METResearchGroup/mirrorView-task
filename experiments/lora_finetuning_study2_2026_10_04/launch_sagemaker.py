"""Launch Study 2 vLLM LoRA eval on SageMaker (smoke or full).

Run from repo root::

    source /tmp/aws-lab-env.sh
    export AWS_SDK_UA_APP_ID=AWSSkill-SageMaker
    PYTHONPATH=. uv run python \\
      experiments/lora_finetuning_study2_2026_10_04/launch_sagemaker.py \\
      --wait
"""

from __future__ import annotations

import argparse
import os
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

import boto3

AWS_REGION = "us-east-2"
ACCOUNT_ID = "517478598677"
ECR_REPO_NAME = "mirrorview-finetune_qwen_model_2026_08_08"
IMAGE_TAG = "study2-vllm-eval"
IMAGE_URI = (
    f"{ACCOUNT_ID}.dkr.ecr.{AWS_REGION}.amazonaws.com/"
    f"{ECR_REPO_NAME}:{IMAGE_TAG}"
)
EXECUTION_ROLE_ARN = (
    "arn:aws:iam::517478598677:role/mirrorview-qwen-finetune-sm-exec"
)
S3_BUCKET = "mirrorview-experimental-artifacts"
S3_OUTPUT_PREFIX = f"{ECR_REPO_NAME}/study2-vllm-eval-output"
INSTANCE_TYPE_DEFAULT = "ml.g5.xlarge"
VOLUME_SIZE_GB = 120
MAX_RUNTIME_SECONDS = 7200
# Smoke extrapolated the 20,000-row pass at 1.24 hours, plus model load.
# Four hours leaves margin without leaving a stuck job running all day.
FULL_MAX_RUNTIME_SECONDS = 14400
CONTAINER_ENTRY_POINT = ["python3"]
DEFAULT_ABLATION = "unanimous"
DEFAULT_RUN_NAME = "Qwen3.5-4B_lora_unanimous_2026_10_04-20:48:14"
DEFAULT_LIMIT = 32
BASE_JOB_NAME = "study2-vllm-eval-smoke"


@dataclass(frozen=True)
class EvalJobConfig:
    """Resolved SageMaker eval job (for dry-run and unit tests)."""

    region: str
    instance_type: str
    image_uri: str
    role_arn: str
    output_s3_uri: str
    environment: dict[str, str]
    container_entry_point: list[str]
    container_arguments: list[str]
    volume_size_gb: int
    max_runtime_seconds: int
    enable_network_isolation: bool
    job_name_prefix: str


def _job_suffix() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")


def _training_job_name(suffix: str | None = None, prefix: str = BASE_JOB_NAME) -> str:
    tail = (suffix or _job_suffix()).replace(":", "-").replace("_", "-")
    name = f"{prefix}-{tail}"
    return name[:63].rstrip("-")


def _require_env(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise ValueError(f"{name} is required but missing or empty.")
    return value


def _lab_aws_environment() -> dict[str, str]:
    """Keys for boto3 inside the container (outrank the execution role)."""
    access = os.environ.get("AWS_ACCESS_KEY_ID", "").strip()
    secret = os.environ.get("AWS_SECRET_ACCESS_KEY", "").strip()
    if not access:
        access = os.environ.get("LAB_AWS_ACCESS_KEY_ID", "").strip()
    if not secret:
        secret = os.environ.get("LAB_AWS_ACCESS_KEY_SECRET", "").strip()
    if not access or not secret:
        raise ValueError(
            "AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY (or LAB_* equivalents) "
            "are required."
        )
    env: dict[str, str] = {
        "AWS_ACCESS_KEY_ID": access,
        "AWS_SECRET_ACCESS_KEY": secret,
        "AWS_DEFAULT_REGION": AWS_REGION,
        "PYTHONPATH": "/app",
        "HF_TOKEN": _require_env("HF_TOKEN"),
    }
    return env


def build_eval_container_arguments(
    ablation: str = DEFAULT_ABLATION,
    run_name: str = DEFAULT_RUN_NAME,
    limit: int | None = DEFAULT_LIMIT,
) -> list[str]:
    """CLI args passed to evaluate.py inside the container."""
    args = [
        "experiments/lora_finetuning_study2_2026_10_04/evaluate.py",
        "--ablation",
        ablation,
        "--run-name",
        run_name,
        "--in-job",
    ]
    if limit is not None:
        args.extend(["--limit", str(limit)])
    return args


def build_job_config(
    *,
    image_uri: str = IMAGE_URI,
    role_arn: str = EXECUTION_ROLE_ARN,
    region: str = AWS_REGION,
    instance_type: str = INSTANCE_TYPE_DEFAULT,
    ablation: str = DEFAULT_ABLATION,
    run_name: str = DEFAULT_RUN_NAME,
    limit: int | None = DEFAULT_LIMIT,
    output_s3_uri: str | None = None,
    environment: dict[str, str] | None = None,
    max_runtime_seconds: int = MAX_RUNTIME_SECONDS,
    job_name_prefix: str = BASE_JOB_NAME,
) -> EvalJobConfig:
    """Construct job config without calling AWS."""
    out = output_s3_uri or f"s3://{S3_BUCKET}/{S3_OUTPUT_PREFIX}"
    env = dict(environment if environment is not None else _lab_aws_environment())
    return EvalJobConfig(
        region=region,
        instance_type=instance_type,
        image_uri=image_uri,
        role_arn=role_arn,
        output_s3_uri=out,
        environment=env,
        container_entry_point=list(CONTAINER_ENTRY_POINT),
        container_arguments=build_eval_container_arguments(
            ablation=ablation,
            run_name=run_name,
            limit=limit,
        ),
        volume_size_gb=VOLUME_SIZE_GB,
        max_runtime_seconds=max_runtime_seconds,
        enable_network_isolation=False,
        job_name_prefix=job_name_prefix,
    )


def build_create_training_job_request(
    config: EvalJobConfig,
    training_job_name: str,
) -> dict[str, Any]:
    """Build kwargs for SageMaker CreateTrainingJob."""
    return {
        "TrainingJobName": training_job_name,
        "RoleArn": config.role_arn,
        "AlgorithmSpecification": {
            "TrainingImage": config.image_uri,
            "TrainingInputMode": "File",
            "ContainerEntrypoint": config.container_entry_point,
            "ContainerArguments": config.container_arguments,
        },
        "OutputDataConfig": {"S3OutputPath": config.output_s3_uri},
        "ResourceConfig": {
            "InstanceType": config.instance_type,
            "InstanceCount": 1,
            "VolumeSizeInGB": config.volume_size_gb,
        },
        "StoppingCondition": {"MaxRuntimeInSeconds": config.max_runtime_seconds},
        "Environment": config.environment,
        "EnableNetworkIsolation": config.enable_network_isolation,
    }


def _ensure_sdk_app_id() -> None:
    os.environ.setdefault("AWS_SDK_UA_APP_ID", "AWSSkill-SageMaker")


def submit_job(
    config: EvalJobConfig,
    training_job_name: str | None = None,
) -> str:
    """Create the SageMaker training job and return its name."""
    _ensure_sdk_app_id()
    name = training_job_name or _training_job_name()
    client = boto3.client("sagemaker", region_name=config.region)
    request = build_create_training_job_request(config, name)
    client.create_training_job(**request)
    return name


def wait_for_job(
    job_name: str,
    region: str = AWS_REGION,
    poll_seconds: int = 60,
) -> str:
    """Block until the job completes or fails; return final status."""
    _ensure_sdk_app_id()
    client = boto3.client("sagemaker", region_name=region)
    terminal = {"Completed", "Failed", "Stopped", "Stopping"}
    while True:
        desc = client.describe_training_job(TrainingJobName=job_name)
        status = desc["TrainingJobStatus"]
        if status in terminal:
            return status
        time.sleep(poll_seconds)


def print_job_config(config: EvalJobConfig, job_name: str | None = None) -> None:
    print("SageMaker eval job config:")
    if job_name:
        print(f"  training_job_name: {job_name}")
    print(f"  region: {config.region}")
    print(f"  instance_type: {config.instance_type}")
    print(f"  image_uri: {config.image_uri}")
    print(f"  role_arn: {config.role_arn}")
    print(f"  output_s3_uri: {config.output_s3_uri}")
    print(f"  container_entry_point: {config.container_entry_point}")
    print(f"  container_arguments: {config.container_arguments}")
    print(f"  volume_size_gb: {config.volume_size_gb}")
    print(f"  max_runtime_seconds: {config.max_runtime_seconds}")
    print(f"  enable_network_isolation: {config.enable_network_isolation}")
    print(f"  environment_keys: {sorted(config.environment)}")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Launch Study 2 vLLM LoRA eval on SageMaker."
    )
    parser.add_argument(
        "--ablation",
        default=DEFAULT_ABLATION,
        choices=("unanimous", "split", "all"),
    )
    parser.add_argument("--run-name", default=DEFAULT_RUN_NAME)
    parser.add_argument(
        "--limit",
        type=int,
        default=DEFAULT_LIMIT,
        help="Smoke row limit (omit with --no-limit for full table).",
    )
    parser.add_argument(
        "--no-limit",
        action="store_true",
        help="Run full evaluation (not used for smoke orchestration).",
    )
    parser.add_argument(
        "--instance-type",
        default=INSTANCE_TYPE_DEFAULT,
        help="SageMaker instance type (e.g. ml.g5.2xlarge retry).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print config without CreateTrainingJob.",
    )
    parser.add_argument(
        "--wait",
        action="store_true",
        help="Block until the job finishes.",
    )
    parser.add_argument(
        "--job-name",
        default=None,
        help="Optional fixed training job name (for tests).",
    )
    parser.add_argument(
        "--max-runtime-seconds",
        type=int,
        default=None,
        help="Override the job cap. Full runs default to four hours.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)
    limit: int | None = None if args.no_limit else args.limit
    if args.max_runtime_seconds is not None:
        max_runtime_seconds = args.max_runtime_seconds
    elif args.no_limit:
        max_runtime_seconds = FULL_MAX_RUNTIME_SECONDS
    else:
        max_runtime_seconds = MAX_RUNTIME_SECONDS
    job_name_prefix = "study2-vllm-eval-full" if args.no_limit else BASE_JOB_NAME
    job_name = args.job_name or _training_job_name(prefix=job_name_prefix)

    if args.dry_run:
        config = build_job_config(
            instance_type=args.instance_type,
            ablation=args.ablation,
            run_name=args.run_name,
            limit=limit,
            max_runtime_seconds=max_runtime_seconds,
            job_name_prefix=job_name_prefix,
            environment={
                "AWS_ACCESS_KEY_ID": "dry-run",
                "AWS_SECRET_ACCESS_KEY": "dry-run",
                "AWS_DEFAULT_REGION": AWS_REGION,
                "PYTHONPATH": "/app",
                "HF_TOKEN": "dry-run",
            },
        )
        print_job_config(config, job_name)
        print("dry-run: not calling CreateTrainingJob")
        return

    config = build_job_config(
        instance_type=args.instance_type,
        ablation=args.ablation,
        run_name=args.run_name,
        limit=limit,
        max_runtime_seconds=max_runtime_seconds,
        job_name_prefix=job_name_prefix,
    )
    print_job_config(config, job_name)
    submitted = submit_job(config, training_job_name=job_name)
    print(f"Submitted SageMaker training job: {submitted}")
    if args.wait:
        final = wait_for_job(submitted, region=config.region)
        print(f"Final status: {final}")


if __name__ == "__main__":
    main(sys.argv[1:])
