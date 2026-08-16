"""Download existing prediction CSVs into the local three-arm preds layout.

Baseline and modal arms come from the larger experiment S3 preds prefix.
The unanimous arm is optional and is filled after the SageMaker job.

Run from root::

    PYTHONPATH=. uv run --extra finetune-qwen-2026-08-08 python \\
      experiments/compare_qwen_lora_modal_eval_2026_08_12/sync_existing_preds.py \\
      --preds-dir experiments/compare_qwen_lora_modal_eval_2026_08_12/preds
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import boto3

S3_BUCKET = "mirrorview-experimental-artifacts"
S3_PREDS_PREFIX = "mirrorview-larger_finetune_qwen_model_2026_08_08/preds"
AWS_REGION = "us-east-2"

# Local arm dir -> remote S3 arm dir under S3_PREDS_PREFIX.
BASE_ARM_SOURCES = {
    "baseline": "baseline",
    "modal_lora": "fine_tuned",
}
UNANIMOUS_ARM_SOURCE = ("unanimous_lora", "unanimous_lora")
SPLIT_FILES = ("train_labels.csv", "test_labels.csv")


def download_file(
    client: object,
    bucket: str,
    key: str,
    dest: Path,
    force: bool,
) -> None:
    """Download one S3 object to ``dest``."""
    if dest.exists() and not force:
        raise FileExistsError(
            f"Refusing to overwrite {dest} without --force"
        )
    dest.parent.mkdir(parents=True, exist_ok=True)
    client.download_file(bucket, key, str(dest))
    print(f"Downloaded s3://{bucket}/{key} -> {dest}")


def sync_arms(
    preds_dir: Path,
    *,
    include_unanimous: bool,
    force: bool,
    region: str = AWS_REGION,
    bucket: str = S3_BUCKET,
) -> list[Path]:
    """Download prediction CSVs into the local preds layout."""
    client = boto3.client("s3", region_name=region)
    sources = dict(BASE_ARM_SOURCES)
    if include_unanimous:
        local_arm, remote_arm = UNANIMOUS_ARM_SOURCE
        sources[local_arm] = remote_arm

    written: list[Path] = []
    for local_arm, remote_arm in sources.items():
        for filename in SPLIT_FILES:
            key = f"{S3_PREDS_PREFIX}/{remote_arm}/{filename}"
            dest = preds_dir / local_arm / filename
            download_file(client, bucket, key, dest, force=force)
            written.append(dest)
    return written


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse CLI arguments."""
    parser = argparse.ArgumentParser(
        description="Sync existing keep/remove prediction CSVs from S3."
    )
    parser.add_argument(
        "--preds-dir",
        required=True,
        help="Local preds directory (baseline/ modal_lora/ [unanimous_lora/]).",
    )
    parser.add_argument(
        "--include-unanimous",
        action="store_true",
        help="Also download preds/unanimous_lora/ from S3.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite existing local CSVs.",
    )
    parser.add_argument(
        "--region",
        default=AWS_REGION,
        help=f"AWS region (default: {AWS_REGION}).",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    """CLI entrypoint."""
    args = parse_args(argv)
    written = sync_arms(
        Path(args.preds_dir),
        include_unanimous=bool(args.include_unanimous),
        force=bool(args.force),
        region=str(args.region),
    )
    print(f"Synced {len(written)} files")


if __name__ == "__main__":
    main(sys.argv[1:])
