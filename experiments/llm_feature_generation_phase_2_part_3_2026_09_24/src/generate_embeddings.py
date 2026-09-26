"""Flatten discovery features and embed with Amazon Titan (Bedrock).

Run from the repo root::

    PYTHONPATH=. uv run python -m \\
        experiments.llm_feature_generation_phase_2_part_3_2026_09_24.src.generate_embeddings \\
        --arm original_only
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any

import numpy as np
from tqdm import tqdm

from experiments.llm_feature_generation_phase_2_part_3_2026_09_24.src import constants, paths
from shared.embeddings.bedrock import BEDROCK_MODEL_ID, EMBEDDING_DIMENSIONS, create_embedding

METADATA_FILENAME = constants.METADATA_FILENAME
RUN_TIMESTAMP_FORMAT = constants.RUN_TIMESTAMP_FORMAT
TOPUP_BATCH_DESIGN = constants.BATCH_DESIGN_MIXED_TOPUP
MIXED_BATCH_DESIGN = constants.BATCH_DESIGN_MIXED


def make_run_timestamp() -> str:
    """Return a local timestamp folder name for normalize embed outputs."""
    return datetime.now().strftime(RUN_TIMESTAMP_FORMAT)


def resolve_discovery_run_dir(arm: str, discovery_run_dir: str | None) -> Path:
    """Resolve the main mixed discovery run directory for one arm."""
    if discovery_run_dir:
        path = Path(discovery_run_dir)
        if not path.is_dir():
            raise FileNotFoundError(f"discovery-run-dir not found: {path}")
        return path
    return _latest_discovery_run_for_batch_design(arm, MIXED_BATCH_DESIGN)


def resolve_topup_run_dir(arm: str, topup_run_dir: str | None) -> Path:
    """Resolve the mixed_topup discovery run directory for one arm."""
    if topup_run_dir:
        path = Path(topup_run_dir)
        if not path.is_dir():
            raise FileNotFoundError(f"topup-run-dir not found: {path}")
        return path
    return _latest_discovery_run_for_batch_design(arm, TOPUP_BATCH_DESIGN)


def _latest_discovery_run_for_batch_design(arm: str, batch_design: str) -> Path:
    parent = paths.discovery_run_dir(arm)
    if not parent.is_dir():
        raise FileNotFoundError(f"Directory not found: {parent}")
    matches: list[Path] = []
    for child in parent.iterdir():
        if not child.is_dir():
            continue
        metadata_path = child / METADATA_FILENAME
        if not metadata_path.is_file():
            continue
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        run_meta = metadata.get("run_metadata", metadata)
        if run_meta.get("batch_design") == batch_design:
            matches.append(child)
    if not matches:
        raise FileNotFoundError(
            f"No discovery run with batch_design={batch_design} under {parent}"
        )
    return sorted(matches, key=lambda path: path.name)[-1]


def load_discovery_feature_rows(
    discovery_run_dir: Path,
    topup_run_dir: Path | None = None,
) -> list[dict[str, Any]]:
    """Load discovery_row payloads from mixed and optional mixed_topup runs."""
    rows = _load_discovery_rows_from_run(discovery_run_dir)
    if topup_run_dir is not None:
        rows.extend(_load_discovery_rows_from_run(topup_run_dir))
    if not rows:
        raise ValueError(f"No discovery rows under {discovery_run_dir}")
    return rows


def _load_discovery_rows_from_run(run_dir: Path) -> list[dict[str, Any]]:
    if not run_dir.is_dir():
        raise FileNotFoundError(f"Discovery run not found: {run_dir}")
    rows: list[dict[str, Any]] = []
    for path in sorted(run_dir.glob("*.json")):
        if path.name == METADATA_FILENAME:
            continue
        payload = json.loads(path.read_text(encoding="utf-8"))
        discovery_row = payload.get("discovery_row")
        if not isinstance(discovery_row, dict):
            raise ValueError(f"Missing discovery_row in {path}")
        rows.append(discovery_row)
    return rows


def build_feature_embed_text(feature: dict[str, Any]) -> str:
    """Build Titan input text for one feature record."""
    text = (
        f"{feature.get('feature_name', '')}: "
        f"{feature.get('feature_value', '')}. "
        f"{feature.get('rationale', '')}"
    ).strip()
    if not text:
        raise ValueError("Empty embedding text after strip for feature")
    return text


def flatten_discovery_to_features(
    discovery_rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Flatten discovery rows into one embedding-ready record per feature."""
    records: list[dict[str, Any]] = []
    for row in discovery_rows:
        batch_id = row["batch_id"]
        batch_design = str(row.get("batch_design", MIXED_BATCH_DESIGN))
        prefix = "topup" if batch_design == TOPUP_BATCH_DESIGN else "mixed"
        result = row.get("result") or {}
        records.extend(
            _features_from_side(
                result.get("keep_features") or [],
                batch_id,
                prefix,
                constants.DECISION_KEEP,
            )
        )
        records.extend(
            _features_from_side(
                result.get("remove_features") or [],
                batch_id,
                prefix,
                constants.DECISION_REMOVE,
            )
        )
    if not records:
        raise ValueError("No features found in discovery rows")
    return records


def _features_from_side(
    features: list[dict[str, Any]],
    batch_id: int,
    prefix: str,
    label_class: str,
) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for index_in_batch, feature in enumerate(features):
        text_embedded = build_feature_embed_text(feature)
        feature_id = f"{prefix}_{batch_id}_{label_class}_{index_in_batch}"
        out.append(
            {
                "feature_id": feature_id,
                "batch_id": batch_id,
                "message_id": str(feature.get("message_id", "")),
                "feature_name": str(feature.get("feature_name", "")),
                "feature_value": str(feature.get("feature_value", "")),
                "category": str(feature.get("category", "")),
                "rationale": str(feature.get("rationale", "")),
                "evidence_span": feature.get("evidence_span"),
                "label_class": label_class,
                "text_embedded": text_embedded,
            }
        )
    return out


def embed_features(records: list[dict[str, Any]]) -> np.ndarray:
    """Embed each record via Bedrock Titan; return float32 matrix (n, 256)."""
    vectors: list[list[float]] = []
    for record in tqdm(records, desc="Titan embeddings"):
        response = create_embedding(record["text_embedded"])
        if response["dimensions"] != EMBEDDING_DIMENSIONS:
            raise ValueError(f"Unexpected dimensions: {response['dimensions']}")
        vectors.append(response["embedding"])
    return np.asarray(vectors, dtype=np.float32)


def write_embedding_artifacts(
    output_dir: Path,
    records: list[dict[str, Any]],
    matrix: np.ndarray,
    metadata: dict[str, Any],
) -> Path:
    """Write features.jsonl, embeddings.npy, feature_ids.json, and metadata.json."""
    output_dir.mkdir(parents=True, exist_ok=True)
    feature_ids = [record["feature_id"] for record in records]
    np.save(output_dir / "embeddings.npy", matrix)
    (output_dir / "feature_ids.json").write_text(
        json.dumps(feature_ids, indent=2),
        encoding="utf-8",
    )
    with (output_dir / "features.jsonl").open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record) + "\n")
    payload = {
        **metadata,
        "bedrock_model_id": BEDROCK_MODEL_ID,
        "dimensions": EMBEDDING_DIMENSIONS,
        "normalize": constants.EMBEDDING_NORMALIZE,
        "timestamp_format": RUN_TIMESTAMP_FORMAT,
        "n_features": len(records),
    }
    (output_dir / METADATA_FILENAME).write_text(
        json.dumps(payload, indent=2),
        encoding="utf-8",
    )
    return output_dir


def _validate_mixed_metadata(run_dir: Path, batch_design: str) -> None:
    metadata_path = run_dir / METADATA_FILENAME
    if not metadata_path.is_file():
        return
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    run_meta = metadata.get("run_metadata", metadata)
    actual = run_meta.get("batch_design")
    if actual is not None and actual != batch_design:
        raise ValueError(
            f"Expected batch_design={batch_design} in {run_dir}, got {actual}"
        )


def run_generate_embeddings(
    arm: str,
    discovery_run_dir: str | None,
    topup_run_dir: str | None,
    batch_design: str,
) -> Path:
    """Run embedding for one arm and return the normalize embed output directory."""
    if batch_design != MIXED_BATCH_DESIGN:
        raise ValueError(f"Only batch_design={MIXED_BATCH_DESIGN} is supported")
    main_dir = resolve_discovery_run_dir(arm, discovery_run_dir)
    _validate_mixed_metadata(main_dir, MIXED_BATCH_DESIGN)
    topup_path = resolve_topup_run_dir(arm, topup_run_dir)
    _validate_mixed_metadata(topup_path, TOPUP_BATCH_DESIGN)
    discovery_rows = load_discovery_feature_rows(main_dir, topup_path)
    records = flatten_discovery_to_features(discovery_rows)
    matrix = embed_features(records)
    timestamp = make_run_timestamp()
    out_dir = paths.normalize_run_dir(arm) / timestamp
    metadata = {
        "arm": arm,
        "discovery_run_dir": str(main_dir),
        "topup_run_dir": str(topup_path),
        "batch_design": batch_design,
    }
    write_embedding_artifacts(out_dir, records, matrix, metadata)
    print(
        f"arm={arm} n_features={len(records)} "
        f"embeddings.npy shape={matrix.shape}"
    )
    print(f"Wrote {out_dir}/")
    return out_dir


def main(argv: list[str] | None = None) -> None:
    """CLI entry: embed discovery features for one text arm."""
    parser = argparse.ArgumentParser(description="Embed discovery features with Titan.")
    parser.add_argument("--arm", choices=constants.TEXT_ARMS, required=True)
    parser.add_argument("--discovery-run-dir", default=None)
    parser.add_argument("--topup-run-dir", default=None)
    parser.add_argument(
        "--batch-design",
        default=MIXED_BATCH_DESIGN,
        choices=(MIXED_BATCH_DESIGN,),
    )
    args = parser.parse_args(argv)
    run_generate_embeddings(
        args.arm,
        args.discovery_run_dir,
        args.topup_run_dir,
        args.batch_design,
    )


if __name__ == "__main__":
    main()
