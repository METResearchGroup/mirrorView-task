"""Upload a staged release (manifest.json + files under s3_upload/<timestamp>/) to S3, one object per key."""

from __future__ import annotations

import argparse
import subprocess
from pathlib import Path
from typing import Any

from scripts.upload_to_s3.constants import AWS_REGION, STAGING_ROOT, TARGET_BUCKET
from scripts.upload_to_s3.verify_s3_upload import load_manifest, resolve_latest_release_dir


def _head_object(key: str) -> bool:
    proc = subprocess.run(
        [
            "aws",
            "s3api",
            "head-object",
            "--bucket",
            TARGET_BUCKET,
            "--key",
            key,
            "--region",
            AWS_REGION,
        ],
        capture_output=True,
        text=True,
    )
    return proc.returncode == 0


def upload_files_to_s3(release_dir: Path, manifest: dict[str, Any], *, dry_run: bool) -> None:
    files: list[str] = list(manifest["files"])
    if dry_run:
        print(f"Dry run: would upload {len(files)} objects to s3://{TARGET_BUCKET}/")
        for key in files:
            print(f"  {key}")
        return

    for key in files:
        local = release_dir / key
        if not local.is_file():
            raise SystemExit(f"Missing staged file for key {key}: {local}")
        existed = _head_object(key)
        status = "overwrite" if existed else "create"
        print(f"{status}: s3://{TARGET_BUCKET}/{key}")
        subprocess.run(
            [
                "aws",
                "s3",
                "cp",
                str(local),
                f"s3://{TARGET_BUCKET}/{key}",
                "--region",
                AWS_REGION,
            ],
            check=True,
        )


def print_upload_summary(release_dir: Path, manifest: dict[str, Any], *, dry_run: bool) -> None:
    n = len(manifest["files"])
    print(f"Release directory: {release_dir}")
    print(f"Manifest: {release_dir / 'manifest.json'}")
    print(f"Objects: {n}")
    if dry_run:
        print("No S3 writes performed (dry run).")


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Upload staged website files to S3 using manifest.json (one aws s3 cp per key)."
        )
    )
    parser.add_argument(
        "--release-dir",
        type=Path,
        default=None,
        help="Staged release directory (default: latest under s3_upload/).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print intended S3 keys without uploading.",
    )
    args = parser.parse_args()

    release_dir = args.release_dir
    if release_dir is None:
        release_dir = resolve_latest_release_dir(STAGING_ROOT)
    else:
        release_dir = release_dir.resolve()
        if not release_dir.is_dir():
            raise SystemExit(f"Not a directory: {release_dir}")

    manifest = load_manifest(release_dir)
    upload_files_to_s3(release_dir, manifest, dry_run=args.dry_run)
    print_upload_summary(release_dir, manifest, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
