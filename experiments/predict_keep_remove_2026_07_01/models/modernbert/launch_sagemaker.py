"""Launch ModernBERT training on SageMaker (ml.g4dn.xlarge, us-east-2).

Uploads stratified train/val/test CSVs to
``s3://jspsych-mirror-view-4/modernbert-training/<run_id>/data/`` and submits
a Hugging Face estimator that runs the same ``train.py`` entrypoint.

Requires ``SAGEMAKER_ROLE_ARN`` and standard AWS credentials. Passes
``WANDB_API_KEY`` from ``EnvVarsContainer`` into the job environment.

Run from root::

    PYTHONPATH=. uv run --extra modernbert-training python \\
      experiments/predict_keep_remove_2026_07_01/models/modernbert/launch_sagemaker.py \\
      --config experiments/predict_keep_remove_2026_07_01/models/modernbert/configs/modernbert_base.yaml
"""

from __future__ import annotations

import argparse
import os
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import boto3
import yaml

PACKAGE_DIR = Path(__file__).resolve().parent


def _load_config(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    if not isinstance(cfg, dict):
        raise ValueError(f"Config must be a mapping: {path}")
    return cfg


def _load_wandb_api_key() -> str:
    from lib.load_env_vars import EnvVarsContainer

    return EnvVarsContainer.get_env_var("WANDB_API_KEY", required=True)


def _load_sagemaker_role_arn() -> str:
    # Ensure .env is loaded via EnvVarsContainer side effect.
    _load_wandb_api_key()
    role = os.environ.get("SAGEMAKER_ROLE_ARN", "").strip()
    if not role:
        raise ValueError(
            "SAGEMAKER_ROLE_ARN is required to launch SageMaker training. "
            "Set it to an IAM execution role ARN."
        )
    return role


def _run_id() -> str:
    return datetime.now(timezone.utc).strftime("%Y_%m_%d-%H%M%S")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Upload splits and launch ModernBERT SageMaker training."
    )
    parser.add_argument(
        "--config",
        default=str(PACKAGE_DIR / "configs" / "modernbert_base.yaml"),
        help="Path to YAML config.",
    )
    parser.add_argument(
        "--run-id",
        default=None,
        help="Optional run id (default: UTC timestamp).",
    )
    parser.add_argument(
        "--wait",
        action="store_true",
        help="Block until the training job completes.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Optional row cap forwarded to train.py (smoke).",
    )
    parser.add_argument(
        "--num-train-epochs",
        type=float,
        default=None,
        help="Optional epoch override forwarded to train.py.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)
    config_path = Path(args.config)
    if not config_path.is_file():
        raise FileNotFoundError(f"Config not found: {config_path}")

    cfg = _load_config(config_path)
    sm_cfg = cfg.get("sagemaker") or {}
    region = str(sm_cfg.get("region", "us-east-2"))
    instance_type = str(sm_cfg.get("instance_type", "ml.g4dn.xlarge"))
    bucket = str(sm_cfg.get("s3_bucket", "jspsych-mirror-view-4"))
    prefix = str(sm_cfg.get("s3_prefix", "modernbert-training"))

    role_arn = _load_sagemaker_role_arn()
    wandb_key = _load_wandb_api_key()
    run_id = args.run_id or _run_id()

    from experiments.predict_keep_remove_2026_07_01.models.modernbert.dataloader import (
        load_classifier_dataframe,
        make_train_val_test_split,
    )

    df = load_classifier_dataframe()
    if args.limit is not None:
        df = df.sample(
            n=min(int(args.limit), len(df)),
            random_state=int(cfg["random_state"]),
        ).reset_index(drop=True)

    train_df, val_df, test_df = make_train_val_test_split(
        df,
        train_fraction=float(cfg["train_fraction"]),
        val_fraction=float(cfg["val_fraction"]),
        test_fraction=float(cfg["test_fraction"]),
        seed=int(cfg["random_state"]),
        label_column=str(cfg["label_col"]),
    )

    data_prefix = f"{prefix}/{run_id}/data"
    output_prefix = f"{prefix}/{run_id}/output"
    data_uri = f"s3://{bucket}/{data_prefix}"
    output_uri = f"s3://{bucket}/{output_prefix}"

    s3 = boto3.client("s3", region_name=region)
    with tempfile.TemporaryDirectory(prefix="modernbert_sm_") as tmp:
        tmp_path = Path(tmp)
        splits = {
            "train": train_df,
            "val": val_df,
            "test": test_df,
        }
        for name, split_df in splits.items():
            local_csv = tmp_path / f"{name}.csv"
            split_df.to_csv(local_csv, index=False)
            key = f"{data_prefix}/{name}.csv"
            s3.upload_file(str(local_csv), bucket, key)
            print(f"Uploaded s3://{bucket}/{key}")

    # Upload config alongside data for the job (also in source_dir).
    # Estimator uses package source_dir which already includes configs/.

    hyperparameters: dict[str, str] = {
        "config": "configs/modernbert_base.yaml",
    }
    if args.limit is not None:
        hyperparameters["limit"] = str(int(args.limit))
    if args.num_train_epochs is not None:
        # SageMaker passes keys as --<key>; match argparse --num-train-epochs.
        hyperparameters["num-train-epochs"] = str(args.num_train_epochs)

    import sagemaker
    from sagemaker.huggingface import HuggingFace

    session = sagemaker.Session(
        boto_session=boto3.Session(region_name=region),
    )

    estimator = HuggingFace(
        entry_point="train.py",
        source_dir=str(PACKAGE_DIR),
        role=role_arn,
        instance_type=instance_type,
        instance_count=1,
        transformers_version="4.49.0",
        pytorch_version="2.5.1",
        py_version="py311",
        hyperparameters=hyperparameters,
        output_path=output_uri,
        environment={
            "WANDB_API_KEY": wandb_key,
            "WANDB_PROJECT": str(cfg["wandb_project"]),
        },
        sagemaker_session=session,
        base_job_name="modernbert-keep-remove",
    )

    estimator.fit(
        {
            "train": f"{data_uri}/train.csv",
            "val": f"{data_uri}/val.csv",
            "test": f"{data_uri}/test.csv",
        },
        wait=bool(args.wait),
    )

    job_name = estimator.latest_training_job.name
    print(f"SageMaker job: {job_name}")
    print(f"Data URI: {data_uri}/")
    print(f"Output URI: {output_uri}/")

    # Verify uploads via AWS CLI when available.
    ls_uri = f"s3://{bucket}/{prefix}/{run_id}/"
    try:
        subprocess.run(
            ["aws", "s3", "ls", ls_uri, "--recursive"],
            check=False,
        )
    except FileNotFoundError:
        print("aws CLI not found; skipped s3 ls verification.")

    print(f"Run id: {run_id}")


if __name__ == "__main__":
    main()
