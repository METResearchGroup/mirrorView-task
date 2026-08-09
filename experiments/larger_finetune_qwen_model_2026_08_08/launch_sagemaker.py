"""Launch SageMaker jobs for the larger modal-label Qwen LoRA experiment.

Reuses helpers from ``experiments.finetune_qwen_model_2026_08_08.launch_sagemaker``
and overrides only cloud names and the container entrypoint.

Run from root::

    PYTHONPATH=. uv run --extra finetune-qwen-2026-08-08 python \\
      experiments/larger_finetune_qwen_model_2026_08_08/launch_sagemaker.py \\
      --mode train --run-id <RUN_ID> [--dry-run] [--wait]
"""

from __future__ import annotations

import argparse
import sys

from experiments.finetune_qwen_model_2026_08_08 import launch_sagemaker as prior

S3_BUCKET = "mirrorview-experimental-artifacts"
S3_PREFIX = "mirrorview-larger_finetune_qwen_model_2026_08_08"
AWS_REGION = "us-east-2"
ECR_REPO_NAME = "mirrorview-larger_finetune_qwen_model_2026_08_08"
INSTANCE_TYPE = "ml.g5.xlarge"
WANDB_PROJECT = "mirrorview-larger-finetune-qwen-2026-08-08"
CONTAINER_ENTRY_POINT = (
    "/app/experiments/larger_finetune_qwen_model_2026_08_08/entrypoint.sh",
)

LaunchMode = prior.LaunchMode


def resolve_image_uri(region: str, account_id: str | None = None) -> str:
    """Build ECR image URI for this experiment repository."""
    return prior.resolve_image_uri(
        region=region,
        account_id=account_id,
        ecr_repo_name=ECR_REPO_NAME,
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
) -> prior.JobConfig:
    """Construct frozen job config using this experiment's cloud names."""
    return prior.build_job_config(
        mode=mode,
        run_id=run_id,
        role_arn=role_arn,
        hf_token=hf_token,
        wandb_api_key=wandb_api_key,
        image_uri=image_uri,
        region=region,
        instance_type=instance_type,
        s3_bucket=S3_BUCKET,
        s3_prefix=S3_PREFIX,
        wandb_project=WANDB_PROJECT,
        container_entry_point=CONTAINER_ENTRY_POINT,
    )


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse CLI arguments."""
    parser = argparse.ArgumentParser(
        description="Launch larger modal-label Qwen LoRA SageMaker jobs."
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
    run_id = args.run_id or prior._run_id()

    role_arn = prior._load_sagemaker_role_arn()
    hf_token = prior._require_hf_token()
    wandb_key: str | None = None
    if mode is LaunchMode.TRAIN:
        wandb_key = prior._load_wandb_api_key()

    if args.dry_run:
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
        prior.print_job_config(config)
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
    prior.print_job_config(config)
    prior.submit_job(config, wait=bool(args.wait))


if __name__ == "__main__":
    main(sys.argv[1:])
