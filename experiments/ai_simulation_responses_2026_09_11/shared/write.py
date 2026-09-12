"""Mirrored S3 path helpers and cohort upload."""

from __future__ import annotations

import io
from dataclasses import asdict
from dataclasses import dataclass

import pandas as pd

from data_platform.generate_features.s3_feature_campaign import (
    CampaignObjectStore,
    s3_uri,
)
from data_platform.utils.object_store import sha256_hex
from experiments.ai_simulation_responses_2026_09_11.shared.constants import (
    COHORT_TRIALS_KEY,
    COHORT_USERS_KEY,
    EXPERIMENT_S3_PREFIX,
    OUTPUT_S3_BUCKET,
    CohortTrial,
    CohortUser,
)
from lib.constants import REPO_ROOT

LEGACY_FINETUNE_PREFIX = "mirrorview-finetune_qwen_model_2026_08_08/"


@dataclass(frozen=True)
class CohortUploadResult:
    """S3 URIs and digests from one cohort upload."""

    users_s3_uri: str
    trials_s3_uri: str
    users_sha256: str
    trials_sha256: str


def mirrored_s3_key(relative_path: str) -> str:
    """Return the S3 object key equal to the repo-relative path."""
    if relative_path.startswith("/"):
        raise ValueError(f"relative path must not start with '/': {relative_path}")
    if relative_path.startswith(LEGACY_FINETUNE_PREFIX):
        raise ValueError(f"legacy finetune prefix is forbidden: {relative_path}")
    if not relative_path.startswith(EXPERIMENT_S3_PREFIX):
        raise ValueError(
            f"relative path must start with {EXPERIMENT_S3_PREFIX!r}: {relative_path}"
        )
    return relative_path


def put_new_mirrored(
    store: CampaignObjectStore,
    relative_path: str,
    body: bytes,
) -> str:
    """Write local bytes then upload with put_new."""
    key = mirrored_s3_key(relative_path)
    local_path = REPO_ROOT / key
    local_path.parent.mkdir(parents=True, exist_ok=True)
    local_path.write_bytes(body)
    store.put_new(key, body)
    return sha256_hex(body)


def upload_cohort(
    users: tuple[CohortUser, ...],
    trials: tuple[CohortTrial, ...],
    store: CampaignObjectStore,
) -> CohortUploadResult:
    """Write cohort parquet locally and on S3."""
    users_body = _users_parquet_bytes(users)
    trials_body = _trials_parquet_bytes(trials)
    users_sha256 = put_new_mirrored(store, COHORT_USERS_KEY, users_body)
    trials_sha256 = put_new_mirrored(store, COHORT_TRIALS_KEY, trials_body)
    return CohortUploadResult(
        users_s3_uri=s3_uri(OUTPUT_S3_BUCKET, COHORT_USERS_KEY),
        trials_s3_uri=s3_uri(OUTPUT_S3_BUCKET, COHORT_TRIALS_KEY),
        users_sha256=users_sha256,
        trials_sha256=trials_sha256,
    )


def require_cohort_keys_absent(store: CampaignObjectStore) -> None:
    """Raise FileExistsError when cohort keys already exist."""
    for key in (COHORT_USERS_KEY, COHORT_TRIALS_KEY):
        if store.get(key) is not None:
            raise FileExistsError(f"Object already exists: {s3_uri(OUTPUT_S3_BUCKET, key)}")


def _users_parquet_bytes(users: tuple[CohortUser, ...]) -> bytes:
    rows = [asdict(user) for user in users]
    return _parquet_bytes(pd.DataFrame(rows))


def _trials_parquet_bytes(trials: tuple[CohortTrial, ...]) -> bytes:
    rows = [asdict(trial) for trial in trials]
    frame = pd.DataFrame(rows)
    frame["pair_order"] = frame["pair_order"].map(list)
    return _parquet_bytes(frame)


def _parquet_bytes(frame: pd.DataFrame) -> bytes:
    buffer = io.BytesIO()
    frame.to_parquet(buffer, index=False)
    return buffer.getvalue()
