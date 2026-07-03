from __future__ import annotations

import argparse
import json
import math
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

REPO_ROOT = Path(__file__).resolve().parents[2]

# Imports are repo-local; keep this script runnable directly.
import sys

sys.path.insert(0, str(REPO_ROOT))

from lib.timestamp_utils import get_current_timestamp  # noqa: E402

from experiments.predict_keep_remove_2026_07_01.dataloader import Dataloader
from experiments.simplified_predict_remove_2026_05_13.experiment_bedrock_embeddings import (
    BEDROCK_MODEL_ID,
    EMBEDDING_DIMENSIONS,
)
from lib.aws.embedding_identity import embedding_identity_sha256


@dataclass(frozen=True)
class CosineHistogramResult:
    mean_cosine: float
    mean_cosine_sigfigs_3: str
    output_png_path: Path
    output_json_path: Path


def _load_embedding(cache_dir: Path, embedding_id: str) -> np.ndarray:
    path = cache_dir / "embeddings" / f"{embedding_id}.npy"
    if not path.exists():
        raise FileNotFoundError(f"Missing embedding cache file: {path}")
    return np.load(path).astype(np.float64, copy=False).ravel()


def _cosine(u: np.ndarray, v: np.ndarray) -> float:
    # Robust cosine (works even if vectors are not perfectly normalized).
    denom = float(np.linalg.norm(u) * np.linalg.norm(v))
    if denom == 0.0:
        return 0.0
    return float(np.dot(u, v) / denom)


def _loess_smooth_1d(x: np.ndarray, y: np.ndarray, x_eval: np.ndarray, *, frac: float) -> np.ndarray:
    """
    Simple LOESS (degree-1) smoothing.

    This is O(n*m) where n=len(x), m=len(x_eval). Here n is histogram bins, so it's fine.
    """
    if x.ndim != 1 or y.ndim != 1:
        raise ValueError("x and y must be 1D arrays")
    if len(x) != len(y):
        raise ValueError("x and y must be same length")
    if len(x) < 2:
        raise ValueError("Need at least 2 points for LOESS")
    if not (0.05 <= frac <= 1.0):
        raise ValueError("frac must be in [0.05, 1.0]")

    n = len(x)
    k = max(2, int(math.ceil(frac * n)))

    x = x.astype(np.float64)
    y = y.astype(np.float64)
    x_eval = x_eval.astype(np.float64)

    # Ensure monotonic x for neighborhood selection stability.
    order = np.argsort(x)
    x_sorted = x[order]
    y_sorted = y[order]

    out = np.zeros_like(x_eval, dtype=np.float64)

    for i, xe in enumerate(x_eval):
        # Nearest k points by absolute distance.
        d = np.abs(x_sorted - xe)
        idx = np.argpartition(d, kth=k - 1)[:k]

        xk = x_sorted[idx]
        yk = y_sorted[idx]
        dk = d[idx]

        max_d = float(np.max(dk))
        if max_d == 0.0:
            out[i] = float(np.mean(yk))
            continue

        # Tricube kernel weights.
        w = (1.0 - (dk / max_d) ** 3) ** 3

        # Weighted linear regression around xe: y ~ b0 + b1*(x - xe)
        x_centered = xk - xe

        S0 = float(np.sum(w))
        if S0 == 0.0:
            out[i] = float(np.mean(yk))
            continue

        S1 = float(np.sum(w * x_centered))
        S2 = float(np.sum(w * x_centered**2))

        T0 = float(np.sum(w * yk))
        T1 = float(np.sum(w * yk * x_centered))

        denom = S0 * S2 - S1 * S1
        if abs(denom) < 1e-15:
            out[i] = T0 / S0
            continue

        b1 = (S0 * T1 - S1 * T0) / denom
        b0 = (T0 - b1 * S1) / S0

        out[i] = float(b0)  # prediction at x=xe

    return out


def _compute_cosine_similarities_for_study2(*, cache_dir: Path) -> list[float]:
    loader = Dataloader()
    train_df = loader.load_training_dataframe()

    if not {"original_text", "mirror_text"}.issubset(set(train_df.columns)):
        raise KeyError("Expected columns `original_text` and `mirror_text` in training dataframe.")

    model_id = BEDROCK_MODEL_ID
    dimensions = EMBEDDING_DIMENSIONS
    normalize = True

    cos_sims: list[float] = []
    embedding_cache: dict[str, np.ndarray] = {}

    for _, row in train_df.iterrows():
        ot = str(row["original_text"])
        mt = str(row["mirror_text"])

        eid_o = embedding_identity_sha256(ot, model_id=model_id, dimensions=dimensions, normalize=normalize)
        eid_m = embedding_identity_sha256(mt, model_id=model_id, dimensions=dimensions, normalize=normalize)

        if eid_o in embedding_cache:
            vo = embedding_cache[eid_o]
        else:
            vo = _load_embedding(cache_dir, eid_o)
            embedding_cache[eid_o] = vo

        if eid_m in embedding_cache:
            vm = embedding_cache[eid_m]
        else:
            vm = _load_embedding(cache_dir, eid_m)
            embedding_cache[eid_m] = vm

        cos_sims.append(_cosine(vo, vm))

    return cos_sims


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--outputs-name",
        type=str,
        default="cosine_similarity_histogram",
        help="Subfolder under outputs/ to write results.json and results.png.",
    )
    parser.add_argument(
        "--embedding-cache-dir",
        type=str,
        default=str(Path(__file__).resolve().parent / "embedding_cache"),
        help="Path to embedding_cache directory containing `embeddings/*.npy`.",
    )
    parser.add_argument(
        "--bins",
        type=int,
        default=30,
        help="Number of histogram bins.",
    )
    parser.add_argument(
        "--loess-frac",
        type=float,
        default=0.35,
        help="LOESS neighborhood fraction for smoothing the histogram curve.",
    )
    args = parser.parse_args()

    cache_dir = Path(args.embedding_cache_dir)
    embeddings_path = cache_dir / "embeddings"
    if not embeddings_path.exists():
        raise FileNotFoundError(f"Missing embeddings dir: {embeddings_path}")

    cos_sims = _compute_cosine_similarities_for_study2(cache_dir=cache_dir)
    cos_arr = np.asarray(cos_sims, dtype=np.float64)

    mean_cosine = float(np.mean(cos_arr))
    mean_cosine_sigfigs_3 = f"{mean_cosine:.3g}"

    # Create output dir
    ts = get_current_timestamp()
    out_dir = Path(__file__).resolve().parent / "outputs" / args.outputs_name / ts
    out_dir.mkdir(parents=True, exist_ok=False)

    # Histogram + smoothing.
    # Cosine similarity is typically in [-1, 1] for normalized vectors.
    hist_range = (-1.0, 1.0)
    counts, edges = np.histogram(cos_arr, bins=args.bins, range=hist_range, density=False)
    bin_width = float(edges[1] - edges[0])
    density = counts.astype(np.float64) / (len(cos_arr) * bin_width)  # density so integrates to ~1
    bin_centers = (edges[:-1] + edges[1:]) / 2.0

    density_smooth = _loess_smooth_1d(bin_centers, density, bin_centers, frac=args.loess_frac)

    # Plot
    fig, ax = plt.subplots(figsize=(10, 6))

    ax.bar(
        bin_centers,
        density,
        width=bin_width * 0.95,
        color="#1f77b4",
        alpha=0.35,
        edgecolor="#1f77b4",
        linewidth=0.6,
        label="Histogram",
    )
    ax.plot(bin_centers, density_smooth, color="#1f77b4", linewidth=2, label="LOESS smoothing")

    ax.axvline(mean_cosine, color="red", linestyle="--", linewidth=2, label=f"Mean = {mean_cosine_sigfigs_3}")

    ax.set_title(
        "Average cosine similarity between a post and its mirror\n(Higher is better)",
        fontsize=14,
    )
    ax.set_xlabel("Cosine similarity (post vs mirror embeddings)")
    ax.set_ylabel("Density")

    # Keep it readable.
    ax.grid(True, axis="y", alpha=0.25)

    # Use the mean line legend only; avoid extra clutter.
    ax.legend(loc="best", fontsize=9)

    fig.tight_layout()

    results_png_path = out_dir / "results.png"
    fig.savefig(results_png_path, dpi=200)

    results_json = {
        "source": "computed from local embedding_cache/*.npy",
        "embedding_cache_dir": str(cache_dir),
        "model_id": BEDROCK_MODEL_ID,
        "dimensions": EMBEDDING_DIMENSIONS,
        "normalize": True,
        "bins": args.bins,
        "loess_frac": args.loess_frac,
        "mean_cosine": mean_cosine,
        "mean_cosine_sigfigs_3": mean_cosine_sigfigs_3,
        "n": len(cos_arr),
        "output": {"results_png_path": str(results_png_path)},
    }
    results_json_path = out_dir / "results.json"
    results_json_path.write_text(json.dumps(results_json, indent=2), encoding="utf-8")

    print("Wrote:", results_json_path)
    print("Wrote:", results_png_path)


if __name__ == "__main__":
    main()

