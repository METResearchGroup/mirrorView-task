"""Upload experiment artifacts to S3.

Run from the repo root::

    PYTHONPATH=. uv run python -m experiments.llm_feature_generation_phase_2_part_3_2026_09_24.src.s3_sync \\
      --paths data/post_split outputs/original_only/cohort
"""

from __future__ import annotations

import argparse
from pathlib import Path

from lib.aws.s3 import S3

from experiments.llm_feature_generation_phase_2_part_3_2026_09_24.src import constants, paths


def s3_key_for_local(local_path: Path) -> str:
    """Map a local experiment path to an S3 object key."""
    resolved = local_path.resolve()
    relative = resolved.relative_to(paths.EXPERIMENT_ROOT.resolve())
    return f"{constants.S3_PREFIX}{relative.as_posix()}"


def collect_files(path: Path) -> list[Path]:
    """Return files under a path when it is a directory."""
    if path.is_file():
        return [path]
    if not path.is_dir():
        return []
    return sorted(
        file_path
        for file_path in path.rglob("*")
        if file_path.is_file()
    )


def upload_paths(paths_to_upload: list[Path], s3_client: S3) -> list[str]:
    """Upload each file under the given paths and return uploaded keys."""
    uploaded: list[str] = []
    for raw_path in paths_to_upload:
        local_path = _resolve_local_path(raw_path)
        if not local_path.exists():
            print(f"warning: missing path {local_path}")
            continue
        for file_path in collect_files(local_path):
            key = s3_key_for_local(file_path)
            s3_client.upload_file(file_path, key)
            uploaded.append(key)
    return uploaded


def main() -> None:
    """Parse CLI args and upload the requested paths."""
    args = _parse_args()
    local_paths = [_resolve_local_path(Path(value)) for value in args.paths]
    s3_client = S3(constants.S3_BUCKET)
    uploaded = upload_paths(local_paths, s3_client)
    prefix = f"s3://{constants.S3_BUCKET}/{constants.S3_PREFIX}"
    print(f"s3_uploaded_prefix={prefix}")
    print(f"n_uploaded={len(uploaded)}")


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Upload experiment artifacts to S3.")
    parser.add_argument("--paths", nargs="+", required=True)
    return parser.parse_args()


def _resolve_local_path(raw_path: Path) -> Path:
    if raw_path.is_absolute():
        return raw_path
    return paths.EXPERIMENT_ROOT / raw_path


if __name__ == "__main__":
    main()
