"""Launch SageMaker adapter inference for the unanimous LoRA on modal data.

Reuses the larger experiment ECR image and entrypoint. Mounts the pull
request 54 adapter and writes preds under preds/unanimous_lora/.

Run from root::

    PYTHONPATH=. uv run --extra finetune-qwen-2026-08-08 python \\
      experiments/compare_qwen_lora_modal_eval_2026_08_12/launch_sagemaker.py \\
      --mode infer_unanimous_adapter [--dry-run] [--wait]
"""

from __future__ import annotations

import argparse
import os
import sys
from dataclasses import replace
from enum import Enum

import boto3

from experiments.finetune_qwen_model_2026_08_08 import launch_sagemaker as prior
from experiments.larger_finetune_qwen_model_2026_08_08 import (
    launch_sagemaker as larger,
)

AWS_REGION = "us-east-2"
INSTANCE_TYPE = "ml.g5.xlarge"
ECR_REPO_NAME = "mirrorview-larger_finetune_qwen_model_2026_08_08"
CONTAINER_ENTRY_POINT = (
    "/app/experiments/larger_finetune_qwen_model_2026_08_08/entrypoint.sh",
)
DATA_S3_URI = (
    "s3://mirrorview-experimental-artifacts/"
    "mirrorview-larger_finetune_qwen_model_2026_08_08/data"
)
# Lean copy of PR 54 adapter weights (no checkpoints / model.tar.gz).
ADAPTER_S3_URI = (
    "s3://mirrorview-experimental-artifacts/"
    "mirrorview-larger_finetune_qwen_model_2026_08_08/adapters/"
    "unanimous_passrole_probe3_lean"
)
PREDS_S3_URI = (
    "s3://mirrorview-experimental-artifacts/"
    "mirrorview-larger_finetune_qwen_model_2026_08_08/preds/unanimous_lora"
)
DEFAULT_SAGEMAKER_ROLE_ARN = (
    "arn:aws:iam::517478598677:role/mirrorview-qwen-finetune-sm-exec"
)


class LaunchMode(str, Enum):
    """Supported comparison launch modes."""

    INFER_UNANIMOUS_ADAPTER = "infer_unanimous_adapter"


def _load_sagemaker_role_arn() -> str:
    """Return SAGEMAKER_ROLE_ARN, with the known Qwen role as fallback."""
    role = os.environ.get("SAGEMAKER_ROLE_ARN", "").strip()
    if not role or role.startswith("[REDACTED]"):
        return DEFAULT_SAGEMAKER_ROLE_ARN
    if "modernbert-sagemaker-executio" in role and not role.endswith(
        "modernbert-sagemaker-execution"
    ):
        return DEFAULT_SAGEMAKER_ROLE_ARN
    if role.endswith("modernbert-sagemaker-execution"):
        return DEFAULT_SAGEMAKER_ROLE_ARN
    return larger._load_sagemaker_role_arn()


def resolve_image_uri(region: str, account_id: str | None = None) -> str:
    """Build ECR image URI for the larger experiment repository."""
    return prior.resolve_image_uri(
        region=region,
        account_id=account_id,
        ecr_repo_name=ECR_REPO_NAME,
    )


def build_job_config(
    run_id: str,
    role_arn: str,
    hf_token: str,
    image_uri: str,
    region: str = AWS_REGION,
    instance_type: str = INSTANCE_TYPE,
) -> prior.JobConfig:
    """Construct config for unanimous-adapter infer on modal chat data."""
    base = prior.build_job_config(
        mode=prior.LaunchMode.INFER_ADAPTER,
        run_id=run_id,
        role_arn=role_arn,
        hf_token=hf_token,
        wandb_api_key=None,
        image_uri=image_uri,
        region=region,
        instance_type=instance_type,
        s3_bucket="mirrorview-experimental-artifacts",
        s3_prefix="mirrorview-larger_finetune_qwen_model_2026_08_08",
        wandb_project="mirrorview-compare-qwen-lora-modal-eval-2026-08-12",
        container_entry_point=CONTAINER_ENTRY_POINT,
    )
    environment = dict(base.environment)
    environment["PREDS_S3_URI"] = PREDS_S3_URI
    environment["RUN_ID"] = run_id
    return replace(
        base,
        data_s3_uri=DATA_S3_URI,
        adapter_s3_uri=ADAPTER_S3_URI,
        output_s3_uri=PREDS_S3_URI,
        environment=environment,
        container_arguments=["infer_adapter"],
        container_entry_point=list(CONTAINER_ENTRY_POINT),
    )


def submit_job(config: prior.JobConfig, wait: bool) -> str:
    """Submit a SageMaker job with Debugger and Profiler disabled.

    New SageMaker accounts cannot enable Debugger (maintenance mode). Prior
    teachability jobs worked before that restriction.
    """
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
        container_entry_point=config.container_entry_point,
        container_arguments=config.container_arguments,
        debugger_hook_config=False,
        disable_profiler=True,
    )

    inputs: dict[str, str] = {"data": config.data_s3_uri}
    if (
        config.mode is prior.LaunchMode.INFER_ADAPTER
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
        description=(
            "Launch unanimous LoRA adapter inference on modal keep/remove data."
        )
    )
    parser.add_argument(
        "--mode",
        choices=[m.value for m in LaunchMode],
        required=True,
        help="infer_unanimous_adapter",
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
    if LaunchMode(args.mode) is not LaunchMode.INFER_UNANIMOUS_ADAPTER:
        raise SystemExit(f"Unsupported mode: {args.mode}")

    run_id = args.run_id or prior._run_id()
    role_arn = _load_sagemaker_role_arn()
    hf_token = prior._require_hf_token()

    if args.dry_run:
        try:
            image_uri = resolve_image_uri(AWS_REGION)
        except Exception:
            image_uri = (
                f"<account>.dkr.ecr.{AWS_REGION}.amazonaws.com/"
                f"{ECR_REPO_NAME}:latest"
            )
        config = build_job_config(
            run_id=run_id,
            role_arn=role_arn,
            hf_token=hf_token,
            image_uri=image_uri,
        )
        prior.print_job_config(config)
        print("dry-run: not submitting fit()")
        return

    image_uri = resolve_image_uri(AWS_REGION)
    config = build_job_config(
        run_id=run_id,
        role_arn=role_arn,
        hf_token=hf_token,
        image_uri=image_uri,
    )
    prior.print_job_config(config)
    submit_job(config, wait=bool(args.wait))


if __name__ == "__main__":
    main(sys.argv[1:])
