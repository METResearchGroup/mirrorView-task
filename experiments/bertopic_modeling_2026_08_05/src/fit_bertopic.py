"""Stage 2: fit BERTopic on original posts with precomputed Titan embeddings.

No LLM in this stage. Passes Titan vectors into ``fit_transform`` with
``embedding_model=None``.

Run from repo root::

    PYTHONPATH=. uv run --extra bertopic python \\
      experiments/bertopic_modeling_2026_08_05/src/fit_bertopic.py --sample-size 50 --seed 42

    PYTHONPATH=. uv run --extra bertopic python \\
      experiments/bertopic_modeling_2026_08_05/src/fit_bertopic.py
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd
from bertopic import BERTopic
from hdbscan import HDBSCAN
from sklearn.feature_extraction.text import CountVectorizer
from umap import UMAP

from experiments.bertopic_modeling_2026_08_05.src import data as data_mod
from experiments.bertopic_modeling_2026_08_05.src import paths
from shared.embeddings.bedrock import BEDROCK_MODEL_ID, EMBEDDING_DIMENSIONS

TEXT_ROLE = paths.TEXT_ROLE_V1
DEFAULT_SEED = 42
DEFAULT_MIN_CLUSTER_SIZE = 15
SMOKE_MIN_CLUSTER_SIZE = 5
UMAP_N_NEIGHBORS = 15
UMAP_N_COMPONENTS_FIT = 5
UMAP_N_COMPONENTS_VIZ = 2
UMAP_MIN_DIST = 0.0
UMAP_METRIC = "cosine"
HDBSCAN_METRIC = "euclidean"
HDBSCAN_SELECTION = "eom"
VECTORIZER_MIN_DF = 2


@dataclass(frozen=True)
class FitResult:
    """Paths and counts from a Stage-2 fit run."""

    run_dir: Path
    n_docs: int
    n_topics: int
    n_noise: int


def _load_aligned_corpus() -> tuple[list[str], np.ndarray, list[str]]:
    """Load cache + original_text aligned by message_id order in the index."""
    cache_dir = paths.embeddings_dir(TEXT_ROLE)
    emb_path = cache_dir / "embeddings.npy"
    index_path = cache_dir / "index.parquet"
    if not emb_path.is_file() or not index_path.is_file():
        raise FileNotFoundError(
            f"Missing Stage-1 cache under {cache_dir}. Run load_embeddings.py first."
        )

    embeddings = np.load(emb_path)
    index = pd.read_parquet(index_path)
    if embeddings.shape != (len(index), EMBEDDING_DIMENSIONS):
        raise ValueError(
            f"Cache shape mismatch: embeddings={embeddings.shape} index_rows={len(index)}"
        )

    posts = data_mod.load_keep_remove_posts()
    text_by_id = {
        str(row.message_id): str(row.original_text)
        for row in posts.itertuples(index=False)
    }
    message_ids = index["message_id"].astype(str).tolist()
    missing = [mid for mid in message_ids if mid not in text_by_id]
    if missing:
        raise ValueError(
            f"Cache message_ids missing from dataset: n={len(missing)} examples={missing[:5]}"
        )
    docs = [text_by_id[mid] for mid in message_ids]
    return docs, embeddings, message_ids


def _sample_rows(
    docs: list[str],
    embeddings: np.ndarray,
    message_ids: list[str],
    sample_size: int,
    seed: int,
) -> tuple[list[str], np.ndarray, list[str]]:
    """Sample rows without replacement; return aligned docs/embeddings/ids."""
    n = len(message_ids)
    if sample_size > n:
        raise ValueError(f"sample_size={sample_size} exceeds corpus size n={n}")
    rng = np.random.default_rng(seed)
    chosen = rng.choice(n, size=sample_size, replace=False)
    chosen.sort()
    docs_out = [docs[i] for i in chosen]
    ids_out = [message_ids[i] for i in chosen]
    emb_out = embeddings[chosen]
    return docs_out, emb_out, ids_out


def _resolve_min_cluster_size(sample_size: int | None) -> int:
    """Production default 15; smoke (--sample-size 50) uses 5."""
    if sample_size is None:
        return DEFAULT_MIN_CLUSTER_SIZE
    return SMOKE_MIN_CLUSTER_SIZE


def _build_topic_model(min_cluster_size: int, seed: int) -> BERTopic:
    """Construct BERTopic with README defaults and embedding_model=None."""
    umap_model = UMAP(
        n_neighbors=UMAP_N_NEIGHBORS,
        n_components=UMAP_N_COMPONENTS_FIT,
        min_dist=UMAP_MIN_DIST,
        metric=UMAP_METRIC,
        random_state=seed,
    )
    hdbscan_model = HDBSCAN(
        min_cluster_size=min_cluster_size,
        metric=HDBSCAN_METRIC,
        cluster_selection_method=HDBSCAN_SELECTION,
        prediction_data=True,
    )
    vectorizer_model = CountVectorizer(
        stop_words="english",
        min_df=VECTORIZER_MIN_DF,
    )
    return BERTopic(
        embedding_model=None,
        umap_model=umap_model,
        hdbscan_model=hdbscan_model,
        vectorizer_model=vectorizer_model,
        calculate_probabilities=True,
        verbose=True,
    )


def _fit_viz_umap(embeddings: np.ndarray, seed: int) -> np.ndarray:
    """Fit a separate 2-D UMAP for visualization overlays."""
    reducer = UMAP(
        n_neighbors=UMAP_N_NEIGHBORS,
        n_components=UMAP_N_COMPONENTS_VIZ,
        min_dist=UMAP_MIN_DIST,
        metric=UMAP_METRIC,
        random_state=seed,
    )
    return reducer.fit_transform(embeddings)


def run_fit_bertopic(
    sample_size: int | None,
    seed: int,
) -> FitResult:
    """Fit BERTopic and write timestamped topics artifacts.

    Parameters
    ----------
    sample_size
        When set, fit on a seeded sample of this many posts. When None, fit
        on the full Stage-1 cache.
    seed
        RNG seed for sampling and UMAP ``random_state``.

    Returns
    -------
    FitResult
        Run directory and topic/noise counts.
    """
    docs, embeddings, message_ids = _load_aligned_corpus()
    if sample_size is not None:
        docs, embeddings, message_ids = _sample_rows(
            docs, embeddings, message_ids, sample_size, seed
        )

    min_cluster_size = _resolve_min_cluster_size(sample_size)
    topic_model = _build_topic_model(min_cluster_size=min_cluster_size, seed=seed)
    topics, probs = topic_model.fit_transform(docs, embeddings)
    umap_2d = _fit_viz_umap(embeddings, seed=seed)

    topics_arr = np.asarray(topics)
    n_docs = len(message_ids)
    n_noise = int((topics_arr == -1).sum())
    n_topics = int(len({int(t) for t in topics_arr if int(t) != -1}))

    max_probs: list[float | None]
    if probs is None:
        max_probs = [None] * n_docs
    else:
        probs_arr = np.asarray(probs)
        if probs_arr.ndim == 1:
            max_probs = [float(x) for x in probs_arr]
        else:
            max_probs = [float(x) for x in probs_arr.max(axis=1)]

    run_dir = paths.topics_dir(TEXT_ROLE) / paths.new_run_timestamp()
    run_dir.mkdir(parents=True, exist_ok=True)

    assignments = pd.DataFrame(
        {
            "message_id": message_ids,
            "topic": [int(t) for t in topics_arr],
            "probability": max_probs,
        }
    )
    assignments.to_parquet(run_dir / "assignments.parquet", index=False)

    topic_info = topic_model.get_topic_info()
    topic_info.to_parquet(run_dir / "topic_info.parquet", index=False)

    np.save(run_dir / "umap_2d.npy", np.asarray(umap_2d, dtype=np.float64))
    if probs is not None:
        np.save(run_dir / "probabilities.npy", np.asarray(probs))

    model_dir = run_dir / "model"
    topic_model.save(
        str(model_dir),
        serialization="safetensors",
        save_ctfidf=True,
        save_embedding_model=False,
    )

    metadata = {
        "text_role": TEXT_ROLE,
        "sample_size": sample_size,
        "seed": seed,
        "message_ids": message_ids,
        "n_docs": n_docs,
        "n_topics": n_topics,
        "n_noise": n_noise,
        "llm_used": False,
        "embedding_cache_path": str(paths.embeddings_dir(TEXT_ROLE)),
        "model_id": BEDROCK_MODEL_ID,
        "dimensions": EMBEDDING_DIMENSIONS,
        "unanimous_rule_id": None,
        "umap": {
            "n_neighbors": UMAP_N_NEIGHBORS,
            "n_components": UMAP_N_COMPONENTS_FIT,
            "min_dist": UMAP_MIN_DIST,
            "metric": UMAP_METRIC,
            "random_state": seed,
        },
        "umap_2d": {
            "n_neighbors": UMAP_N_NEIGHBORS,
            "n_components": UMAP_N_COMPONENTS_VIZ,
            "min_dist": UMAP_MIN_DIST,
            "metric": UMAP_METRIC,
            "random_state": seed,
        },
        "hdbscan": {
            "min_cluster_size": min_cluster_size,
            "metric": HDBSCAN_METRIC,
            "cluster_selection_method": HDBSCAN_SELECTION,
            "prediction_data": True,
        },
        "vectorizer": {
            "stop_words": "english",
            "min_df": VECTORIZER_MIN_DF,
        },
        "bertopic": {
            "embedding_model": None,
            "calculate_probabilities": True,
        },
        "probabilities_shape": None if probs is None else list(np.asarray(probs).shape),
    }
    (run_dir / "metadata.json").write_text(
        json.dumps(metadata, indent=2) + "\n",
        encoding="utf-8",
    )

    print(f"topics_run_dir={run_dir}")
    print(f"n_docs={n_docs} n_topics={n_topics} n_noise={n_noise}")
    return FitResult(
        run_dir=run_dir,
        n_docs=n_docs,
        n_topics=n_topics,
        n_noise=n_noise,
    )


def main() -> None:
    """CLI entrypoint for Stage 2."""
    parser = argparse.ArgumentParser(
        description="Fit BERTopic on original posts with Titan embeddings (no LLM)."
    )
    parser.add_argument(
        "--sample-size",
        type=int,
        default=None,
        help="Optional sample size for smoke runs (e.g. 50). Omit for full corpus.",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=DEFAULT_SEED,
        help=f"RNG seed (default {DEFAULT_SEED}).",
    )
    args = parser.parse_args()
    run_fit_bertopic(sample_size=args.sample_size, seed=args.seed)


if __name__ == "__main__":
    main()
