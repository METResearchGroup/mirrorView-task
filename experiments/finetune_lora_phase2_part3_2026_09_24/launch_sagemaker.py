"""Launch SageMaker jobs for Part 3 LoRA fine-tuning experiments.

Wraps ``experiments.finetune_qwen_model_2026_08_08.launch_sagemaker`` with
per-experiment S3 layout and Qwen3.5 thinking-disabled template kwargs.

Run from root::

    PYTHONPATH=. uv run --extra finetune-qwen-2026-08-08 python \\
      experiments/finetune_lora_phase2_part3_2026_09_24/launch_sagemaker.py \\
      --mode train --experiment experiment1_unanimous --run-id <RUN_ID> \\
      [--smoke] [--dry-run] [--wait]
"""

from __future__ import annotations

import argparse
import os
import sys

from experiments.finetune_lora_phase2_part3_2026_09_24.shared.run_config import (
    AWS_REGION,
    CHAT_TEMPLATE_KWARGS,
    ECR_REPO_NAME,
    EXPERIMENT_NAMES,
    INSTANCE_TYPE,
    MODEL_ID,
    S3_BUCKET,
    S3_PREFIX,
    WANDB_PROJECT,
    chat_template_kwargs_json,
    default_hyperparams,
)
from experiments.finetune_qwen_model_2026_08_08 import launch_sagemaker as prior

LaunchMode = prior.LaunchMode
JobConfig = prior.JobConfig

DEFAULT_SAGEMAKER_ROLE_ARN = (
    "arn:aws:iam::517478598677:role/mirrorview-qwen-finetune-sm-exec"
)
CONTAINER_ENTRY_POINT = (
    "/app/experiments/finetune_lora_phase2_part3_2026_09_24/entrypoint.sh",
)


def _load_sagemaker_role_arn() -> str:
    """Return SAGEMAKER_ROLE_ARN, with a known-role fallback if redacted."""
    role = os.environ.get("SAGEMAKER_ROLE_ARN", "").strip()
    if not role or role.startswith("[REDACTED]"):
        return DEFAULT_SAGEMAKER_ROLE_ARN
    return prior._load_sagemaker_role_arn()


def _validate_mode_experiment(mode: LaunchMode, experiment: str) -> None:
    """Reject invalid mode and experiment pairings."""
    if experiment not in EXPERIMENT_NAMES:
        raise ValueError(f"Unknown experiment: {experiment}")
    if mode is LaunchMode.TRAIN and experiment == "experiment4_cross_eval":
        raise ValueError("train mode does not support experiment4_cross_eval")
    if mode is LaunchMode.INFER_ADAPTER and experiment == "experiment4_cross_eval":
        raise ValueError(
            "infer_adapter mode does not support experiment4_cross_eval"
        )
    if mode is LaunchMode.INFER_BASELINE and experiment != "experiment4_cross_eval":
        raise ValueError(
            "infer_baseline is only supported for experiment4_cross_eval"
        )


def resolve_image_uri(region: str, account_id: str | None = None) -> str:
    """Build ECR image URI for this experiment repository."""
    return prior.resolve_image_uri(
        region=region,
        account_id=account_id,
        ecr_repo_name=ECR_REPO_NAME,
    )


def build_job_config(
    mode: LaunchMode,
    experiment: str,
    run_id: str,
    role_arn: str,
    hf_token: str,
    wandb_api_key: str | None,
    image_uri: str,
    smoke: bool = False,
    region: str = AWS_REGION,
    instance_type: str = INSTANCE_TYPE,
) -> JobConfig:
    """Construct frozen job config for a mode and experiment.

    S3 layout
    ---------
    train
        data: ``{prefix}/{experiment}/data/``
        output: ``{prefix}/{experiment}/adapters/{run_id}/``
    infer_baseline (experiment4 only)
        data: ``{prefix}/data/``
        output: ``{prefix}/{experiment}/preds/``
    infer_adapter
        data: ``{prefix}/data/``
        adapter: ``{prefix}/{experiment}/adapters/{run_id}/``
        output: ``{prefix}/{experiment}/preds/``
    """
    _validate_mode_experiment(mode, experiment)
    template_json = chat_template_kwargs_json()
    shared_data_uri = f"s3://{S3_BUCKET}/{S3_PREFIX}/data"
    experiment_preds_uri = f"s3://{S3_BUCKET}/{S3_PREFIX}/{experiment}/preds"
    adapter_s3_uri = (
        f"s3://{S3_BUCKET}/{S3_PREFIX}/{experiment}/adapters/{run_id}"
    )

    base_env = {
        "HF_TOKEN": hf_token,
        "RUN_ID": run_id,
        "MODE": mode.value,
        "AWS_REGION": region,
        "MODEL_ID": MODEL_ID,
        "CHAT_TEMPLATE_KWARGS_JSON": template_json,
    }
    if smoke:
        base_env["SMOKE"] = "1"

    if mode is LaunchMode.TRAIN:
        hyperparams = default_hyperparams(experiment)
        data_s3_uri = f"s3://{S3_BUCKET}/{S3_PREFIX}/{experiment}/data"
        output_s3_uri = adapter_s3_uri
        container_arguments = ["train"]
        environment = {
            **base_env,
            "WANDB_API_KEY": str(wandb_api_key),
            "WANDB_PROJECT": WANDB_PROJECT,
            "NUM_TRAIN_EPOCHS": str(hyperparams.num_train_epochs),
            "ADAPTER_S3_URI": adapter_s3_uri,
        }
    elif mode is LaunchMode.INFER_BASELINE:
        data_s3_uri = shared_data_uri
        output_s3_uri = experiment_preds_uri
        adapter_s3_uri = None
        container_arguments = ["infer_baseline"]
        environment = {
            **base_env,
            "PREDS_S3_URI": output_s3_uri,
        }
    else:
        data_s3_uri = shared_data_uri
        output_s3_uri = experiment_preds_uri
        container_arguments = ["infer_adapter"]
        environment = {
            **base_env,
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
        container_entry_point=list(CONTAINER_ENTRY_POINT),
    )


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse CLI arguments."""
    parser = argparse.ArgumentParser(
        description="Launch Part 3 Qwen LoRA SageMaker train/infer jobs."
    )
    parser.add_argument(
        "--mode",
        choices=[m.value for m in LaunchMode],
        required=True,
        help="train | infer_baseline | infer_adapter",
    )
    parser.add_argument(
        "--experiment",
        choices=list(EXPERIMENT_NAMES),
        required=True,
        help="Part 3 experiment directory name.",
    )
    parser.add_argument(
        "--run-id",
        required=True,
        help="Run id for adapter and prediction paths.",
    )
    parser.add_argument(
        "--smoke",
        action="store_true",
        help="Set SMOKE=1 (train max_steps=2, infer limit=5).",
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
    run_id = args.run_id

    role_arn = _load_sagemaker_role_arn()
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
            experiment=args.experiment,
            run_id=run_id,
            role_arn=role_arn,
            hf_token=hf_token,
            wandb_api_key=wandb_key or "",
            image_uri=image_uri,
            smoke=bool(args.smoke),
        )
        prior.print_job_config(config)
        print("dry-run: not submitting fit()")
        return

    image_uri = resolve_image_uri(AWS_REGION)
    config = build_job_config(
        mode=mode,
        experiment=args.experiment,
        run_id=run_id,
        role_arn=role_arn,
        hf_token=hf_token,
        wandb_api_key=wandb_key or "",
        image_uri=image_uri,
        smoke=bool(args.smoke),
    )
    prior.print_job_config(config)
    prior.submit_job(config, wait=bool(args.wait))


if __name__ == "__main__":
    main(sys.argv[1:])
