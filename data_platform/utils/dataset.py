from __future__ import annotations

import json
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from data_platform.constants import PACKAGE_ROOT

_DATA_ROOT = PACKAGE_ROOT / "data"

DATASET_ID_PATTERN = re.compile(
    r"^(bluesky|reddit|twitter)_[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$"
)
MANIFEST_FILENAME = "dataset.json"


def validate_dataset_id(dataset_id: str) -> str:
    if not DATASET_ID_PATTERN.match(dataset_id):
        raise ValueError(
            "dataset_id must match {platform}_{uuid} where platform is bluesky, reddit, or twitter "
            "(lowercase RFC 4122 hex with hyphens)"
        )
    return dataset_id


def dataset_root(platform: str, dataset_id: str) -> Path:
    dataset_id = validate_dataset_id(dataset_id)
    expected_prefix = dataset_id.split("_", 1)[0]
    if platform != expected_prefix:
        raise ValueError(
            f"platform {platform!r} does not match dataset_id prefix {expected_prefix!r}"
        )
    return _DATA_ROOT / platform / dataset_id


def relative_run_path(dataset_root_path: Path, run_dir: Path) -> str:
    return str(run_dir.relative_to(dataset_root_path))


def load_dataset_manifest(platform: str, dataset_id: str) -> dict[str, Any]:
    path = dataset_root(platform, dataset_id) / MANIFEST_FILENAME
    if not path.exists():
        raise FileNotFoundError(f"Dataset manifest not found: {path}")
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def write_dataset_manifest(
    platform: str,
    dataset_id: str,
    *,
    name: str,
    ingestion_config: str,
    created_at: str | None = None,
) -> Path:
    root = dataset_root(platform, dataset_id)
    root.mkdir(parents=True, exist_ok=True)
    manifest = {
        "dataset_id": validate_dataset_id(dataset_id),
        "platform": platform,
        "name": name,
        "created_at": created_at or datetime.now(UTC).isoformat(),
        "ingestion_config": ingestion_config,
    }
    path = root / MANIFEST_FILENAME
    with path.open("w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)
    return path
