"""Upload the Part 3 experiment outputs tree to S3.

Run from repo root::

    PYTHONPATH=. uv run python \\
      experiments/bertopic_original_mirror_part3_2026_09_24/src/upload_outputs.py
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

BUCKET = "mirrorview-experimental-artifacts"
PREFIX = "experiments/bertopic_original_mirror_part3_2026_09_24"
EXPERIMENT_ROOT = Path(__file__).resolve().parents[1]


def build_s3_key(local_path: str) -> str:
    """Return the S3 key that mirrors a repo-relative experiment path."""
    parts = Path(local_path).parts
    if "experiments" in parts:
        return "/".join(parts[parts.index("experiments") :])
    return str(Path(local_path)).lstrip("/")


def collect_output_files(output_root: Path) -> list[Path]:
    """Every file under ``output_root``, in sorted order."""
    return sorted(path for path in output_root.rglob("*") if path.is_file())


def upload_outputs(
    output_root: Path,
    bucket: str = BUCKET,
    prefix: str = PREFIX,
    dry_run: bool = False,
    client=None,
) -> dict:
    """Upload each file and write ``upload_manifest.json`` beside the tree.

    ``client`` must provide ``put_object(Bucket, Key, Body)`` when ``dry_run``
    is false. The manifest counts one file per put.
    """
    files = collect_output_files(output_root)
    keys = []
    total_bytes = 0
    for path in files:
        relative = path.relative_to(output_root).as_posix()
        key = f"{prefix.rstrip('/')}/outputs/{relative}"
        body = path.read_bytes()
        total_bytes += len(body)
        keys.append(key)
        if not dry_run:
            if client is None:
                raise ValueError("client is required when dry_run is false")
            client.put_object(Bucket=bucket, Key=key, Body=body)
    manifest = {
        "uploaded_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "bucket": bucket,
        "prefix": prefix,
        "n_files": len(keys),
        "total_bytes": total_bytes,
        "keys": keys,
    }
    (output_root / "upload_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return manifest


def main() -> None:
    """Upload ``outputs/`` with the repo S3 client."""
    parser = argparse.ArgumentParser(description="Upload Part 3 BERTopic outputs to S3.")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    output_root = EXPERIMENT_ROOT / "outputs"
    client = None
    if not args.dry_run:
        from lib.aws.s3 import S3

        store = S3(BUCKET, region_name="us-east-2")
        client = store._client
    manifest = upload_outputs(output_root, dry_run=args.dry_run, client=client)
    if client is not None:
        manifest_path = output_root / "upload_manifest.json"
        client.put_object(
            Bucket=BUCKET,
            Key=f"{PREFIX}/outputs/upload_manifest.json",
            Body=manifest_path.read_bytes(),
        )
    print(f"n_files={manifest['n_files']} total_bytes={manifest['total_bytes']}")


if __name__ == "__main__":
    main()
