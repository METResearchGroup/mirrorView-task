"""Cluster normalize embeddings with HDBSCAN and K-Means.

Run from the repo root::

    PYTHONPATH=. uv run python -m \\
        experiments.llm_feature_generation_phase_2_part_3_2026_09_24.src.cluster_embeddings \\
        --arm original_only --seed 42
"""

from __future__ import annotations

import argparse
import json
import statistics
from pathlib import Path
from typing import Any

import numpy as np
from sklearn.cluster import HDBSCAN, KMeans
from sklearn.metrics import adjusted_rand_score, silhouette_score
from sklearn.preprocessing import StandardScaler

from experiments.llm_feature_generation_phase_2_part_3_2026_09_24.src import constants, paths
from experiments.llm_feature_generation_phase_2_part_3_2026_09_24.src.paths import latest_timestamp_subdir

METADATA_FILENAME = constants.METADATA_FILENAME
DOWNSTREAM_METHOD = "hdbscan"
HDBSCAN_METRIC = "euclidean"
DEFAULT_MIN_CLUSTER_SIZE = 5
KMEANS_K_MIN = 2
KMEANS_K_MAX = 10
KMEANS_N_INIT = 10
KMEANS_MAX_ITER = 300
NOISE_CLUSTER_ID = -1
ASSIGNMENTS_HDBSCAN_FILENAME = "assignments_hdbscan.json"
ASSIGNMENTS_KMEANS_FILENAME = "assignments_kmeans.json"
STABILITY_FILENAME = "stability_within_arm.json"
CROSS_ARM_FILENAME = "stability_across_arms.json"
SHARED_NORMALIZE_DIR = paths.EXPERIMENT_ROOT / "outputs" / "shared" / "normalize"
SEED_PAIR_KEYS = ("42_43", "42_44", "43_44")


def resolve_embeddings_run_dir(arm: str, embeddings_run_dir: str | None) -> Path:
    """Resolve the normalize embed run directory for one arm."""
    if embeddings_run_dir:
        path = Path(embeddings_run_dir)
        if not path.is_dir():
            raise FileNotFoundError(f"embeddings-run-dir not found: {path}")
        return path
    return latest_timestamp_subdir(paths.normalize_run_dir(arm))


def load_embeddings(embeddings_run_dir: Path) -> tuple[np.ndarray, list[dict[str, Any]]]:
    """Load embedding matrix and aligned feature records."""
    npy_path = embeddings_run_dir / "embeddings.npy"
    jsonl_path = embeddings_run_dir / "features.jsonl"
    if not npy_path.is_file() or not jsonl_path.is_file():
        raise FileNotFoundError(f"Missing embeddings artifacts in {embeddings_run_dir}")
    matrix = np.load(npy_path)
    records = [
        json.loads(line)
        for line in jsonl_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    if matrix.shape[0] != len(records):
        raise ValueError("Row count mismatch between embeddings.npy and features.jsonl")
    if matrix.shape[1] != constants.EMBEDDING_DIM:
        raise ValueError(f"Expected embedding dim {constants.EMBEDDING_DIM}")
    return matrix, records


def run_hdbscan(
    matrix: np.ndarray,
    min_cluster_size: int,
    seed: int,
) -> np.ndarray:
    """Fit HDBSCAN on a scaled matrix and return per-row cluster labels."""
    _ = seed
    effective_size, min_samples = _resolve_hdbscan_params(matrix.shape[0], min_cluster_size)
    scaler = StandardScaler()
    scaled = scaler.fit_transform(matrix)
    model = HDBSCAN(
        min_cluster_size=effective_size,
        min_samples=min_samples,
        metric=HDBSCAN_METRIC,
        copy=True,
    )
    return model.fit_predict(scaled)


def _resolve_hdbscan_params(n_features: int, requested: int) -> tuple[int, int]:
    if n_features < 2:
        raise ValueError(f"Need at least 2 features to cluster, got {n_features}")
    if n_features >= requested * 2:
        return requested, requested
    if n_features < 20:
        return 2, 1
    effective = max(2, min(requested, n_features // 2))
    return effective, effective


def run_kmeans_sweep(
    matrix: np.ndarray,
    k_min: int,
    k_max: int,
    seed: int,
) -> tuple[dict[str, Any], np.ndarray]:
    """Sweep k and return k_selection payload plus best-k label vector."""
    scaler = StandardScaler()
    scaled = scaler.fit_transform(matrix)
    n_features = scaled.shape[0]
    rows: list[dict[str, Any]] = []
    best_k = k_min
    best_silhouette = -1.0
    for k in range(k_min, k_max + 1):
        if k >= n_features:
            break
        model = KMeans(
            n_clusters=k,
            random_state=seed,
            n_init=KMEANS_N_INIT,
            max_iter=KMEANS_MAX_ITER,
        )
        labels = model.fit_predict(scaled)
        silhouette = float(
            silhouette_score(scaled, labels, metric="euclidean", random_state=seed)
        )
        rows.append({"k": k, "silhouette": silhouette, "inertia": float(model.inertia_)})
        if silhouette > best_silhouette:
            best_silhouette = silhouette
            best_k = k
    final_model = KMeans(
        n_clusters=best_k,
        random_state=seed,
        n_init=KMEANS_N_INIT,
        max_iter=KMEANS_MAX_ITER,
    )
    best_labels = final_model.fit_predict(scaled)
    k_selection = {"selected_k": best_k, "rows": rows}
    return k_selection, best_labels


def assignments_to_json(labels: np.ndarray, feature_ids: list[str]) -> dict[str, int]:
    """Map feature_id strings to integer cluster labels."""
    if len(labels) != len(feature_ids):
        raise ValueError("labels and feature_ids length mismatch")
    return {feature_id: int(label) for feature_id, label in zip(feature_ids, labels, strict=True)}


def compute_seed_pair_ari(
    assignments_a: dict[str, int],
    assignments_b: dict[str, int],
) -> float:
    """Compute adjusted Rand index on the intersection of feature ids."""
    shared_ids = sorted(set(assignments_a) & set(assignments_b))
    if not shared_ids:
        raise ValueError("No shared feature ids for ARI")
    labels_a = [assignments_a[feature_id] for feature_id in shared_ids]
    labels_b = [assignments_b[feature_id] for feature_id in shared_ids]
    return float(adjusted_rand_score(labels_a, labels_b))


def _cluster_sizes(labels: np.ndarray) -> dict[str, int]:
    sizes: dict[str, int] = {}
    for cluster_id in sorted({int(label) for label in labels}):
        sizes[str(cluster_id)] = int(np.sum(labels == cluster_id))
    return sizes


def write_cluster_artifacts(
    output_dir: Path,
    hdbscan_labels: np.ndarray,
    kmeans_labels: np.ndarray,
    k_selection: dict[str, Any],
    feature_ids: list[str],
    metadata: dict[str, Any],
) -> Path:
    """Write cluster assignment JSON files and metadata under output_dir."""
    output_dir.mkdir(parents=True, exist_ok=True)
    hdbscan_map = assignments_to_json(hdbscan_labels, feature_ids)
    kmeans_map = assignments_to_json(kmeans_labels, feature_ids)
    (output_dir / ASSIGNMENTS_HDBSCAN_FILENAME).write_text(
        json.dumps(hdbscan_map, indent=2),
        encoding="utf-8",
    )
    (output_dir / ASSIGNMENTS_KMEANS_FILENAME).write_text(
        json.dumps(kmeans_map, indent=2),
        encoding="utf-8",
    )
    (output_dir / "cluster_sizes_hdbscan.json").write_text(
        json.dumps(_cluster_sizes(hdbscan_labels), indent=2),
        encoding="utf-8",
    )
    (output_dir / "k_selection.json").write_text(
        json.dumps(k_selection, indent=2),
        encoding="utf-8",
    )
    (output_dir / METADATA_FILENAME).write_text(
        json.dumps(metadata, indent=2),
        encoding="utf-8",
    )
    return output_dir


def aggregate_stability_within_arm(embeddings_run_dir: Path, arm: str) -> dict[str, Any]:
    """Aggregate pairwise seed ARI when all three cluster seed dirs exist."""
    seed_dirs = {
        seed: embeddings_run_dir / f"clusters_seed_{seed}"
        for seed in constants.CLUSTER_SEEDS
    }
    for seed, seed_dir in seed_dirs.items():
        if not (seed_dir / ASSIGNMENTS_HDBSCAN_FILENAME).is_file():
            raise FileNotFoundError(f"Missing seed {seed} assignments in {seed_dir}")
    assignments = {
        seed: json.loads((seed_dir / ASSIGNMENTS_HDBSCAN_FILENAME).read_text(encoding="utf-8"))
        for seed, seed_dir in seed_dirs.items()
    }
    pair_aris = {
        "42_43": compute_seed_pair_ari(assignments[42], assignments[43]),
        "42_44": compute_seed_pair_ari(assignments[42], assignments[44]),
        "43_44": compute_seed_pair_ari(assignments[43], assignments[44]),
    }
    hdbscan_counts: dict[str, int] = {}
    noise_fraction: dict[str, float] = {}
    for seed in constants.CLUSTER_SEEDS:
        labels = list(assignments[seed].values())
        n_noise = sum(1 for label in labels if label == NOISE_CLUSTER_ID)
        clusters = {label for label in labels if label != NOISE_CLUSTER_ID}
        hdbscan_counts[str(seed)] = len(clusters)
        noise_fraction[str(seed)] = n_noise / len(labels) if labels else 0.0
    mean_ari = statistics.mean(pair_aris.values())
    return {
        "arm": arm,
        "seeds": list(constants.CLUSTER_SEEDS),
        "adjusted_rand_index": pair_aris,
        "mean_ari": mean_ari,
        "hdbscan_cluster_counts": hdbscan_counts,
        "noise_fraction": noise_fraction,
    }


def write_stability_within_arm(embeddings_run_dir: Path, arm: str) -> Path | None:
    """Write stability_within_arm.json when all three seeds are present."""
    try:
        payload = aggregate_stability_within_arm(embeddings_run_dir, arm)
    except FileNotFoundError:
        return None
    out_path = embeddings_run_dir / STABILITY_FILENAME
    out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"stability_within_arm mean_ari={payload['mean_ari']:.2f}")
    return out_path


def write_cross_arm_stability() -> Path:
    """Roll up per-arm stability summaries into outputs/shared/normalize."""
    per_arm_mean_ari: dict[str, float] = {}
    per_arm_cluster_median: dict[str, int] = {}
    per_arm_noise_median: dict[str, float] = {}
    for arm in constants.TEXT_ARMS:
        embed_parent = paths.normalize_run_dir(arm)
        if not embed_parent.is_dir():
            continue
        embed_dir = latest_timestamp_subdir(embed_parent)
        stability_path = embed_dir / STABILITY_FILENAME
        if not stability_path.is_file():
            continue
        payload = json.loads(stability_path.read_text(encoding="utf-8"))
        per_arm_mean_ari[arm] = float(payload["mean_ari"])
        counts = [int(v) for v in payload["hdbscan_cluster_counts"].values()]
        noise = [float(v) for v in payload["noise_fraction"].values()]
        per_arm_cluster_median[arm] = int(statistics.median(counts))
        per_arm_noise_median[arm] = float(statistics.median(noise))
    summary = {
        "arms": list(constants.TEXT_ARMS),
        "per_arm_mean_ari": per_arm_mean_ari,
        "per_arm_hdbscan_cluster_count_median": per_arm_cluster_median,
        "per_arm_noise_fraction_median": per_arm_noise_median,
        "note": (
            "Cross-arm ARI not defined (distinct feature_id sets per arm); "
            "compare stability summaries."
        ),
    }
    SHARED_NORMALIZE_DIR.mkdir(parents=True, exist_ok=True)
    out_path = SHARED_NORMALIZE_DIR / CROSS_ARM_FILENAME
    out_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return out_path


def run_cluster_embeddings(
    arm: str,
    embeddings_run_dir: str | None,
    seed: int,
    min_cluster_size: int,
) -> Path:
    """Cluster one arm for a single seed and return clusters_seed_<seed> dir."""
    if seed not in constants.CLUSTER_SEEDS:
        raise ValueError(f"seed must be one of {constants.CLUSTER_SEEDS}")
    embed_dir = resolve_embeddings_run_dir(arm, embeddings_run_dir)
    matrix, records = load_embeddings(embed_dir)
    feature_ids = [record["feature_id"] for record in records]
    hdbscan_labels = run_hdbscan(matrix, min_cluster_size, seed)
    k_selection, kmeans_labels = run_kmeans_sweep(
        matrix,
        KMEANS_K_MIN,
        KMEANS_K_MAX,
        seed,
    )
    cluster_dir = embed_dir / f"clusters_seed_{seed}"
    n_noise = int(np.sum(hdbscan_labels == NOISE_CLUSTER_ID))
    n_clusters = len({int(label) for label in hdbscan_labels if int(label) != NOISE_CLUSTER_ID})
    noise_fraction = n_noise / len(hdbscan_labels) if len(hdbscan_labels) else 0.0
    metadata = {
        "seed": seed,
        "arm": arm,
        "embeddings_run_dir": str(embed_dir),
        "downstream_method": DOWNSTREAM_METHOD,
        "min_cluster_size": min_cluster_size,
    }
    write_cluster_artifacts(
        cluster_dir,
        hdbscan_labels,
        kmeans_labels,
        k_selection,
        feature_ids,
        metadata,
    )
    print(
        f"arm={arm} seed={seed} hdbscan_clusters={n_clusters} "
        f"noise_fraction={noise_fraction:.2f} kmeans_best_k={k_selection['selected_k']}"
    )
    print(f"Wrote {cluster_dir}/")
    write_stability_within_arm(embed_dir, arm)
    return cluster_dir


def main(argv: list[str] | None = None) -> None:
    """CLI entry: cluster embeddings or write cross-arm stability."""
    parser = argparse.ArgumentParser(description="Cluster normalize embeddings.")
    parser.add_argument("--arm", choices=constants.TEXT_ARMS, default=None)
    parser.add_argument("--embeddings-run-dir", default=None)
    parser.add_argument("--seed", type=int, default=None)
    parser.add_argument("--min-cluster-size", type=int, default=DEFAULT_MIN_CLUSTER_SIZE)
    parser.add_argument("--write-cross-arm-stability", action="store_true")
    args = parser.parse_args(argv)
    if args.write_cross_arm_stability:
        out_path = write_cross_arm_stability()
        print(f"Wrote {out_path}")
        return
    if args.arm is None or args.seed is None:
        raise SystemExit("--arm and --seed are required unless --write-cross-arm-stability")
    run_cluster_embeddings(args.arm, args.embeddings_run_dir, args.seed, args.min_cluster_size)


if __name__ == "__main__":
    main()
