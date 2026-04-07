"""Verify S3 objects exist for a staged release manifest and critical runtime keys."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

from scripts.upload_to_s3.constants import (
    AWS_REGION,
    CRITICAL_S3_KEYS,
    STAGING_ROOT,
    TARGET_BUCKET,
)


def _head_object(key: str) -> tuple[bool, str]:
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
    if proc.returncode == 0:
        return True, ""
    err = (proc.stderr or proc.stdout or "").strip()
    return False, err


def resolve_latest_release_dir(staging_root: Path) -> Path:
    if not staging_root.is_dir():
        raise SystemExit(f"No staging root {staging_root}; run the uploader first.")
    candidates = [p for p in staging_root.iterdir() if p.is_dir()]
    if not candidates:
        raise SystemExit(f"No release directories under {staging_root}.")
    latest = sorted(candidates, key=lambda p: p.name)[-1]
    return latest


def load_manifest(release_dir: Path) -> dict[str, Any]:
    path = release_dir / "manifest.json"
    if not path.is_file():
        raise SystemExit(f"Missing manifest: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def verify_required_keys(manifest: dict[str, Any]) -> list[str]:
    missing: list[str] = []
    for key in manifest.get("files", []):
        ok, err = _head_object(key)
        if not ok:
            missing.append(f"{key} ({err or 'not found'})")
    return missing


def verify_critical_keys_exist() -> list[str]:
    missing: list[str] = []
    for key in CRITICAL_S3_KEYS:
        ok, err = _head_object(key)
        if not ok:
            missing.append(f"{key} ({err or 'not found'})")
    return missing


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Verify uploaded S3 keys for a release (manifest + critical paths)."
    )
    parser.add_argument(
        "--release-dir",
        type=Path,
        default=None,
        help="Staged release directory (default: latest under s3_upload/).",
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
    print(f"Verifying manifest from {release_dir}")
    problems: list[str] = []

    m_missing = verify_required_keys(manifest)
    if m_missing:
        problems.append("Manifest keys missing in S3:")
        problems.extend(f"  - {m}" for m in m_missing)

    c_missing = verify_critical_keys_exist()
    if c_missing:
        problems.append("Critical keys missing in S3:")
        problems.extend(f"  - {m}" for m in c_missing)

    if problems:
        print("\n".join(problems), file=sys.stderr)
        raise SystemExit(1)

    print(
        f"OK: all {len(manifest.get('files', []))} manifest files and "
        f"{len(CRITICAL_S3_KEYS)} critical keys are present in s3://{TARGET_BUCKET}/"
    )


if __name__ == "__main__":
    main()
