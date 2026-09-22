"""Download and upload experiment artifacts under the experimental S3 prefix.

Run from the repo root:

    PYTHONPATH=. uv run python experiments/reasoning_during_moderation_2026_09_15/shared/cohort.py --write-counts
"""

from __future__ import annotations

from pathlib import Path

from data_platform.generate_features.s3_feature_campaign import CampaignObjectStore
from experiments.reasoning_during_moderation_2026_09_15.shared.constants import (
    OUTPUT_S3_BUCKET,
)
from lib.constants import REPO_ROOT


def download_if_missing(path: Path, key: str) -> None:
    """Write ``key`` from S3 when the local file is absent."""
    if path.is_file():
        return
    store = CampaignObjectStore(OUTPUT_S3_BUCKET)
    stored = store.get(key)
    if stored is None:
        raise FileNotFoundError(key)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(stored.body)


def upload_under_prefix(path: Path, allowed_prefix: str) -> None:
    """Upload ``path`` with put_new when absent, else replace. Refuse other prefixes."""
    key = str(path.relative_to(REPO_ROOT))
    if not key.startswith(allowed_prefix):
        raise ValueError(f"refusing S3 key outside {allowed_prefix}: {key}")
    store = CampaignObjectStore(OUTPUT_S3_BUCKET)
    body = path.read_bytes()
    existing = store.get(key)
    if existing is None:
        store.put_new(key, body)
        return
    store.replace(key, body, etag=existing.etag)
