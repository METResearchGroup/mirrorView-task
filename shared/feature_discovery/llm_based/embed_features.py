"""Stage 2: flatten Stage-1 features and embed with Amazon Titan.

Path-parameterized helpers with no experiment imports. Callers supply
``output_root`` and label/group identifiers.

Run from repo root::

    PYTHONPATH=. uv run python -c "
    from shared.feature_discovery.llm_based import embed_features
    assert hasattr(embed_features, 'build_feature_embed_text')
    print('embed_features OK')
    "
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
from tqdm import tqdm

from shared.embeddings.bedrock import (
    BEDROCK_MODEL_ID,
    EMBEDDING_DIMENSIONS,
    create_embedding,
)

_METADATA_FILENAME = "metadata.json"
FEATURE_ID_SCHEME = "batch_id_index_in_batch"
_PROVENANCE_ID_KEYS = ("participant_id", "message_id")


def load_stage1_feature_rows(features_run_dir: Path) -> list[dict[str, Any]]:
    """Load Stage-1 result JSON files, skipping metadata.json.

    Parameters
    ----------
    features_run_dir
        Timestamped Stage-1 output directory.

    Returns
    -------
    list[dict[str, Any]]
        Parsed Stage-1 row payloads.

    Raises
    ------
    FileNotFoundError
        When the directory does not exist.
    ValueError
        When no result JSON files are found.
    """
    if not features_run_dir.is_dir():
        raise FileNotFoundError(f"Stage-1 directory not found: {features_run_dir}")

    rows: list[dict[str, Any]] = []
    for path in sorted(features_run_dir.glob("*.json")):
        if path.name == _METADATA_FILENAME:
            continue
        rows.append(json.loads(path.read_text(encoding="utf-8")))
    if not rows:
        raise ValueError(f"No Stage-1 result JSON files found in {features_run_dir}")
    return rows


def build_feature_embed_text(feature: dict[str, Any]) -> str:
    """Build the Titan input string for one extracted feature.

    Parameters
    ----------
    feature
        Stage-1 feature dict with name, value, and rationale.

    Returns
    -------
    str
        ``{feature_name}: {feature_value}. {rationale}``

    Raises
    ------
    ValueError
        When the resulting string is empty after strip.
    """
    text = (
        f"{feature.get('feature_name', '')}: "
        f"{feature.get('feature_value', '')}. "
        f"{feature.get('rationale', '')}"
    ).strip()
    if not text:
        raise ValueError("Empty embedding text after strip for feature")
    return text


def _provenance_fields(feature: dict[str, Any]) -> dict[str, str]:
    """Return participant_id and/or message_id when present on the feature."""
    fields: dict[str, str] = {}
    for key in _PROVENANCE_ID_KEYS:
        if key in feature and feature[key] is not None:
            fields[key] = str(feature[key])
    return fields


def extract_features_for_embedding(
    stage1_rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Flatten Stage-1 features into embedding-ready records with stable ids.

    Parameters
    ----------
    stage1_rows
        Stage-1 runner output rows.

    Returns
    -------
    list[dict[str, Any]]
        Records with feature_id, provenance fields, and text_embedded.

    Raises
    ------
    ValueError
        When zero features remain after flatten (empty Stage-1 or all QA-rejected).
    """
    records: list[dict[str, Any]] = []
    for row in stage1_rows:
        batch_id = row.get("batch_id")
        features = row.get("result", {}).get("features") or []
        if not features:
            continue
        for index_in_batch, feature in enumerate(features):
            text_embedded = build_feature_embed_text(feature)
            feature_id = f"{batch_id}_{index_in_batch}"
            record: dict[str, Any] = {
                "feature_id": feature_id,
                "batch_id": batch_id,
                "feature_name": str(feature.get("feature_name", "")),
                "feature_value": str(feature.get("feature_value", "")),
                "category": str(feature.get("category", "")),
                "rationale": str(feature.get("rationale", "")),
                "evidence_span": feature.get("evidence_span"),
                "is_open_ended": feature.get("is_open_ended"),
                "text_embedded": text_embedded,
            }
            record.update(_provenance_fields(feature))
            records.append(record)
    if not records:
        raise ValueError(
            "No features found to embed in Stage-1 rows "
            "(empty Stage-1 or all batches QA-rejected)"
        )
    return records


def _embed_one_record(record: dict[str, Any]) -> dict[str, Any]:
    """Call Titan and attach embedding fields to one feature record."""
    out = create_embedding(record["text_embedded"])
    if out["model_id"] != BEDROCK_MODEL_ID:
        raise ValueError(f"Unexpected model_id: {out['model_id']}")
    if out["dimensions"] != EMBEDDING_DIMENSIONS:
        raise ValueError(f"Unexpected dimensions: {out['dimensions']}")
    if out["normalize"] is not True:
        raise ValueError("Expected normalize=True from create_embedding")
    if len(out["embedding"]) != EMBEDDING_DIMENSIONS:
        raise ValueError(f"Expected embedding length {EMBEDDING_DIMENSIONS}")
    return {
        **record,
        "embedding": out["embedding"],
        "input_text_token_count": out.get("input_text_token_count"),
        "model_id": out["model_id"],
        "dimensions": out["dimensions"],
        "normalize": out["normalize"],
    }


def embed_feature_records(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Embed each feature record via Bedrock Titan with defaults.

    Parameters
    ----------
    records
        Flattened feature records with ``text_embedded``.

    Returns
    -------
    list[dict[str, Any]]
        Records with embedding vectors attached.
    """
    embedded: list[dict[str, Any]] = []
    for record in tqdm(records, desc="Stage 2 embeddings"):
        embedded.append(_embed_one_record(record))
    return embedded


def write_embedding_artifacts(
    output_root: Path,
    label_class: str,
    source_features_run_dir: Path,
    embedded_records: list[dict[str, Any]],
    run_timestamp: str,
) -> Path:
    """Write Stage-2 metadata, JSONL, npy, and feature_ids sidecar.

    Parameters
    ----------
    output_root
        Class/group Stage-2 root; artifacts go under ``output_root / run_timestamp``.
    label_class
        Class or Likert-group label stored in metadata.
    source_features_run_dir
        Stage-1 run directory used as input.
    embedded_records
        Features with embeddings.
    run_timestamp
        Output folder name.

    Returns
    -------
    Path
        Stage-2 run directory.
    """
    out_dir = output_root / run_timestamp
    out_dir.mkdir(parents=True, exist_ok=True)

    matrix = np.asarray(
        [record["embedding"] for record in embedded_records],
        dtype=np.float64,
    )
    feature_ids = [record["feature_id"] for record in embedded_records]
    np.save(out_dir / "embeddings.npy", matrix)
    (out_dir / "feature_ids.json").write_text(
        json.dumps(feature_ids, indent=2),
        encoding="utf-8",
    )

    with (out_dir / "features.jsonl").open("w", encoding="utf-8") as handle:
        for record in embedded_records:
            handle.write(json.dumps(record) + "\n")

    metadata = {
        "label_class": label_class,
        "source_features_run_dir": str(source_features_run_dir),
        "model_id": BEDROCK_MODEL_ID,
        "dimensions": EMBEDDING_DIMENSIONS,
        "normalize": True,
        "n_features": len(embedded_records),
        "feature_id_scheme": FEATURE_ID_SCHEME,
        "primary_format": "features.jsonl + embeddings.npy + feature_ids.json",
    }
    (out_dir / _METADATA_FILENAME).write_text(
        json.dumps(metadata, indent=2),
        encoding="utf-8",
    )
    return out_dir


def run_embed_features(
    output_root: Path,
    label_class: str,
    features_run_dir: Path,
    run_timestamp: str,
) -> Path:
    """Load Stage-1 features, embed, and write Stage-2 artifacts.

    Parameters
    ----------
    output_root
        Class/group Stage-2 root directory.
    label_class
        Class or Likert-group label for metadata.
    features_run_dir
        Stage-1 timestamp directory.
    run_timestamp
        Output folder name under ``output_root``.

    Returns
    -------
    Path
        Stage-2 run directory.
    """
    stage1_rows = load_stage1_feature_rows(features_run_dir)
    records = extract_features_for_embedding(stage1_rows)
    embedded = embed_feature_records(records)
    return write_embedding_artifacts(
        output_root=output_root,
        label_class=label_class,
        source_features_run_dir=features_run_dir,
        embedded_records=embedded,
        run_timestamp=run_timestamp,
    )
