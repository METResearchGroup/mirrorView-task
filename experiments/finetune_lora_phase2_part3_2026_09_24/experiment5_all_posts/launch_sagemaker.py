"""Launch SageMaker jobs for experiment5 merge and vLLM infer.

Run from root::

    PYTHONPATH=. uv run python \\
      experiments/finetune_lora_phase2_part3_2026_09_24/experiment5_all_posts/launch_sagemaker.py \\
      --mode merge --model unanimous [--dry-run] [--wait]
"""

from __future__ import annotations

import argparse
import os
import sys
from dataclasses import dataclass
from typing import Literal

import boto3

from experiments.finetune_lora_phase2_part3_2026_09_24.experiment5_all_posts.constants import (
    ADAPTER_S3_URIS,
    AWS_REGION,
    CONTAINER_ENTRY_POINT,
    DATA_S3_URI,
    ECR_IMAGE_URI,
    INSTANCE_TYPE,
    MODEL_ID,
    ModelVariant,
    SAGEMAKER_ROLE_ARN,
    merged_model_s3_uri,
    preds_s3_uri,
)
from experiments.finetune_qwen_model_2026_08_08.launch_sagemaker import (
    JobConfig,
    print_job_config,
)

LaunchModeName = Literal["merge", "infer"]


@dataclass(frozen=True)
class AllPostsJobConfig:
    """Resolved SageMaker configuration for experiment5."""

    mode: LaunchModeName
    model_variant: ModelVariant
    region: str
    instance_type: str
    image_uri: str
    role_arn: str
    data_s3_uri: str
    output_s3_uri: str
    adapter_s3_uri: str | None
    merged_s3_uri: str | None
    preds_s3_uri: str | None
    environment: dict[str, str]
    container_arguments: list[str]
    container_entry_point: list[str]


def _require_hf_token() -> str:
    token = os.environ.get("HF_TOKEN", "").strip()
    if not token:
        raise ValueError("HF_TOKEN is required but missing or empty.")
    return token


def _load_role_arn() -> str:
    role = os.environ.get("SAGEMAKER_ROLE_ARN", "").strip()
    if not role or role.startswith("[REDACTED]"):
        return SAGEMAKER_ROLE_ARN
    return role


def build_job_config(
    mode: LaunchModeName,
    model_variant: ModelVariant,
    role_arn: str,
    hf_token: str,
    image_uri: str = ECR_IMAGE_URI,
    region: str = AWS_REGION,
    instance_type: str = INSTANCE_TYPE,
) -> AllPostsJobConfig:
    """Construct frozen job config without submitting to SageMaker."""
    adapter_uri = ADAPTER_S3_URIS[model_variant]
    merged_uri = merged_model_s3_uri(model_variant)
    preds_uri = preds_s3_uri(model_variant)

    base_env = {
        "HF_TOKEN": hf_token,
        "AWS_REGION": region,
        "MODEL_ID": MODEL_ID,
        "MODEL_VARIANT": model_variant,
    }

    if mode == "merge":
        output_uri = merged_uri
        environment = {
            **base_env,
            "MERGED_DIR": "/opt/ml/model",
        }
        adapter_s3_uri = adapter_uri
        merged_s3_uri_value = None
        preds_s3_uri_value = None
        data_s3_uri = DATA_S3_URI
    else:
        output_uri = preds_uri
        environment = {
            **base_env,
            "MERGED_DIR": "/opt/ml/input/data/merged",
            "CHAT_JSONL": "/opt/ml/input/data/data/chat_all_posts.jsonl",
            "OUTPUT_CSV": "/opt/ml/model/all_posts.csv",
            "PREDS_S3_URI": preds_uri,
        }
        adapter_s3_uri = None
        merged_s3_uri_value = merged_uri
        preds_s3_uri_value = preds_uri
        data_s3_uri = DATA_S3_URI

    return AllPostsJobConfig(
        mode=mode,
        model_variant=model_variant,
        region=region,
        instance_type=instance_type,
        image_uri=image_uri,
        role_arn=role_arn,
        data_s3_uri=data_s3_uri,
        output_s3_uri=output_uri,
        adapter_s3_uri=adapter_s3_uri,
        merged_s3_uri=merged_s3_uri_value,
        preds_s3_uri=preds_s3_uri_value,
        environment=environment,
        container_arguments=[mode],
        container_entry_point=list(CONTAINER_ENTRY_POINT),
    )


def _to_legacy_job_config(config: AllPostsJobConfig) -> JobConfig:
    """Adapt experiment5 config to the August ``JobConfig`` for ``submit_job``."""
    from experiments.finetune_qwen_model_2026_08_08.launch_sagemaker import LaunchMode

    mode = LaunchMode.INFER_ADAPTER if config.mode == "infer" else LaunchMode.TRAIN
    return JobConfig(
        mode=mode,
        run_id=f"exp5_{config.model_variant}_{config.mode}",
        region=config.region,
        instance_type=config.instance_type,
        image_uri=config.image_uri,
        role_arn=config.role_arn,
        data_s3_uri=config.data_s3_uri,
        output_s3_uri=config.output_s3_uri,
        adapter_s3_uri=config.adapter_s3_uri,
        environment=config.environment,
        container_arguments=config.container_arguments,
        container_entry_point=config.container_entry_point,
    )


def submit_all_posts_job(config: AllPostsJobConfig, wait: bool) -> str:
    """Submit a SageMaker Training job with merge or infer channels."""
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
        base_job_name=f"exp5-all-posts-{config.mode}-{config.model_variant}",
        hyperparameters={},
        container_entry_point=config.container_entry_point,
        container_arguments=config.container_arguments,
    )

    inputs: dict[str, str] = {"data": config.data_s3_uri}
    if config.mode == "merge" and config.adapter_s3_uri is not None:
        inputs["adapter"] = config.adapter_s3_uri
    if config.mode == "infer" and config.merged_s3_uri is not None:
        inputs["merged"] = config.merged_s3_uri

    estimator.fit(inputs=inputs, wait=wait)
    job_name = estimator.latest_training_job.name
    print(f"SageMaker job: {job_name}")
    print(f"Data URI: {config.data_s3_uri}/")
    print(f"Output URI: {config.output_s3_uri}/")
    if config.adapter_s3_uri:
        print(f"Adapter URI: {config.adapter_s3_uri}/")
    if config.merged_s3_uri:
        print(f"Merged URI: {config.merged_s3_uri}/")
    if config.preds_s3_uri:
        print(f"Preds URI: {config.preds_s3_uri}/")
    return str(job_name)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Launch experiment5 merge or vLLM infer SageMaker jobs."
    )
    parser.add_argument(
        "--mode",
        choices=("merge", "infer"),
        required=True,
        help="merge adapter into base | infer on merged weights",
    )
    parser.add_argument(
        "--model",
        choices=("unanimous", "modal"),
        required=True,
        help="Which adapter / merged model arm to run",
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
    args = parse_args(argv)
    role_arn = _load_role_arn()
    hf_token = _require_hf_token()
    config = build_job_config(
        mode=args.mode,
        model_variant=args.model,
        role_arn=role_arn,
        hf_token=hf_token,
    )
    legacy = _to_legacy_job_config(config)
    print_job_config(legacy)
    print(f"  model_variant: {config.model_variant}")
    if config.merged_s3_uri:
        print(f"  merged_s3_uri: {config.merged_s3_uri}")
    if config.preds_s3_uri:
        print(f"  preds_s3_uri: {config.preds_s3_uri}")

    if args.dry_run:
        print("dry-run: not submitting fit()")
        return

    submit_all_posts_job(config, wait=bool(args.wait))


if __name__ == "__main__":
    main(sys.argv[1:])
