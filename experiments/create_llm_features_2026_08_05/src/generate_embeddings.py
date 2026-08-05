"""Stage 2: embed Stage-1 feature texts with Amazon Titan via shared Bedrock helper.

Run from repo root::

    PYTHONPATH=. uv run python experiments/create_llm_features_2026_08_05/src/generate_embeddings.py \\
      --label-class keep \\
      --features-run-dir experiments/create_llm_features_2026_08_05/outputs/generated_features/keep/outputs/<TIMESTAMP>
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any

import numpy as np
from tqdm import tqdm

from experiments.create_llm_features_2026_08_05.src.paths import (
    LabelClass,
    latest_timestamp_subdir,
    stage1_root,
    stage2_root,
    validate_label_class,
)
from shared.embeddings.bedrock import (
    BEDROCK_MODEL_ID,
    EMBEDDING_DIMENSIONS,
    create_embedding,
)

_METADATA_FILENAME = "metadata.json"
FEATURE_ID_SCHEME = "batch_id_index_in_batch"
DEFAULT_LABEL_CLASS = LabelClass.KEEP.value


def _make_run_timestamp() -> str:
    """Return a local ISO-like timestamp for Stage-2 output folders."""
    return datetime.now().strftime("%Y-%m-%dT%H-%M-%S")


def resolve_features_run_dir(label_class: str, features_run_dir: str | None) -> Path:
    """Resolve Stage-1 run directory from an explicit path or the latest timestamp.

    Parameters
    ----------
    label_class
        keep or remove.
    features_run_dir
        Explicit Stage-1 timestamp directory, or None to pick latest.

    Returns
    -------
    Path
        Stage-1 run directory containing item JSON files.
    """
    if features_run_dir:
        path = Path(features_run_dir)
        if not path.is_dir():
            raise FileNotFoundError(f"features-run-dir not found: {path}")
        return path
    outputs_parent = stage1_root(label_class) / "outputs"
    return latest_timestamp_subdir(outputs_parent)


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
            records.append(
                {
                    "feature_id": feature_id,
                    "batch_id": batch_id,
                    "message_id": str(feature.get("message_id", "")),
                    "feature_name": str(feature.get("feature_name", "")),
                    "feature_value": str(feature.get("feature_value", "")),
                    "category": str(feature.get("category", "")),
                    "rationale": str(feature.get("rationale", "")),
                    "evidence_span": feature.get("evidence_span"),
                    "is_open_ended": feature.get("is_open_ended"),
                    "text_embedded": text_embedded,
                }
            )
    if not records:
        raise ValueError("No features found to embed in Stage-1 rows")
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
    """Embed each feature record via Bedrock Titan.

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
    label_class: str,
    source_features_run_dir: Path,
    embedded_records: list[dict[str, Any]],
    run_timestamp: str,
) -> Path:
    """Write Stage-2 metadata, JSONL, npy, and feature_ids sidecar.

    Parameters
    ----------
    label_class
        keep or remove.
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
    out_dir = stage2_root(label_class) / run_timestamp
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


def run_generate_embeddings(
    label_class: str,
    features_run_dir: str | None,
) -> Path:
    """Run Stage 2 for one label class and return the output directory.

    Parameters
    ----------
    label_class
        keep or remove.
    features_run_dir
        Explicit Stage-1 directory or None for latest.

    Returns
    -------
    Path
        Stage-2 run directory.
    """
    validate_label_class(label_class)
    source_dir = resolve_features_run_dir(label_class, features_run_dir)
    stage1_rows = load_stage1_feature_rows(source_dir)
    records = extract_features_for_embedding(stage1_rows)
    embedded = embed_feature_records(records)
    return write_embedding_artifacts(
        label_class,
        source_dir,
        embedded,
        _make_run_timestamp(),
    )


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse CLI arguments for Stage 2."""
    parser = argparse.ArgumentParser(
        description="Embed Stage-1 feature texts with Amazon Titan Text Embeddings V2."
    )
    parser.add_argument(
        "--label-class",
        required=True,
        choices=[LabelClass.KEEP.value, LabelClass.REMOVE.value],
    )
    parser.add_argument(
        "--features-run-dir",
        default=None,
        help="Stage-1 timestamp dir; defaults to latest under stage1_root/outputs/.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    """CLI entry: embed Stage-1 features for one label class."""
    args = parse_args(argv)
    out_dir = run_generate_embeddings(args.label_class, args.features_run_dir)
    print(f"Wrote Stage-2 embeddings to {out_dir}")


if __name__ == "__main__":
    main()
