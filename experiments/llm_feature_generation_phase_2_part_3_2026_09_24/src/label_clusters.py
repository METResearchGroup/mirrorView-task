"""Label HDBSCAN clusters with gpt-6-luna via llm_client.

Run from the repo root::

    PYTHONPATH=. uv run python -m \\
        experiments.llm_feature_generation_phase_2_part_3_2026_09_24.src.label_clusters \\
        --arm original_only --seed 42 --clusters-run-dir <path>
"""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any

import numpy as np

from experiments.llm_feature_generation_phase_2_part_3_2026_09_24.src import constants, llm_client, paths
from experiments.llm_feature_generation_phase_2_part_3_2026_09_24.src.prompts import build_cluster_label_messages
from experiments.llm_feature_generation_phase_2_part_3_2026_09_24.src.schemas import ClusterLabelResult

METADATA_FILENAME = constants.METADATA_FILENAME
ASSIGNMENTS_HDBSCAN_FILENAME = "assignments_hdbscan.json"
NOISE_CLUSTER_ID = -1
DEFAULT_SAMPLE_PER_CLUSTER = 8
STAGE_CLUSTER_LABEL = "cluster_label"
RUN_TIMESTAMP_FORMAT = constants.RUN_TIMESTAMP_FORMAT


def _require_step3_contracts() -> None:
    if build_cluster_label_messages is None:
        raise ImportError("build_cluster_label_messages missing from prompts.py")
    if ClusterLabelResult is None:
        raise ImportError("ClusterLabelResult missing from schemas.py")


_require_step3_contracts()


def make_run_timestamp() -> str:
    """Return a local timestamp for label output folders."""
    return datetime.now().strftime(RUN_TIMESTAMP_FORMAT)


def load_hdbscan_assignments(clusters_run_dir: Path) -> dict[str, int]:
    """Load feature_id -> cluster_id map from assignments_hdbscan.json."""
    path = clusters_run_dir / ASSIGNMENTS_HDBSCAN_FILENAME
    if not path.is_file():
        raise FileNotFoundError(f"Missing {ASSIGNMENTS_HDBSCAN_FILENAME} in {clusters_run_dir}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    return {str(key): int(value) for key, value in payload.items()}


def build_cluster_label_items(
    assignments: dict[str, int],
    feature_records: list[dict[str, Any]],
    sample_per_cluster: int,
    seed: int,
) -> list[dict[str, Any]]:
    """Build one labeling item per non-noise HDBSCAN cluster."""
    if sample_per_cluster <= 0:
        raise ValueError("sample_per_cluster must be positive")
    by_id = {record["feature_id"]: record for record in feature_records}
    by_cluster: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for feature_id, cluster_id in assignments.items():
        if cluster_id == NOISE_CLUSTER_ID:
            continue
        record = by_id.get(feature_id)
        if record is None:
            raise KeyError(f"Unknown feature_id in assignments: {feature_id}")
        by_cluster[cluster_id].append(record)
    items: list[dict[str, Any]] = []
    for cluster_id in sorted(by_cluster):
        members = by_cluster[cluster_id]
        rng = np.random.default_rng(seed + int(cluster_id))
        n_sample = min(sample_per_cluster, len(members))
        indices = rng.choice(len(members), size=n_sample, replace=False)
        sampled = [_sample_feature_payload(members[int(index)]) for index in indices]
        label_class = _majority_label_class(members)
        items.append(
            {
                "cluster_id": int(cluster_id),
                "label_class": label_class,
                "n_members": len(members),
                "sampled_features": sampled,
            }
        )
    return items


def _sample_feature_payload(record: dict[str, Any]) -> dict[str, Any]:
    return {
        "feature_id": record["feature_id"],
        "message_id": record["message_id"],
        "feature_name": record["feature_name"],
        "feature_value": record["feature_value"],
        "category": record.get("category", ""),
        "rationale": record.get("rationale", ""),
        "evidence_span": record.get("evidence_span"),
    }


def _majority_label_class(members: list[dict[str, Any]]) -> str:
    counts = Counter(str(record.get("label_class", constants.DECISION_KEEP)) for record in members)
    return counts.most_common(1)[0][0]


def label_clusters_for_run(
    items: list[dict[str, Any]],
    arm: str,
    seed: int,
    output_dir: Path,
) -> Path:
    """Call llm_client.complete_structured for each cluster labeling item."""
    if not items:
        raise ValueError("No clusters to label")
    output_dir.mkdir(parents=True, exist_ok=True)
    run_metadata = {
        "model": constants.LLM_MODEL_ID,
        "reasoning_effort": constants.LLM_REASONING_EFFORT,
        "arm": arm,
        "seed": seed,
        "stage": STAGE_CLUSTER_LABEL,
        "litellm_model": constants.LLM_LITELLM_MODEL_ID,
        "timestamp_format": RUN_TIMESTAMP_FORMAT,
    }
    for call_index, item in enumerate(items):
        messages = build_cluster_label_messages(item)
        parsed = llm_client.complete_structured(
            messages,
            ClusterLabelResult,
            stage=STAGE_CLUSTER_LABEL,
            arm=arm,
            call_index=call_index,
            output_dir=output_dir,
            run_metadata=run_metadata,
        )
        row = {
            "cluster_id": item["cluster_id"],
            "arm": arm,
            "seed": seed,
            "n_members": item["n_members"],
            "sampled_feature_ids": [
                feature["feature_id"] for feature in item["sampled_features"]
            ],
            "result": parsed.model_dump(),
        }
        _merge_cluster_label_row(output_dir, call_index, row)
    metadata_path = output_dir / METADATA_FILENAME
    metadata_path.write_text(
        json.dumps({"run_metadata": run_metadata}, indent=2) + "\n",
        encoding="utf-8",
    )
    return output_dir


def _merge_cluster_label_row(output_dir: Path, call_index: int, row: dict[str, Any]) -> None:
    matches = sorted(output_dir.glob(f"{call_index:05d}_*.json"))
    if not matches:
        raise FileNotFoundError(f"Missing llm artifact for call_index={call_index}")
    artifact_path = matches[-1]
    payload = json.loads(artifact_path.read_text(encoding="utf-8"))
    payload["cluster_label_row"] = row
    artifact_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def _load_feature_records(embeddings_run_dir: Path) -> list[dict[str, Any]]:
    jsonl_path = embeddings_run_dir / "features.jsonl"
    if not jsonl_path.is_file():
        raise FileNotFoundError(f"Missing features.jsonl in {embeddings_run_dir}")
    return [
        json.loads(line)
        for line in jsonl_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def run_label_clusters(
    arm: str,
    clusters_run_dir: str,
    seed: int,
    sample_per_cluster: int,
) -> Path:
    """Label all non-noise clusters for one clusters_seed_<seed> directory."""
    cluster_dir = Path(clusters_run_dir)
    assignments = load_hdbscan_assignments(cluster_dir)
    embeddings_run_dir = cluster_dir.parent
    feature_records = _load_feature_records(embeddings_run_dir)
    items = build_cluster_label_items(
        assignments,
        feature_records,
        sample_per_cluster,
        seed,
    )
    for item in items:
        item["arm"] = arm
        item["seed"] = seed
    label_timestamp = make_run_timestamp()
    output_dir = cluster_dir / "labels" / label_timestamp
    n_noise = sum(1 for cluster_id in assignments.values() if cluster_id == NOISE_CLUSTER_ID)
    label_clusters_for_run(items, arm, seed, output_dir)
    print(
        f"arm={arm} seed={seed} clusters_labeled={len(items)} skipped_noise={n_noise}"
    )
    print(f"Wrote {output_dir}/")
    return output_dir


def main(argv: list[str] | None = None) -> None:
    """CLI entry: label HDBSCAN clusters for one seed directory."""
    parser = argparse.ArgumentParser(description="LLM label HDBSCAN clusters.")
    parser.add_argument("--arm", choices=constants.TEXT_ARMS, required=True)
    parser.add_argument("--clusters-run-dir", required=True)
    parser.add_argument("--seed", type=int, required=True)
    parser.add_argument(
        "--sample-per-cluster",
        type=int,
        default=DEFAULT_SAMPLE_PER_CLUSTER,
    )
    args = parser.parse_args(argv)
    run_label_clusters(
        args.arm,
        args.clusters_run_dir,
        args.seed,
        args.sample_per_cluster,
    )


if __name__ == "__main__":
    main()
