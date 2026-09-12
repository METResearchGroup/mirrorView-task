"""Mirrored S3 path helpers and cohort upload."""

from __future__ import annotations

from dataclasses import dataclass

from data_platform.generate_features.s3_feature_campaign import CampaignObjectStore
from experiments.ai_simulation_responses_2026_09_11.shared.constants import (
    CohortTrial,
    CohortUser,
)


@dataclass(frozen=True)
class CohortUploadResult:
    """S3 URIs and digests from one cohort upload."""

    users_s3_uri: str
    trials_s3_uri: str
    users_sha256: str
    trials_sha256: str


def mirrored_s3_key(relative_path: str) -> str:
    """Return the S3 object key equal to the repo-relative path."""
    raise NotImplementedError


def put_new_mirrored(
    store: CampaignObjectStore,
    relative_path: str,
    body: bytes,
) -> str:
    """Write local bytes then upload with put_new."""
    raise NotImplementedError


def upload_cohort(
    users: tuple[CohortUser, ...],
    trials: tuple[CohortTrial, ...],
    store: CampaignObjectStore,
) -> CohortUploadResult:
    """Write cohort parquet locally and on S3."""
    raise NotImplementedError


def require_cohort_keys_absent(store: CampaignObjectStore) -> None:
    """Raise FileExistsError when cohort keys already exist."""
    raise NotImplementedError
