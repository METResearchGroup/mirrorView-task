"""S3 key helpers, serialization, and immutable writes for the experiment.

Run from repo root::

    PYTHONPATH=. uv run python -m experiments.zero_shot_llm_inference_2026_09_30.src.step1_setup.prepare
"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING, Any

from experiments.zero_shot_llm_inference_2026_09_30.shared.schemas import Study2InputRecord

if TYPE_CHECKING:
    from data_platform.generate_features.s3_feature_campaign import CampaignObjectStore


def apply_lab_aws_credentials_when_unset() -> None:
    """Copy lab AWS env vars into standard names when those are empty.

    Raises
    ------
    ValueError
        Never raised; invalid env values are ignored like empty strings.
    """
    raise NotImplementedError


def validate_path_segment(segment: str) -> str:
    """Return ``segment`` when it is one safe path component.

    Raises
    ------
    ValueError
        When the segment is empty, unsafe, or contains slashes.
    """
    raise NotImplementedError


def join_experiment_key(*segments: str) -> str:
    """Join path segments below the fixed experiment S3 root.

    Raises
    ------
    ValueError
        When any segment fails validation or the key escapes the root.
    """
    raise NotImplementedError


def build_model_run_prefix(run_id: str, model_folder: str) -> str:
    """Return the S3 prefix for one model folder under a run.

    Raises
    ------
    ValueError
        When ``run_id`` or ``model_folder`` is not a safe segment.
    """
    raise NotImplementedError


def sha256_hex(data: bytes) -> str:
    """Return the SHA-256 hex digest of ``data``."""
    raise NotImplementedError


def serialize_json_document(value: dict[str, Any]) -> bytes:
    """Serialize one JSON object as compact UTF-8 bytes with a final newline."""
    raise NotImplementedError


def serialize_study2_input_jsonl(records: list[Study2InputRecord]) -> bytes:
    """Serialize prepared records as sorted-key JSONL with a final newline."""
    raise NotImplementedError


def put_immutable_object(
    store: CampaignObjectStore,
    key: str,
    body: bytes,
) -> None:
    """Create one object with ``put_new`` and no overwrite behavior.

    Raises
    ------
    FileExistsError
        When the object key already exists in the store.
    """
    raise NotImplementedError


def object_exists(store: CampaignObjectStore, key: str) -> bool:
    """Return whether ``key`` is already present in the store."""
    raise NotImplementedError
