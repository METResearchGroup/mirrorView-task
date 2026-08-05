"""Stage 3: dual HDBSCAN + KMeans clustering of feature embeddings with PNG viz.

Path-parameterized helpers with no experiment imports. Callers supply
``cluster_output_root`` and ``class_png_dir``.

Run from repo root::

    PYTHONPATH=. uv run python -c "
    from shared.feature_discovery.llm_based import cluster
    assert hasattr(cluster, 'run_dual_clustering')
    print('cluster OK')
    "
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from sklearn.cluster import HDBSCAN, KMeans
from sklearn.decomposition import PCA
from sklearn.metrics import silhouette_score
from sklearn.preprocessing import StandardScaler

_METADATA_FILENAME = "metadata.json"
DEFAULT_SEED = 42
DEFAULT_MIN_CLUSTER_SIZE = 5
HDBSCAN_METRIC = "euclidean"
HDBSCAN_NOISE_POLICY = "skip_noise_for_labeling"
DOWNSTREAM_METHOD = "hdbscan"
KMEANS_N_INIT = 10
KMEANS_MAX_ITER = 300
SILHOUETTE_SAMPLE_SIZE_CAP = 4000
PCA_N_COMPONENTS_VIZ = 2
ASSIGNMENTS_HDBSCAN_FILENAME = "assignments_hdbscan.json"
ASSIGNMENTS_KMEANS_FILENAME = "assignments_kmeans.json"
PNG_HDBSCAN_NAME = "cluster_hdbscan.png"
PNG_KMEANS_NAME = "cluster_kmeans.png"
EMBEDDING_DIMENSIONS = 256


def load_stage2_embeddings(
    embeddings_run_dir: Path,
) -> tuple[np.ndarray, list[dict[str, Any]]]:
    """Load embedding matrix and aligned feature provenance records.

    Parameters
    ----------
    embeddings_run_dir
        Stage-2 run directory with embeddings.npy and features.jsonl.

    Returns
    -------
    tuple[np.ndarray, list[dict[str, Any]]]
        Matrix shape (n_features, 256) and provenance rows aligned by row order.
    """
    npy_path = embeddings_run_dir / "embeddings.npy"
    jsonl_path = embeddings_run_dir / "features.jsonl"
    ids_path = embeddings_run_dir / "feature_ids.json"
    if not npy_path.is_file():
        raise FileNotFoundError(f"Missing embeddings.npy in {embeddings_run_dir}")
    if not jsonl_path.is_file():
        raise FileNotFoundError(f"Missing features.jsonl in {embeddings_run_dir}")

    matrix = np.load(npy_path)
    records = [
        json.loads(line)
        for line in jsonl_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    if len(records) != matrix.shape[0]:
        raise ValueError(
            f"Row mismatch: embeddings.npy has {matrix.shape[0]} rows, "
            f"features.jsonl has {len(records)}"
        )
    if ids_path.is_file():
        feature_ids = json.loads(ids_path.read_text(encoding="utf-8"))
        if feature_ids != [record["feature_id"] for record in records]:
            raise ValueError("feature_ids.json does not match features.jsonl order")
    if matrix.ndim != 2 or matrix.shape[1] != EMBEDDING_DIMENSIONS:
        raise ValueError(
            f"Expected matrix shape (n, {EMBEDDING_DIMENSIONS}), got {matrix.shape}"
        )
    return matrix, records


def resolve_hdbscan_params(
    n_features: int,
    requested_min_cluster_size: int,
) -> tuple[int, int, str | None]:
    """Choose HDBSCAN min_cluster_size and min_samples for the run size.

    Production-scale n keeps the requested min_cluster_size. Tiny smoke n
    (e.g. ≤8 features) lowers min_cluster_size to 2 and min_samples to 1 so
    clusters can form; otherwise all points become noise and Stage 4 cannot
    label.

    Parameters
    ----------
    n_features
        Number of feature vectors.
    requested_min_cluster_size
        Preferred min_cluster_size (default 5).

    Returns
    -------
    tuple[int, int, str | None]
        Effective min_cluster_size, min_samples, and optional override reason.
    """
    if n_features < 2:
        raise ValueError(f"Need at least 2 features to cluster, got {n_features}")
    if n_features >= requested_min_cluster_size * 2:
        return requested_min_cluster_size, requested_min_cluster_size, None
    effective_size = max(2, min(requested_min_cluster_size, n_features // 2))
    if n_features < 20:
        effective_size = 2
        min_samples = 1
        reason = (
            f"n_features={n_features} < 20: "
            f"min_cluster_size=2, min_samples=1 "
            f"(requested min_cluster_size={requested_min_cluster_size})"
        )
        return effective_size, min_samples, reason
    reason = (
        f"n_features={n_features} < 2 * requested={requested_min_cluster_size}"
    )
    return effective_size, effective_size, reason


def fit_hdbscan(
    scaled_matrix: np.ndarray,
    min_cluster_size: int,
    min_samples: int,
) -> tuple[np.ndarray, dict[str, Any]]:
    """Fit sklearn HDBSCAN and return labels plus params metadata."""
    model = HDBSCAN(
        min_cluster_size=min_cluster_size,
        min_samples=min_samples,
        metric=HDBSCAN_METRIC,
        copy=True,
    )
    labels = model.fit_predict(scaled_matrix)
    unique = set(int(label) for label in labels)
    n_noise = int(np.sum(labels == -1))
    n_clusters = len(unique - {-1})
    params = {
        "method": "hdbscan",
        "min_cluster_size": min_cluster_size,
        "min_samples": min_samples,
        "metric": HDBSCAN_METRIC,
        "n_clusters": n_clusters,
        "n_noise": n_noise,
        "hdbscan_noise_policy": HDBSCAN_NOISE_POLICY,
    }
    return labels, params


def select_k_silhouette(
    scaled_matrix: np.ndarray,
    seed: int,
) -> tuple[int, list[dict[str, Any]], str]:
    """Select KMeans k by maximizing silhouette on the scaled matrix.

    Parameters
    ----------
    scaled_matrix
        Scaled embedding matrix.
    seed
        random_state for KMeans and silhouette subsample.

    Returns
    -------
    tuple[int, list[dict[str, Any]], str]
        Selected k, selection rows, and selection mode string.
    """
    n_features = scaled_matrix.shape[0]
    if n_features < 4:
        return 1, [], "n_features_lt_4_forced_k1"

    k_max = min(15, n_features - 1)
    k_range = range(2, k_max + 1)
    rows: list[dict[str, Any]] = []
    best_k = 2
    best_sil = -1.0
    sample_size = min(SILHOUETTE_SAMPLE_SIZE_CAP, n_features)
    for k in k_range:
        model = KMeans(
            n_clusters=k,
            random_state=seed,
            n_init=KMEANS_N_INIT,
            max_iter=KMEANS_MAX_ITER,
        )
        labels = model.fit_predict(scaled_matrix)
        silhouette = float(
            silhouette_score(
                scaled_matrix,
                labels,
                metric="euclidean",
                sample_size=sample_size,
                random_state=seed,
            )
        )
        rows.append(
            {
                "k": int(k),
                "silhouette": silhouette,
                "inertia": float(model.inertia_),
            }
        )
        if silhouette > best_sil:
            best_sil = silhouette
            best_k = int(k)
    return best_k, rows, "silhouette_max"


def fit_kmeans(
    scaled_matrix: np.ndarray,
    selected_k: int,
    seed: int,
) -> np.ndarray:
    """Fit final KMeans and return cluster labels."""
    model = KMeans(
        n_clusters=selected_k,
        random_state=seed,
        n_init=KMEANS_N_INIT,
        max_iter=KMEANS_MAX_ITER,
    )
    return model.fit_predict(scaled_matrix)


def _assignment_rows(
    records: list[dict[str, Any]],
    labels: np.ndarray,
) -> list[dict[str, Any]]:
    """Build per-feature assignment dicts for one clustering method."""
    rows: list[dict[str, Any]] = []
    for record, cluster_id in zip(records, labels, strict=True):
        row: dict[str, Any] = {
            "feature_id": record["feature_id"],
            "feature_name": record["feature_name"],
            "feature_value": record["feature_value"],
            "category": record.get("category"),
            "rationale": record.get("rationale"),
            "evidence_span": record.get("evidence_span"),
            "cluster_id": int(cluster_id),
        }
        if "message_id" in record:
            row["message_id"] = record["message_id"]
        if "participant_id" in record:
            row["participant_id"] = record["participant_id"]
        rows.append(row)
    return rows


def _cluster_sizes(labels: np.ndarray) -> dict[str, int]:
    """Return cluster_id -> size map as JSON-friendly string keys."""
    sizes: dict[str, int] = {}
    for cluster_id in sorted(set(int(label) for label in labels)):
        sizes[str(cluster_id)] = int(np.sum(labels == cluster_id))
    return sizes


def _plot_clusters(
    coords_2d: np.ndarray,
    labels: np.ndarray,
    title: str,
    output_path: Path,
    noise_gray: bool,
) -> None:
    """Write a 2D scatter PNG colored by cluster labels."""
    fig, ax = plt.subplots(figsize=(8, 6))
    unique_labels = sorted(set(int(label) for label in labels))
    cmap = plt.get_cmap("tab20")
    for index, cluster_id in enumerate(unique_labels):
        mask = labels == cluster_id
        if noise_gray and cluster_id == -1:
            color = "0.6"
            label = "noise (-1)"
        else:
            color = cmap(index % 20)
            label = f"cluster {cluster_id}"
        ax.scatter(
            coords_2d[mask, 0],
            coords_2d[mask, 1],
            c=[color],
            s=36,
            alpha=0.85,
            label=label,
            edgecolors="none",
        )
    ax.set_title(title)
    ax.set_xlabel("PCA-1")
    ax.set_ylabel("PCA-2")
    ax.legend(loc="best", fontsize=8, frameon=False)
    fig.tight_layout()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=150)
    plt.close(fig)


def write_cluster_artifacts(
    cluster_output_root: Path,
    class_png_dir: Path,
    label_class: str,
    source_embeddings_run_dir: Path,
    records: list[dict[str, Any]],
    scaled_matrix: np.ndarray,
    hdbscan_labels: np.ndarray,
    hdbscan_params: dict[str, Any],
    kmeans_labels: np.ndarray,
    selected_k: int,
    k_selection_rows: list[dict[str, Any]],
    k_selection_mode: str,
    seed: int,
    min_cluster_size_requested: int,
    run_timestamp: str,
) -> Path:
    """Write assignments, sizes, PNGs, and metadata for one class run.

    Parameters
    ----------
    cluster_output_root
        Class/group Stage-3 root; timestamped artifacts go under this path.
    class_png_dir
        Directory for class-root PNGs (typically the Stage-3 root).
    label_class
        Class or Likert-group label for titles and metadata.
    source_embeddings_run_dir
        Stage-2 run directory used as input.
    records
        Feature provenance rows aligned with the embedding matrix.
    scaled_matrix
        StandardScaler-transformed embeddings used for clustering and PCA.
    hdbscan_labels
        HDBSCAN cluster labels (noise = -1).
    hdbscan_params
        HDBSCAN params metadata dict.
    kmeans_labels
        KMeans cluster labels.
    selected_k
        Selected KMeans k.
    k_selection_rows
        Silhouette selection rows.
    k_selection_mode
        Selection mode string.
    seed
        RNG seed for PCA.
    min_cluster_size_requested
        Preferred HDBSCAN min_cluster_size before overrides.
    run_timestamp
        Output folder name.

    Returns
    -------
    Path
        Stage-3 run directory.
    """
    out_dir = cluster_output_root / run_timestamp
    out_dir.mkdir(parents=True, exist_ok=True)
    class_png_dir.mkdir(parents=True, exist_ok=True)

    hdbscan_assignments = _assignment_rows(records, hdbscan_labels)
    kmeans_assignments = _assignment_rows(records, kmeans_labels)
    (out_dir / ASSIGNMENTS_HDBSCAN_FILENAME).write_text(
        json.dumps(hdbscan_assignments, indent=2),
        encoding="utf-8",
    )
    (out_dir / ASSIGNMENTS_KMEANS_FILENAME).write_text(
        json.dumps(kmeans_assignments, indent=2),
        encoding="utf-8",
    )
    (out_dir / "cluster_sizes_hdbscan.json").write_text(
        json.dumps(_cluster_sizes(hdbscan_labels), indent=2),
        encoding="utf-8",
    )
    (out_dir / "cluster_sizes_kmeans.json").write_text(
        json.dumps(_cluster_sizes(kmeans_labels), indent=2),
        encoding="utf-8",
    )
    (out_dir / "k_selection.json").write_text(
        json.dumps(
            {
                "selected_k": selected_k,
                "k_selection": k_selection_mode,
                "rows": k_selection_rows,
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    n_components = min(
        PCA_N_COMPONENTS_VIZ, scaled_matrix.shape[0], scaled_matrix.shape[1]
    )
    coords_2d = PCA(n_components=n_components, random_state=seed).fit_transform(
        scaled_matrix
    )
    if coords_2d.shape[1] == 1:
        coords_2d = np.column_stack([coords_2d[:, 0], np.zeros(len(coords_2d))])

    class_hdbscan_png = class_png_dir / PNG_HDBSCAN_NAME
    class_kmeans_png = class_png_dir / PNG_KMEANS_NAME
    _plot_clusters(
        coords_2d,
        hdbscan_labels,
        f"{label_class} HDBSCAN feature clusters",
        class_hdbscan_png,
        noise_gray=True,
    )
    _plot_clusters(
        coords_2d,
        kmeans_labels,
        f"{label_class} KMeans feature clusters (comparison)",
        class_kmeans_png,
        noise_gray=False,
    )
    shutil.copy2(class_hdbscan_png, out_dir / PNG_HDBSCAN_NAME)
    shutil.copy2(class_kmeans_png, out_dir / PNG_KMEANS_NAME)

    metadata = {
        "label_class": label_class,
        "source_embeddings_run_dir": str(source_embeddings_run_dir),
        "seed": seed,
        "scaler": "StandardScaler_fit_all_rows",
        "downstream_method": DOWNSTREAM_METHOD,
        "hdbscan_noise_policy": HDBSCAN_NOISE_POLICY,
        "n_features": len(records),
        "embedding_dim": EMBEDDING_DIMENSIONS,
        "min_cluster_size_requested": min_cluster_size_requested,
        "hdbscan": hdbscan_params,
        "kmeans": {
            "method": "kmeans",
            "selected_k": selected_k,
            "k_selection": k_selection_mode,
            "n_init": KMEANS_N_INIT,
            "max_iter": KMEANS_MAX_ITER,
            "comparison_only": True,
        },
        "class_root_pngs": {
            "hdbscan": str(class_hdbscan_png),
            "kmeans": str(class_kmeans_png),
        },
        "assignments_format": "json",
        "sklearn_HDBSCAN": "sklearn.cluster.HDBSCAN",
    }
    (out_dir / _METADATA_FILENAME).write_text(
        json.dumps(metadata, indent=2),
        encoding="utf-8",
    )
    return out_dir


def run_dual_clustering(
    embeddings_run_dir: Path,
    cluster_output_root: Path,
    class_png_dir: Path,
    label_class: str,
    run_timestamp: str,
    seed: int,
    min_cluster_size: int,
) -> Path:
    """Cluster Stage-2 embeddings with HDBSCAN and KMeans.

    Parameters
    ----------
    embeddings_run_dir
        Stage-2 run directory.
    cluster_output_root
        Class/group Stage-3 root for timestamped artifacts.
    class_png_dir
        Directory for class-root comparison PNGs.
    label_class
        Class or Likert-group label for metadata and plot titles.
    run_timestamp
        Output folder name under ``cluster_output_root``.
    seed
        RNG seed for KMeans / silhouette / PCA.
    min_cluster_size
        Preferred HDBSCAN min_cluster_size (may be lowered for tiny n).

    Returns
    -------
    Path
        Stage-3 run directory.
    """
    matrix, records = load_stage2_embeddings(embeddings_run_dir)
    scaled = StandardScaler().fit_transform(matrix)

    effective_size, min_samples, override_reason = resolve_hdbscan_params(
        matrix.shape[0],
        min_cluster_size,
    )
    hdbscan_labels, hdbscan_params = fit_hdbscan(
        scaled,
        effective_size,
        min_samples,
    )
    if override_reason is not None:
        hdbscan_params["min_cluster_size_override_reason"] = override_reason

    selected_k, k_rows, k_mode = select_k_silhouette(scaled, seed)
    kmeans_labels = fit_kmeans(scaled, selected_k, seed)

    return write_cluster_artifacts(
        cluster_output_root=cluster_output_root,
        class_png_dir=class_png_dir,
        label_class=label_class,
        source_embeddings_run_dir=embeddings_run_dir,
        records=records,
        scaled_matrix=scaled,
        hdbscan_labels=hdbscan_labels,
        hdbscan_params=hdbscan_params,
        kmeans_labels=kmeans_labels,
        selected_k=selected_k,
        k_selection_rows=k_rows,
        k_selection_mode=k_mode,
        seed=seed,
        min_cluster_size_requested=min_cluster_size,
        run_timestamp=run_timestamp,
    )
