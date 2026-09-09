"""Upload party assignment files and batch config to the September study bucket.

Run from the repo root:

    PYTHONPATH=. uv run python experiments/load_study_assignments_2026_09_09/upload.py
"""

from __future__ import annotations

import sys
from pathlib import Path

from data_platform.generate_features.s3_feature_campaign import (
    CampaignObjectStore,
    s3_uri,
)
from experiments.load_study_assignments_2026_09_09.constants import (
    ASSIGNMENT_PREFIX,
    ASSIGNMENTS_FILENAME,
    BATCH_DIRNAME,
    CONDITION,
    CONFIG_FILENAME,
    EXPERIMENT_DIRNAME,
    PARTY_DEMOCRAT,
    PARTY_REPUBLICAN,
    STUDY_BUCKET,
)
from lib.constants import REPO_ROOT
from lib.timestamp_utils import get_current_timestamp


def main() -> int:
    """Upload config.yaml and both party CSVs under a timestamped prefix."""
    timestamp = get_current_timestamp()
    store = CampaignObjectStore(STUDY_BUCKET)
    keys = _upload_batch(store, _batch_dir(), timestamp)
    _print_upload(keys, timestamp)
    return 0


def _upload_batch(
    store: CampaignObjectStore, batch_dir: Path, timestamp: str
) -> list[str]:
    keys = [_batch_key(timestamp, relative) for relative in _relative_paths()]
    for relative, key in zip(_relative_paths(), keys):
        store.put_new(key, (batch_dir / relative).read_bytes())
    return keys


def _print_upload(keys: list[str], timestamp: str) -> None:
    for key in keys:
        print(s3_uri(STUDY_BUCKET, key))
    print(f"batch_uri={s3_uri(STUDY_BUCKET, f'{ASSIGNMENT_PREFIX}/{timestamp}')}")


def _relative_paths() -> tuple[str, ...]:
    return (
        CONFIG_FILENAME,
        f"{PARTY_DEMOCRAT}/{CONDITION}/{ASSIGNMENTS_FILENAME}",
        f"{PARTY_REPUBLICAN}/{CONDITION}/{ASSIGNMENTS_FILENAME}",
    )


def _batch_key(timestamp: str, relative: str) -> str:
    return f"{ASSIGNMENT_PREFIX}/{timestamp}/{relative}"


def _batch_dir() -> Path:
    return REPO_ROOT / "experiments" / EXPERIMENT_DIRNAME / BATCH_DIRNAME


if __name__ == "__main__":
    sys.exit(main())
