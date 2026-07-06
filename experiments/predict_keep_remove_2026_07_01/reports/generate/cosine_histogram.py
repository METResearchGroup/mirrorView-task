"""Histogram of cosine similarity between original and mirrored post embeddings."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

from experiments.predict_keep_remove_2026_07_01.data.dataloader import Dataloader
from experiments.predict_keep_remove_2026_07_01.reports.paths import (
    DEFAULT_EMBEDDING_CACHE_DIR,
    make_output_dir,
)
from experiments.simplified_predict_remove_2026_05_13.experiment_bedrock_embeddings import (
    BEDROCK_MODEL_ID,
    EMBEDDING_DIMENSIONS,
)
from lib.aws.embedding_identity import embedding_identity_sha256


def _load_embedding(cache_dir: Path, embedding_id: str) -> np.ndarray:
    path = cache_dir / "embeddings" / f"{embedding_id}.npy"
    if not path.exists():
        raise FileNotFoundError(f"Missing embedding cache file: {path}")
    return np.load(path).astype(np.float64, copy=False).ravel()


def _cosine(u: np.ndarray, v: np.ndarray) -> float:
    denom = float(np.linalg.norm(u) * np.linalg.norm(v))
    if denom == 0.0:
        return 0.0
    return float(np.dot(u, v) / denom)


def compute_cosine_similarities(*, cache_dir: Path) -> list[float]:
    train_df = Dataloader().load_training_dataframe()
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
        help="Subfolder under reports/outputs/ to write results.json and results.png.",
    )
    parser.add_argument(
        "--embedding-cache-dir",
        type=str,
        default=str(DEFAULT_EMBEDDING_CACHE_DIR),
        help="Path to embedding_cache directory containing `embeddings/*.npy`.",
    )
    parser.add_argument(
        "--bins",
        type=int,
        default=30,
        help="Number of histogram bins.",
    )
    args = parser.parse_args()

    cache_dir = Path(args.embedding_cache_dir)
    embeddings_path = cache_dir / "embeddings"
    if not embeddings_path.exists():
        raise FileNotFoundError(f"Missing embeddings dir: {embeddings_path}")

    cos_sims = compute_cosine_similarities(cache_dir=cache_dir)
    cos_arr = np.asarray(cos_sims, dtype=np.float64)

    mean_cosine = float(np.mean(cos_arr))
    mean_cosine_sigfigs_3 = f"{mean_cosine:.3g}"

    out_dir = make_output_dir(args.outputs_name)

    hist_range = (-1.0, 1.0)
    counts, edges = np.histogram(cos_arr, bins=args.bins, range=hist_range, density=False)
    bin_width = float(edges[1] - edges[0])
    density = counts.astype(np.float64) / (len(cos_arr) * bin_width)
    bin_centers = (edges[:-1] + edges[1:]) / 2.0

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
    ax.axvline(mean_cosine, color="red", linestyle="--", linewidth=2, label="Mean cosine similarity")
    ax.set_title(
        "Average cosine similarity between a post and its mirror\n(Higher is better)",
        fontsize=14,
    )
    ax.set_xlabel("Cosine similarity (post vs mirror embeddings)")
    ax.set_ylabel("Density")
    ax.grid(True, axis="y", alpha=0.25)
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
