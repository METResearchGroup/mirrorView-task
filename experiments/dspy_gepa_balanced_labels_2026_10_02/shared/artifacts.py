"""S3 storage for the balanced GEPA ablation.

Run from the repo root::

    PYTHONPATH=. uv run python experiments/dspy_gepa_balanced_labels_2026_10_02/src/step1_setup/main.py
"""

from __future__ import annotations

import hashlib
import json
from io import BytesIO
from typing import Any

import pandas as pd

from experiments.dspy_gepa_balanced_labels_2026_10_02.shared.config import (
    FINISHED_S3_PREFIX,
    INPUT_PREFIX,
    S3_BUCKET,
    S3_PREFIX,
    SPLIT_NAMES,
)
from experiments.dspy_gepa_balanced_labels_2026_10_02.shared.data import SAMPLING_METHOD, BalancedBundle
from experiments.dspy_gepa_optimization_2026_09_30.shared.data import EXCLUDELIST_POST_IDS
from experiments.dspy_gepa_optimization_2026_09_30.shared.telemetry import apply_lab_aws_credentials
from lib.aws.s3 import S3

MANIFEST_KEY = f"{INPUT_PREFIX}split_manifest.json"


def upload_inputs(bundle: BalancedBundle) -> dict[str, str]:
    """Upload the four splits and the manifest."""
    apply_lab_aws_credentials()
    store = _store()
    bodies = {name: parquet_bytes(bundle.splits[name]) for name in SPLIT_NAMES}
    manifest = {
        "sampling_method": SAMPLING_METHOD,
        "cohort_post_ids": list(bundle.cohort_ids),
        "eligible_count": bundle.eligible_count,
        "exclusion_ids": list(EXCLUDELIST_POST_IDS),
        "splits": {name: _split_record(bundle.splits[name], sha256_hex(bodies[name])) for name in SPLIT_NAMES},
    }
    objects = {**{split_key(name): bodies[name] for name in SPLIT_NAMES}, MANIFEST_KEY: manifest_bytes(manifest)}
    for key, body in objects.items():
        _reject_finished_prefix(key)
        _put_or_confirm(store, key, body)
    return {key: sha256_hex(body) for key, body in objects.items()}


def read_split(split_name: str) -> pd.DataFrame:
    """Download one prepared split."""
    apply_lab_aws_credentials()
    return pd.read_parquet(BytesIO(_store().get_bytes(split_key(split_name))))


def upload_run_bytes(run_id: str, relative_key: str, body: bytes) -> str:
    """Upload one immutable run object."""
    apply_lab_aws_credentials()
    key = f"{S3_PREFIX}runs/{run_id}/{relative_key}"
    _reject_finished_prefix(key)
    store = _store()
    if store.object_exists(key):
        if store.get_bytes(key) != body:
            raise ValueError(f"run object already exists with different bytes: {key}")
        return key
    store.upload_bytes(key, body, content_type=_content_type(key), metadata={"sha256": sha256_hex(body)})
    if store.get_bytes(key) != body:
        raise ValueError(f"read-after-write mismatch for {key}")
    return key


def read_run_json(run_id: str, relative_key: str) -> dict[str, Any]:
    """Download one JSON run object."""
    apply_lab_aws_credentials()
    key = f"{S3_PREFIX}runs/{run_id}/{relative_key}"
    _reject_finished_prefix(key)
    return json.loads(_store().get_bytes(key))


def run_object_exists(run_id: str, relative_key: str) -> bool:
    """Return whether one run object is already stored."""
    apply_lab_aws_credentials()
    key = f"{S3_PREFIX}runs/{run_id}/{relative_key}"
    _reject_finished_prefix(key)
    return _store().object_exists(key)


def parquet_bytes(frame: pd.DataFrame) -> bytes:
    """Serialize a frame to Parquet bytes."""
    buffer = BytesIO()
    frame.to_parquet(buffer, index=False)
    return buffer.getvalue()


def sha256_hex(body: bytes) -> str:
    """Return the hex SHA-256 digest of ``body``."""
    return hashlib.sha256(body).hexdigest()


def split_key(split_name: str) -> str:
    """Return the Parquet key for one split."""
    if split_name not in SPLIT_NAMES:
        raise ValueError(f"unknown split {split_name}")
    return f"{INPUT_PREFIX}{split_name}.parquet"


def manifest_bytes(document: dict[str, Any]) -> bytes:
    """Serialize a manifest with sorted keys."""
    return json.dumps(document, indent=2, sort_keys=True).encode()


def _split_record(frame: pd.DataFrame, digest: str) -> dict[str, Any]:
    labels = frame["keep_remove_label"].astype(int)
    return {
        "sha256": digest,
        "row_count": int(len(frame)),
        "keep_count": int(labels.eq(0).sum()),
        "remove_count": int(labels.eq(1).sum()),
        "post_ids": frame["post_id"].astype(str).tolist(),
    }


def _put_or_confirm(store: S3, key: str, body: bytes) -> None:
    if not store.object_exists(key):
        store.upload_bytes(key, body, content_type=_content_type(key), metadata={"sha256": sha256_hex(body)})
        return
    if store.get_bytes(key) != body:
        raise ValueError(f"existing object differs from the prepared bytes: {key}")


def _reject_finished_prefix(key: str) -> None:
    if key.startswith(FINISHED_S3_PREFIX):
        raise ValueError(f"refusing to touch the finished run prefix: {key}")


def _store() -> S3:
    return S3(S3_BUCKET, region_name="us-east-2")


def _content_type(key: str) -> str:
    if key.endswith(".json"):
        return "application/json"
    return "application/octet-stream"
