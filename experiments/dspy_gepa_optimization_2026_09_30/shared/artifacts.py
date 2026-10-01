"""S3 artifacts for the DSPy GEPA experiment.

Run from the repo root::

    PYTHONPATH=. uv run python experiments/dspy_gepa_optimization_2026_09_30/src/step1_setup/main.py
"""

from __future__ import annotations

import hashlib
import json
from io import BytesIO
from typing import Any

import pandas as pd

from experiments.dspy_gepa_optimization_2026_09_30.shared.config import (
    INPUT_PREFIX,
    KEEP_LABEL,
    RANDOM_SEED,
    REMOVE_LABEL,
    S3_BUCKET,
    SPLIT_NAMES,
)
from experiments.dspy_gepa_optimization_2026_09_30.shared.data import (
    EXCLUDELIST_POST_IDS,
    SAMPLING_METHOD,
    SplitBundle,
    source_dataset_name,
    source_dataset_path,
)
from experiments.dspy_gepa_optimization_2026_09_30.shared.telemetry import apply_lab_aws_credentials
from lib.aws.s3 import S3

MANIFEST_KEY = f"{INPUT_PREFIX}split_manifest.json"


def split_key(split_name: str) -> str:
    """Return the input Parquet key for one split."""
    if split_name not in SPLIT_NAMES:
        raise ValueError(f"unknown split {split_name}")
    return f"{INPUT_PREFIX}{split_name}.parquet"


def sha256_hex(body: bytes) -> str:
    """Return the hex SHA-256 digest of ``body``."""
    return hashlib.sha256(body).hexdigest()


def parquet_bytes(frame: pd.DataFrame) -> bytes:
    """Serialize a frame to Parquet bytes in its current row order."""
    buffer = BytesIO()
    frame.to_parquet(buffer, index=False)
    return buffer.getvalue()


def build_manifest(bundle: SplitBundle, split_hashes: dict[str, str]) -> dict[str, Any]:
    """Return the split manifest for the prepared bundle."""
    return {
        "dataset_name": source_dataset_name(),
        "dataset_path": source_dataset_path(),
        "source_count": bundle.source_count,
        "eligible_count": int(len(bundle.eligible)),
        "exclusion_ids": list(EXCLUDELIST_POST_IDS),
        "seed": RANDOM_SEED,
        "sampling_method": SAMPLING_METHOD,
        "cohort_post_ids": list(bundle.cohort_ids),
        "cohort_sha256": sha256_hex("\n".join(bundle.cohort_ids).encode()),
        "splits": {
            name: _split_record(bundle.splits[name], split_hashes[name], split_key(name))
            for name in SPLIT_NAMES
        },
    }


def manifest_bytes(manifest: dict[str, Any]) -> bytes:
    """Serialize a manifest with sorted keys."""
    return json.dumps(manifest, indent=2, sort_keys=True).encode()


def upload_inputs(bundle: SplitBundle) -> dict[str, str]:
    """Upload the four splits and manifest, reusing identical existing bytes."""
    apply_lab_aws_credentials()
    store = S3(S3_BUCKET, region_name="us-east-2")
    bodies = {name: parquet_bytes(bundle.splits[name]) for name in SPLIT_NAMES}
    hashes = {name: sha256_hex(body) for name, body in bodies.items()}
    manifest = manifest_bytes(build_manifest(bundle, hashes))
    objects = {**{split_key(name): bodies[name] for name in SPLIT_NAMES}, MANIFEST_KEY: manifest}
    for key, body in objects.items():
        _put_or_confirm(store, key, body)
    _read_back(store, objects)
    return {key: sha256_hex(body) for key, body in objects.items()}


def read_manifest() -> dict[str, Any]:
    """Download and parse the split manifest."""
    apply_lab_aws_credentials()
    body = S3(S3_BUCKET, region_name="us-east-2").get_bytes(MANIFEST_KEY)
    payload = json.loads(body)
    if not isinstance(payload, dict):
        raise ValueError("split manifest must be a JSON object")
    return payload


def read_split(split_name: str) -> pd.DataFrame:
    """Download one prepared split."""
    apply_lab_aws_credentials()
    body = S3(S3_BUCKET, region_name="us-east-2").get_bytes(split_key(split_name))
    return pd.read_parquet(BytesIO(body))


def _split_record(frame: pd.DataFrame, digest: str, key: str) -> dict[str, Any]:
    labels = frame["keep_remove_label"].astype(int)
    stances = frame["sampled_stance"].astype(str)
    return {
        "key": key,
        "sha256": digest,
        "post_ids": frame["post_id"].astype(str).tolist(),
        "row_count": int(len(frame)),
        "keep_count": int(labels.eq(KEEP_LABEL).sum()),
        "remove_count": int(labels.eq(REMOVE_LABEL).sum()),
        "stance_counts": {str(name): int(count) for name, count in stances.value_counts().sort_index().items()},
    }


def _put_or_confirm(store: S3, key: str, body: bytes) -> None:
    if not store.object_exists(key):
        store.upload_bytes(key, body, content_type=_content_type(key), metadata={"sha256": sha256_hex(body)})
        return
    existing = store.get_bytes(key)
    if existing != body:
        raise ValueError(f"existing object differs from the prepared bytes: {key}")


def _read_back(store: S3, objects: dict[str, bytes]) -> None:
    for key, body in objects.items():
        downloaded = store.get_bytes(key)
        if downloaded != body:
            raise ValueError(f"read-after-write mismatch for {key}")


def _content_type(key: str) -> str:
    if key.endswith(".json"):
        return "application/json"
    return "application/octet-stream"
