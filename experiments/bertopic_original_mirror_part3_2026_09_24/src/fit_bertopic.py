"""Fit BERTopic on deduped Part 3 posts with cached Titan embeddings.

Run from repo root::

    PYTHONPATH=. uv run --extra bertopic python \\
      experiments/bertopic_original_mirror_part3_2026_09_24/src/fit_bertopic.py \\
      --text-role original --sample-pairs 50 --seed 42
"""

from __future__ import annotations

import argparse
import json
import shutil
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd
from bertopic import BERTopic
from hdbscan import HDBSCAN
from sklearn.feature_extraction.text import CountVectorizer
from umap import UMAP

from experiments.bertopic_original_mirror_part3_2026_09_24.src import data as data_mod
from experiments.bertopic_original_mirror_part3_2026_09_24.src import paths
from experiments.bertopic_original_mirror_part3_2026_09_24.src.dedupe import (
    dedupe_stimuli,
    write_dedupe_report,
)
from experiments.bertopic_original_mirror_part3_2026_09_24.src.load_embeddings import (
    EMBEDDINGS_FILENAME,
    INDEX_FILENAME,
)
from shared.embeddings.bedrock import EMBEDDING_DIMENSIONS

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
VECTORIZER_STOP_WORDS = "english"


@dataclass(frozen=True)
class FitCorpus:
    """Documents, embeddings, and ids aligned row for row."""

    docs: list[str]
    embeddings: np.ndarray
    post_ids: list[str]
    text_roles: list[str]


@dataclass(frozen=True)
class FitResult:
    """Paths and counts from one fit."""

    run_dir: Path
    n_docs: int
    n_topics: int
    n_noise: int


def sample_post_ids(post_ids: list[str], n: int, seed: int) -> list[str]:
    """Draw ``n`` post ids without replacement. The returned list is sorted.

    Parameters
    ----------
    post_ids
        Candidate ids.
    n
        Sample size.
    seed
        NumPy Generator seed.

    Returns
    -------
    list[str]
        Sorted sampled ids.

    Raises
    ------
    ValueError
        If ``n`` exceeds the number of ids.
    """
    if n > len(post_ids):
        raise ValueError(f"sample size {n} exceeds corpus size {len(post_ids)}")
    rng = np.random.default_rng(seed)
    chosen = rng.choice(len(post_ids), size=n, replace=False)
    return sorted(post_ids[int(index)] for index in chosen)


def _embeddings_by_post_id(role: str) -> dict[str, np.ndarray]:
    """Load one role cache as a post-id to vector map."""
    cache_dir = paths.embeddings_dir(role)
    embeddings = np.load(cache_dir / EMBEDDINGS_FILENAME)
    index = pd.read_parquet(cache_dir / INDEX_FILENAME)
    if embeddings.shape[1] != EMBEDDING_DIMENSIONS:
        raise ValueError(f"Expected {EMBEDDING_DIMENSIONS}-d embeddings, got {embeddings.shape}")
    return {
        str(post_id): embeddings[int(row_id)]
        for post_id, row_id in zip(index["post_id"].astype(str), index["row_id"])
    }


def _vectors_for_ids(vectors: dict[str, np.ndarray], post_ids: list[str], role: str) -> np.ndarray:
    """Stack vectors for ``post_ids`` in that order."""
    missing = [post_id for post_id in post_ids if post_id not in vectors]
    if missing:
        raise ValueError(f"Missing {role} embeddings for {missing[:5]}")
    return np.vstack([vectors[post_id] for post_id in post_ids])


def assemble_joint_corpus(
    posts: pd.DataFrame,
    original_embeddings: np.ndarray,
    mirror_embeddings: np.ndarray,
) -> FitCorpus:
    """Stack original then mirror rows for each post.

    Parameters
    ----------
    posts
        Deduped stimuli sorted by ``post_id``, with a ``text`` column unused.
    original_embeddings
        Vectors aligned to ``posts`` row order.
    mirror_embeddings
        Vectors aligned to ``posts`` row order.

    Returns
    -------
    FitCorpus
        Two rows per post.
    """
    order = np.argsort(posts["post_id"].to_numpy(), kind="mergesort")
    ordered = posts.iloc[order].reset_index(drop=True)
    original_embeddings = original_embeddings[order]
    mirror_embeddings = mirror_embeddings[order]
    docs: list[str] = []
    roles: list[str] = []
    ids: list[str] = []
    blocks: list[np.ndarray] = []
    for position, row in enumerate(ordered.itertuples(index=False)):
        post_id = str(row.post_id)
        docs.extend([str(row.original_text), str(row.mirror_text)])
        roles.extend(["original", "mirror"])
        ids.extend([post_id, post_id])
        blocks.append(original_embeddings[position])
        blocks.append(mirror_embeddings[position])
    return FitCorpus(docs, np.vstack(blocks), ids, roles)


def load_fit_corpus(role: str) -> tuple[FitCorpus, dict]:
    """Dedupe stimuli and align Titan embeddings for ``role``."""
    stimuli = data_mod.load_stimuli_posts()
    deduped, report = dedupe_stimuli(stimuli)
    deduped = deduped.sort_values("post_id", kind="mergesort").reset_index(drop=True)
    post_ids = deduped["post_id"].astype(str).tolist()
    if role == "joint":
        original_vectors = _embeddings_by_post_id("original")
        mirror_vectors = _embeddings_by_post_id("mirror")
        corpus = assemble_joint_corpus(
            deduped,
            _vectors_for_ids(original_vectors, post_ids, "original"),
            _vectors_for_ids(mirror_vectors, post_ids, "mirror"),
        )
        return corpus, report
    column = data_mod.select_text_column(role)
    vectors = _embeddings_by_post_id(role)
    corpus = FitCorpus(
        docs=deduped[column].astype(str).tolist(),
        embeddings=_vectors_for_ids(vectors, post_ids, role),
        post_ids=post_ids,
        text_roles=[role] * len(post_ids),
    )
    return corpus, report


def subset_corpus(corpus: FitCorpus, post_ids: list[str]) -> FitCorpus:
    """Keep rows whose post id is in ``post_ids``, preserving order."""
    keep = set(post_ids)
    positions = [index for index, post_id in enumerate(corpus.post_ids) if post_id in keep]
    return FitCorpus(
        docs=[corpus.docs[index] for index in positions],
        embeddings=corpus.embeddings[positions],
        post_ids=[corpus.post_ids[index] for index in positions],
        text_roles=[corpus.text_roles[index] for index in positions],
    )


def min_cluster_size_for(sample_pairs: int | None) -> int:
    """Return 5 for a smoke sample and 15 for a full fit."""
    if sample_pairs is None:
        return DEFAULT_MIN_CLUSTER_SIZE
    return SMOKE_MIN_CLUSTER_SIZE


def build_topic_model(min_cluster_size: int, seed: int) -> BERTopic:
    """Construct BERTopic with the Part 2 hyperparameters."""
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
    vectorizer_model = CountVectorizer(stop_words=VECTORIZER_STOP_WORDS, min_df=VECTORIZER_MIN_DF)
    return BERTopic(
        embedding_model=None,
        umap_model=umap_model,
        hdbscan_model=hdbscan_model,
        vectorizer_model=vectorizer_model,
        calculate_probabilities=True,
        verbose=True,
    )


def fit_viz_umap(embeddings: np.ndarray, seed: int) -> np.ndarray:
    """Fit a 2-D UMAP for plots. This projection is not the fit UMAP."""
    reducer = UMAP(
        n_neighbors=min(UMAP_N_NEIGHBORS, len(embeddings) - 1),
        n_components=UMAP_N_COMPONENTS_VIZ,
        min_dist=UMAP_MIN_DIST,
        metric=UMAP_METRIC,
        random_state=seed,
    )
    return np.asarray(reducer.fit_transform(embeddings), dtype=np.float64)


def max_topic_probability(probabilities: np.ndarray | None, n_docs: int) -> list[float | None]:
    """Return the max topic probability per document."""
    if probabilities is None:
        return [None] * n_docs
    array = np.asarray(probabilities)
    if array.ndim == 1:
        return [float(value) for value in array]
    return [float(value) for value in array.max(axis=1)]


def _hyperparameter_metadata(seed: int, min_cluster_size: int) -> dict:
    """Return the UMAP, HDBSCAN, and vectorizer settings used for a fit."""
    return {
        "umap": {
            "n_neighbors": UMAP_N_NEIGHBORS,
            "n_components": UMAP_N_COMPONENTS_FIT,
            "min_dist": UMAP_MIN_DIST,
            "metric": UMAP_METRIC,
            "random_state": seed,
        },
        "hdbscan": {
            "min_cluster_size": min_cluster_size,
            "metric": HDBSCAN_METRIC,
            "cluster_selection_method": HDBSCAN_SELECTION,
        },
        "vectorizer": {"stop_words": VECTORIZER_STOP_WORDS, "min_df": VECTORIZER_MIN_DF},
    }


def run_fit_bertopic(role: str, sample_pairs: int | None, seed: int) -> FitResult:
    """Fit one role and write a timestamped topics run.

    Parameters
    ----------
    role
        ``original``, ``mirror``, or ``joint``.
    sample_pairs
        When set, fit only this many post ids. Joint keeps both rows.
    seed
        Sampling and UMAP seed.

    Returns
    -------
    FitResult
        Run directory and counts.
    """
    validated = paths.require_text_role(role)
    corpus, report = load_fit_corpus(validated)
    sample_ids = None
    if sample_pairs is not None:
        unique_ids = sorted(set(corpus.post_ids))
        sample_ids = sample_post_ids(unique_ids, sample_pairs, seed)
        corpus = subset_corpus(corpus, sample_ids)
    min_cluster_size = min_cluster_size_for(sample_pairs)
    topic_model = build_topic_model(min_cluster_size, seed)
    topics, probabilities = topic_model.fit_transform(corpus.docs, corpus.embeddings)
    topics_array = np.asarray(topics)
    umap_2d = fit_viz_umap(corpus.embeddings, seed)
    n_docs = len(corpus.docs)
    n_noise = int((topics_array == -1).sum())
    n_topics = len({int(topic) for topic in topics_array if int(topic) != -1})
    run_dir = paths.topics_dir(validated) / paths.new_run_timestamp()
    _write_fit_artifacts(
        run_dir,
        corpus,
        topics_array,
        max_topic_probability(probabilities, n_docs),
        probabilities,
        umap_2d,
        topic_model,
        report,
        validated,
        sample_ids,
        seed,
        min_cluster_size,
        n_topics,
        n_noise,
    )
    print(f"topics_run_dir={run_dir}")
    print(f"n_docs={n_docs} n_topics={n_topics} n_noise={n_noise}")
    return FitResult(run_dir, n_docs, n_topics, n_noise)


def _write_fit_artifacts(
    run_dir: Path,
    corpus: FitCorpus,
    topics: np.ndarray,
    probabilities: list[float | None],
    raw_probabilities: np.ndarray | None,
    umap_2d: np.ndarray,
    topic_model: BERTopic,
    report: dict,
    role: str,
    sample_ids: list[str] | None,
    seed: int,
    min_cluster_size: int,
    n_topics: int,
    n_noise: int,
) -> None:
    """Write assignments, topic info, model, and metadata for one run."""
    run_dir.mkdir(parents=True, exist_ok=True)
    assignments = pd.DataFrame(
        {
            "post_id": corpus.post_ids,
            "pair_post_id": corpus.post_ids,
            "text_role": corpus.text_roles,
            "topic": [int(topic) for topic in topics],
            "probability": probabilities,
        }
    )
    if role == "joint":
        assignments.insert(0, "row_id", np.arange(len(assignments), dtype=np.int64))
    assignments.to_parquet(run_dir / "assignments.parquet", index=False)
    topic_model.get_topic_info().to_parquet(run_dir / "topic_info.parquet", index=False)
    np.save(run_dir / "umap_2d.npy", umap_2d)
    if raw_probabilities is not None:
        np.save(run_dir / "probabilities.npy", np.asarray(raw_probabilities))
    topic_model.save(
        str(run_dir / "model"),
        serialization="safetensors",
        save_ctfidf=True,
        save_embedding_model=False,
    )
    write_dedupe_report(paths.dedupe_report_path(), report)
    shutil.copy(paths.dedupe_report_path(), run_dir / "dedupe_report.json")
    metadata = {
        "text_role": role,
        "sample_post_ids": sample_ids,
        "seed": seed,
        "dedupe_report_path": str(paths.dedupe_report_path()),
        "n_docs": len(corpus.docs),
        "n_topics": n_topics,
        "n_noise": n_noise,
        "llm_used": False,
        **_hyperparameter_metadata(seed, min_cluster_size),
    }
    (run_dir / "metadata.json").write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    """CLI entry for a Part 3 BERTopic fit."""
    parser = argparse.ArgumentParser(description="Fit BERTopic on a Part 3 text role.")
    parser.add_argument("--text-role", choices=["original", "mirror", "joint"], required=True)
    parser.add_argument("--sample-pairs", type=int, default=None)
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    args = parser.parse_args()
    run_fit_bertopic(args.text_role, args.sample_pairs, args.seed)


if __name__ == "__main__":
    main()
