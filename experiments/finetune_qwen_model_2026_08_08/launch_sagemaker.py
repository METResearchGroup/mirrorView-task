"""Launch SageMaker jobs for Qwen LoRA train / infer_baseline / infer_adapter.

Uses a custom ECR image (not the Hugging Face estimator). Instance type
``ml.g5.xlarge`` in ``us-east-2``.

Run from root::

    PYTHONPATH=. uv run --extra finetune-qwen-2026-08-08 python \\
      experiments/finetune_qwen_model_2026_08_08/launch_sagemaker.py \\
      --mode train --run-id <RUN_ID> [--dry-run] [--wait]
"""

from __future__ import annotations

import argparse
import os
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum

import boto3

S3_BUCKET = "mirrorview-experimental-artifacts"
S3_PREFIX = "mirrorview-finetune_qwen_model_2026_08_08"
AWS_REGION = "us-east-2"
ECR_REPO_NAME = "mirrorview-finetune_qwen_model_2026_08_08"
INSTANCE_TYPE = "ml.g5.xlarge"
WANDB_PROJECT = "mirrorview-finetune-qwen-2026-08-08"


class LaunchMode(str, Enum):
    """SageMaker container mode."""

    TRAIN = "train"
    INFER_BASELINE = "infer_baseline"
    INFER_ADAPTER = "infer_adapter"


@dataclass(frozen=True)
class JobConfig:
    """Resolved SageMaker job configuration (for dry-run + tests)."""

    mode: LaunchMode
    run_id: str
    region: str
    instance_type: str
    image_uri: str
    role_arn: str
    data_s3_uri: str
    output_s3_uri: str
    adapter_s3_uri: str | None
    environment: dict[str, str]
    container_arguments: list[str]


def _run_id() -> str:
    """UTC timestamp run id."""
    return datetime.now(timezone.utc).strftime("%Y_%m_%d-%H%M%S")


def _require_hf_token() -> str:
    """Return HF_TOKEN or raise."""
    token = os.environ.get("HF_TOKEN", "").strip()
    if not token:
        raise ValueError("HF_TOKEN is required but missing or empty.")
    return token


def _load_wandb_api_key() -> str:
    """Return WANDB_API_KEY via EnvVarsContainer."""
    from lib.load_env_vars import EnvVarsContainer

    return EnvVarsContainer.get_env_var("WANDB_API_KEY", required=True)


def _load_sagemaker_role_arn() -> str:
    """Return SAGEMAKER_ROLE_ARN after ensuring .env is loaded."""
    # Side effect: load .env through EnvVarsContainer for WANDB-related keys.
    from lib.load_env_vars import EnvVarsContainer

    EnvVarsContainer.get_env_var("WANDB_API_KEY", required=False)
    role = os.environ.get("SAGEMAKER_ROLE_ARN", "").strip()
    if not role:
        raise ValueError(
            "SAGEMAKER_ROLE_ARN is required to launch SageMaker jobs."
        )
    return role


def resolve_image_uri(region: str, account_id: str | None = None) -> str:
    """Build ECR image URI for the experiment repository."""
    if account_id is None:
        sts = boto3.client("sts", region_name=region)
        account_id = sts.get_caller_identity()["Account"]
    return (
        f"{account_id}.dkr.ecr.{region}.amazonaws.com/"
        f"{ECR_REPO_NAME}:latest"
    )


def build_job_config(
    mode: LaunchMode,
    run_id: str,
    role_arn: str,
    hf_token: str,
    wandb_api_key: str | None,
    image_uri: str,
    region: str = AWS_REGION,
    instance_type: str = INSTANCE_TYPE,
) -> JobConfig:
    """Construct frozen job config for a mode (no AWS submit)."""
    data_s3_uri = f"s3://{S3_BUCKET}/{S3_PREFIX}/data"
    adapter_s3_uri = f"s3://{S3_BUCKET}/{S3_PREFIX}/adapters/{run_id}"
    if mode is LaunchMode.TRAIN:
        output_s3_uri = adapter_s3_uri
        container_arguments = ["train"]
        environment = {
            "HF_TOKEN": hf_token,
            "WANDB_API_KEY": str(wandb_api_key),
            "WANDB_PROJECT": WANDB_PROJECT,
            "RUN_ID": run_id,
            "MODE": mode.value,
            "AWS_REGION": region,
            "ADAPTER_S3_URI": adapter_s3_uri,
        }
    elif mode is LaunchMode.INFER_BASELINE:
        output_s3_uri = f"s3://{S3_BUCKET}/{S3_PREFIX}/preds/baseline"
        container_arguments = ["infer_baseline"]
        environment = {
            "HF_TOKEN": hf_token,
            "RUN_ID": run_id,
            "MODE": mode.value,
            "AWS_REGION": region,
            "PREDS_S3_URI": output_s3_uri,
        }
        adapter_s3_uri = None
    else:
        output_s3_uri = f"s3://{S3_BUCKET}/{S3_PREFIX}/preds/fine_tuned"
        container_arguments = ["infer_adapter"]
        environment = {
            "HF_TOKEN": hf_token,
            "RUN_ID": run_id,
            "MODE": mode.value,
            "AWS_REGION": region,
            "PREDS_S3_URI": output_s3_uri,
        }

    return JobConfig(
        mode=mode,
        run_id=run_id,
        region=region,
        instance_type=instance_type,
        image_uri=image_uri,
        role_arn=role_arn,
        data_s3_uri=data_s3_uri,
        output_s3_uri=output_s3_uri,
        adapter_s3_uri=adapter_s3_uri,
        environment=environment,
        container_arguments=container_arguments,
    )


def print_job_config(config: JobConfig) -> None:
    """Pretty-print resolved job config."""
    print("SageMaker job config:")
    print(f"  mode: {config.mode.value}")
    print(f"  run_id: {config.run_id}")
    print(f"  region: {config.region}")
    print(f"  instance_type: {config.instance_type}")
    print(f"  image_uri: {config.image_uri}")
    print(f"  role_arn: {config.role_arn}")
    print(f"  data_s3_uri: {config.data_s3_uri}")
    print(f"  output_s3_uri: {config.output_s3_uri}")
    print(f"  adapter_s3_uri: {config.adapter_s3_uri}")
    print(f"  container_arguments: {config.container_arguments}")
    env_keys = sorted(config.environment)
    print(f"  environment_keys: {env_keys}")


def submit_job(config: JobConfig, wait: bool) -> str:
    """Submit a SageMaker Training job with the custom image."""
    import sagemaker
    from sagemaker.estimator import Estimator

    session = sagemaker.Session(
        boto_session=boto3.Session(region_name=config.region),
    )
    estimator = Estimator(
        image_uri=config.image_uri,
        role=config.role_arn,
        instance_count=1,
        instance_type=config.instance_type,
        output_path=config.output_s3_uri,
        sagemaker_session=session,
        environment=config.environment,
        base_job_name=f"qwen-lora-{config.mode.value.replace('_', '-')}",
        hyperparameters={},
        container_entry_point=["/app/experiments/finetune_qwen_model_2026_08_08/entrypoint.sh"],
        container_arguments=config.container_arguments,
    )

    inputs: dict[str, str] = {"data": config.data_s3_uri}
    if (
        config.mode is LaunchMode.INFER_ADAPTER
        and config.adapter_s3_uri is not None
    ):
        inputs["adapter"] = config.adapter_s3_uri

    estimator.fit(inputs=inputs, wait=wait)
    job_name = estimator.latest_training_job.name
    print(f"SageMaker job: {job_name}")
    print(f"Data URI: {config.data_s3_uri}/")
    print(f"Output URI: {config.output_s3_uri}/")
    if config.adapter_s3_uri:
        print(f"Adapter URI: {config.adapter_s3_uri}/")
    print(f"Run id: {config.run_id}")
    return str(job_name)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse CLI arguments."""
    parser = argparse.ArgumentParser(
        description="Launch Qwen LoRA SageMaker train/infer jobs."
    )
    parser.add_argument(
        "--mode",
        choices=[m.value for m in LaunchMode],
        required=True,
        help="train | infer_baseline | infer_adapter",
    )
    parser.add_argument(
        "--run-id",
        default=None,
        help="Run id (default: UTC timestamp).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print config without calling fit().",
    )
    parser.add_argument(
        "--wait",
        action="store_true",
        help="Block until the SageMaker job completes.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    """CLI entrypoint."""
    args = parse_args(argv)
    mode = LaunchMode(args.mode)
    run_id = args.run_id or _run_id()

    role_arn = _load_sagemaker_role_arn()
    hf_token = _require_hf_token()
    wandb_key: str | None = None
    if mode is LaunchMode.TRAIN:
        wandb_key = _load_wandb_api_key()

    if args.dry_run:
        # Avoid STS when possible for unit-test friendliness; still resolve
        # a placeholder account if STS works.
        try:
            image_uri = resolve_image_uri(AWS_REGION)
        except Exception:
            image_uri = (
                f"<account>.dkr.ecr.{AWS_REGION}.amazonaws.com/"
                f"{ECR_REPO_NAME}:latest"
            )
        config = build_job_config(
            mode=mode,
            run_id=run_id,
            role_arn=role_arn,
            hf_token=hf_token,
            wandb_api_key=wandb_key or "",
            image_uri=image_uri,
        )
        print_job_config(config)
        print("dry-run: not submitting fit()")
        return

    image_uri = resolve_image_uri(AWS_REGION)
    config = build_job_config(
        mode=mode,
        run_id=run_id,
        role_arn=role_arn,
        hf_token=hf_token,
        wandb_api_key=wandb_key or "",
        image_uri=image_uri,
    )
    print_job_config(config)
    submit_job(config, wait=bool(args.wait))


if __name__ == "__main__":
    main(sys.argv[1:])
