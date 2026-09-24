"""Cluster normalize embeddings with HDBSCAN and K-Means.

Run from the repo root::

    PYTHONPATH=. uv run python -m \\
        experiments.llm_feature_generation_phase_2_part_3_2026_09_24.src.cluster_embeddings \\
        --arm original_only --embeddings-run-dir outputs/.../normalize/<ts> --stability-only
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
STABILITY_V2_FILENAME = constants.STABILITY_V2_FILENAME
K_SELECTION_WIDE_FILENAME = constants.K_SELECTION_WIDE_FILENAME
CROSS_ARM_V2_FILENAME = constants.STABILITY_ACROSS_ARMS_V2_FILENAME
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


def _scale_matrix(matrix: np.ndarray) -> np.ndarray:
    scaler = StandardScaler()
    return scaler.fit_transform(matrix)


def _k_values_for_sweep(k_min: int, k_max: int, step: int, n_features: int) -> list[int]:
    candidates = list(range(k_min, k_max + 1, step))
    return [k for k in candidates if k < n_features]


def _fit_kmeans_labels(scaled: np.ndarray, k: int, seed: int) -> np.ndarray:
    model = KMeans(
        n_clusters=k,
        random_state=seed,
        n_init=constants.KMEANS_N_INIT,
        max_iter=constants.KMEANS_MAX_ITER,
    )
    return model.fit_predict(scaled)


def _silhouette_for_labels(scaled: np.ndarray, labels: np.ndarray, seed: int) -> float:
    return float(silhouette_score(scaled, labels, metric="euclidean", random_state=seed))


def _kmeans_edge_flags(selected_k: int, attempted: list[int]) -> dict[str, bool]:
    if not attempted:
        return {"hits_k_min_edge": False, "hits_k_max_edge": False}
    return {
        "hits_k_min_edge": selected_k == min(attempted),
        "hits_k_max_edge": selected_k == max(attempted),
    }


def run_kmeans_sweep_wide(matrix: np.ndarray, seed: int) -> dict[str, Any]:
    """Sweep a wide k range and return selection metrics including edge flags."""
    scaled = _scale_matrix(matrix)
    k_values = _k_values_for_sweep(
        constants.KMEANS_WIDE_K_MIN,
        constants.KMEANS_WIDE_K_MAX,
        constants.KMEANS_WIDE_K_STEP,
        scaled.shape[0],
    )
    rows: list[dict[str, Any]] = []
    best_k = k_values[0] if k_values else constants.KMEANS_WIDE_K_MIN
    best_silhouette = -1.0
    for k in k_values:
        model = KMeans(
            n_clusters=k,
            random_state=seed,
            n_init=constants.KMEANS_N_INIT,
            max_iter=constants.KMEANS_MAX_ITER,
        )
        labels = model.fit_predict(scaled)
        silhouette = _silhouette_for_labels(scaled, labels, seed)
        rows.append({"k": k, "silhouette": silhouette, "inertia": float(model.inertia_)})
        if silhouette > best_silhouette:
            best_silhouette = silhouette
            best_k = k
    edge = _kmeans_edge_flags(best_k, k_values)
    return {
        "selected_k": best_k,
        "rows": rows,
        "k_min": constants.KMEANS_WIDE_K_MIN,
        "k_max": constants.KMEANS_WIDE_K_MAX,
        "k_step": constants.KMEANS_WIDE_K_STEP,
        **edge,
    }


def load_hdbscan_assignments(seed_dir: Path) -> dict[str, int]:
    """Load HDBSCAN assignments JSON from one clusters_seed directory."""
    path = seed_dir / ASSIGNMENTS_HDBSCAN_FILENAME
    if not path.is_file():
        raise FileNotFoundError(f"Missing {ASSIGNMENTS_HDBSCAN_FILENAME} in {seed_dir}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    return {str(key): int(value) for key, value in payload.items()}


def assignments_to_label_vector(
    feature_ids: list[str],
    assignments: dict[str, int],
) -> np.ndarray:
    """Align assignment dict to feature_ids row order."""
    return np.array([assignments[feature_id] for feature_id in feature_ids], dtype=np.int64)


def resolve_min_cluster_size(embeddings_run_dir: Path) -> int:
    """Read min_cluster_size from reference seed metadata when present."""
    meta_path = (
        embeddings_run_dir
        / f"clusters_seed_{constants.HDBSCAN_REFERENCE_SEED}"
        / METADATA_FILENAME
    )
    if not meta_path.is_file():
        return constants.HDBSCAN_DEFAULT_MIN_CLUSTER_SIZE
    payload = json.loads(meta_path.read_text(encoding="utf-8"))
    return int(payload.get("min_cluster_size", constants.HDBSCAN_DEFAULT_MIN_CLUSTER_SIZE))


def compute_pairwise_seed_aris(
    assignments_by_seed: dict[int, dict[str, int]],
) -> dict[str, float]:
    """Compute adjusted Rand index for the three standard seed pairs."""
    return {
        "42_43": compute_seed_pair_ari(assignments_by_seed[42], assignments_by_seed[43]),
        "42_44": compute_seed_pair_ari(assignments_by_seed[42], assignments_by_seed[44]),
        "43_44": compute_seed_pair_ari(assignments_by_seed[43], assignments_by_seed[44]),
    }


def compute_kmeans_stability_at_k(
    matrix: np.ndarray,
    feature_ids: list[str],
    selected_k: int,
) -> dict[str, Any]:
    """Run K-Means at fixed k for each cluster seed and report pairwise ARI."""
    scaled = _scale_matrix(matrix)
    assignments_by_seed: dict[int, dict[str, int]] = {}
    for seed in constants.CLUSTER_SEEDS:
        labels = _fit_kmeans_labels(scaled, selected_k, seed)
        assignments_by_seed[seed] = assignments_to_json(labels, feature_ids)
    pair_aris = compute_pairwise_seed_aris(assignments_by_seed)
    return {
        "selected_k": selected_k,
        "adjusted_rand_index": pair_aris,
        "mean_ari": float(statistics.mean(pair_aris.values())),
    }


def _ari_label_vectors(
    reference: np.ndarray,
    candidate: np.ndarray,
    exclude_noise: bool,
) -> float:
    if exclude_noise:
        noise_id = constants.NOISE_CLUSTER_ID
        mask = (reference != noise_id) & (candidate != noise_id)
        if int(np.sum(mask)) < 2:
            return float("nan")
        return float(adjusted_rand_score(reference[mask], candidate[mask]))
    return float(adjusted_rand_score(reference, candidate))


def _one_subsample_ari(
    matrix: np.ndarray,
    reference_labels: np.ndarray,
    min_cluster_size: int,
    rng: np.random.Generator,
) -> tuple[float, float]:
    n_rows = matrix.shape[0]
    n_keep = max(2, int(n_rows * constants.HDBSCAN_SUBSAMPLE_FRACTION))
    indices = rng.choice(n_rows, size=n_keep, replace=False)
    sub_matrix = matrix[indices]
    sub_labels = run_hdbscan(sub_matrix, min_cluster_size, constants.HDBSCAN_REFERENCE_SEED)
    ref_slice = reference_labels[indices]
    all_points = _ari_label_vectors(ref_slice, sub_labels, exclude_noise=False)
    no_noise = _ari_label_vectors(ref_slice, sub_labels, exclude_noise=True)
    return all_points, no_noise


def _summarize_repeat_aris(values: list[float]) -> dict[str, float]:
    clean = [value for value in values if not np.isnan(value)]
    if not clean:
        return {"mean": float("nan"), "std": float("nan"), "min": float("nan")}
    return {
        "mean": float(statistics.mean(clean)),
        "std": float(statistics.pstdev(clean)) if len(clean) > 1 else 0.0,
        "min": float(min(clean)),
    }


def compute_hdbscan_subsample_stability(
    matrix: np.ndarray,
    reference_labels: np.ndarray,
    min_cluster_size: int,
) -> dict[str, Any]:
    """Measure HDBSCAN stability under repeated row subsamples vs full reference."""
    all_aris: list[float] = []
    no_noise_aris: list[float] = []
    for repeat in range(constants.HDBSCAN_SUBSAMPLE_REPEATS):
        rng = np.random.default_rng(constants.HDBSCAN_REFERENCE_SEED + repeat)
        all_ari, no_noise_ari = _one_subsample_ari(
            matrix,
            reference_labels,
            min_cluster_size,
            rng,
        )
        all_aris.append(all_ari)
        no_noise_aris.append(no_noise_ari)
    return {
        "fraction": constants.HDBSCAN_SUBSAMPLE_FRACTION,
        "repeats": constants.HDBSCAN_SUBSAMPLE_REPEATS,
        "reference_seed": constants.HDBSCAN_REFERENCE_SEED,
        "ari_all_points": _summarize_repeat_aris(all_aris),
        "ari_excluding_noise": _summarize_repeat_aris(no_noise_aris),
    }


def hdbscan_noise_fractions(
    embeddings_run_dir: Path,
) -> dict[str, float]:
    """Report noise share per cluster seed from existing HDBSCAN assignments."""
    fractions: dict[str, float] = {}
    for seed in constants.CLUSTER_SEEDS:
        seed_dir = embeddings_run_dir / f"clusters_seed_{seed}"
        assignments = load_hdbscan_assignments(seed_dir)
        labels = list(assignments.values())
        n_noise = sum(1 for label in labels if label == constants.NOISE_CLUSTER_ID)
        fractions[str(seed)] = n_noise / len(labels) if labels else 0.0
    return fractions


def build_stability_v2_payload(
    arm: str,
    matrix: np.ndarray,
    feature_ids: list[str],
    embeddings_run_dir: Path,
    k_selection_wide: dict[str, Any],
) -> dict[str, Any]:
    """Assemble stability_v2 metrics without rewriting cluster artifacts."""
    min_cluster_size = resolve_min_cluster_size(embeddings_run_dir)
    ref_dir = embeddings_run_dir / f"clusters_seed_{constants.HDBSCAN_REFERENCE_SEED}"
    reference_assignments = load_hdbscan_assignments(ref_dir)
    reference_labels = assignments_to_label_vector(feature_ids, reference_assignments)
    kmeans_stability = compute_kmeans_stability_at_k(
        matrix,
        feature_ids,
        int(k_selection_wide["selected_k"]),
    )
    subsample = compute_hdbscan_subsample_stability(
        matrix,
        reference_labels,
        min_cluster_size,
    )
    return {
        "arm": arm,
        "embeddings_run_dir": str(embeddings_run_dir),
        "hdbscan_noise_fraction": hdbscan_noise_fractions(embeddings_run_dir),
        "kmeans_wide_selection": {
            "selected_k": k_selection_wide["selected_k"],
            "hits_k_min_edge": k_selection_wide["hits_k_min_edge"],
            "hits_k_max_edge": k_selection_wide["hits_k_max_edge"],
            "k_min": k_selection_wide["k_min"],
            "k_max": k_selection_wide["k_max"],
            "k_step": k_selection_wide["k_step"],
        },
        "kmeans_seed_stability": kmeans_stability,
        "hdbscan_subsample_stability": subsample,
    }


def write_stability_v2_artifacts(
    embeddings_run_dir: Path,
    arm: str,
) -> tuple[Path, Path]:
    """Write stability_v2.json and k_selection_wide.json from existing embeddings."""
    matrix, records = load_embeddings(embeddings_run_dir)
    feature_ids = [record["feature_id"] for record in records]
    k_selection_wide = run_kmeans_sweep_wide(matrix, constants.HDBSCAN_REFERENCE_SEED)
    wide_path = embeddings_run_dir / K_SELECTION_WIDE_FILENAME
    wide_path.write_text(json.dumps(k_selection_wide, indent=2), encoding="utf-8")
    payload = build_stability_v2_payload(
        arm,
        matrix,
        feature_ids,
        embeddings_run_dir,
        k_selection_wide,
    )
    stability_path = embeddings_run_dir / STABILITY_V2_FILENAME
    stability_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(
        f"stability_v2 arm={arm} k={k_selection_wide['selected_k']} "
        f"kmeans_mean_ari={payload['kmeans_seed_stability']['mean_ari']:.3f}"
    )
    return stability_path, wide_path


def run_stability_only(arm: str, embeddings_run_dir: str | None) -> tuple[Path, Path]:
    """Compute stability v2 metrics without re-clustering or LLM calls."""
    embed_dir = resolve_embeddings_run_dir(arm, embeddings_run_dir)
    return write_stability_v2_artifacts(embed_dir, arm)


def write_cross_arm_stability_v2() -> Path:
    """Roll up per-arm stability_v2 summaries into outputs/shared/normalize."""
    per_arm: dict[str, dict[str, Any]] = {}
    for arm in constants.TEXT_ARMS:
        embed_parent = paths.normalize_run_dir(arm)
        if not embed_parent.is_dir():
            continue
        embed_dir = latest_timestamp_subdir(embed_parent)
        stability_path = embed_dir / STABILITY_V2_FILENAME
        if not stability_path.is_file():
            continue
        per_arm[arm] = json.loads(stability_path.read_text(encoding="utf-8"))
    summary = {
        "arms": list(constants.TEXT_ARMS),
        "per_arm": per_arm,
        "note": (
            "Cross-arm ARI not defined (distinct feature_id sets per arm); "
            "compare stability_v2 summaries."
        ),
    }
    SHARED_NORMALIZE_DIR.mkdir(parents=True, exist_ok=True)
    out_path = SHARED_NORMALIZE_DIR / CROSS_ARM_V2_FILENAME
    out_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return out_path


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
    parser.add_argument("--write-cross-arm-stability-v2", action="store_true")
    parser.add_argument("--stability-only", action="store_true")
    args = parser.parse_args(argv)
    if args.write_cross_arm_stability:
        out_path = write_cross_arm_stability()
        print(f"Wrote {out_path}")
        return
    if args.write_cross_arm_stability_v2:
        out_path = write_cross_arm_stability_v2()
        print(f"Wrote {out_path}")
        return
    if args.stability_only:
        if args.arm is None:
            raise SystemExit("--arm is required with --stability-only")
        stability_path, wide_path = run_stability_only(args.arm, args.embeddings_run_dir)
        print(f"Wrote {stability_path}")
        print(f"Wrote {wide_path}")
        return
    if args.arm is None or args.seed is None:
        raise SystemExit(
            "--arm and --seed are required unless using a stability subcommand"
        )
    run_cluster_embeddings(args.arm, args.embeddings_run_dir, args.seed, args.min_cluster_size)


if __name__ == "__main__":
    main()
