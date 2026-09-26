"""One original-role BERTopic fit used by the ablation runners."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
from bertopic import BERTopic

from experiments.bertopic_original_mirror_part3_2026_09_24.src.fit_bertopic import (
    FitCorpus,
    build_topic_model,
    load_fit_corpus,
)

NOISE_TOPIC_ID = -1


def original_corpus() -> FitCorpus:
    """Deduped original-role documents and Titan embeddings."""
    corpus, _report = load_fit_corpus("original")
    return corpus


def fit_topics(
    docs: list[str],
    embeddings: np.ndarray,
    seed: int,
    min_cluster_size: int,
    reduce_outliers: bool = False,
) -> tuple[BERTopic, np.ndarray, np.ndarray]:
    """Fit BERTopic and optionally reassign noise with the embedding strategy.

    Returns the model, topics before outlier reduction, and topics after.
    When reduction is off, the two topic arrays are the same object.
    """
    model = build_topic_model(min_cluster_size, seed)
    topics, _probabilities = model.fit_transform(docs, embeddings)
    before = np.asarray(topics)
    if not reduce_outliers:
        return model, before, before
    reduced = model.reduce_outliers(
        docs,
        before.tolist(),
        strategy="embeddings",
        embeddings=embeddings,
    )
    return model, before, np.asarray(reduced)


def topic_counts(topics: np.ndarray) -> tuple[int, int, float]:
    """Non-noise topic count, noise count, and noise share."""
    n_noise = int((topics == NOISE_TOPIC_ID).sum())
    n_topics = len({int(topic) for topic in topics if int(topic) != NOISE_TOPIC_ID})
    share = float(n_noise / len(topics)) if len(topics) else float("nan")
    return n_topics, n_noise, share


def write_assignments(path: Path, post_ids: list[str], topics: np.ndarray) -> None:
    """Write ``post_id`` and ``topic`` for one ablation fit."""
    path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame({"post_id": post_ids, "topic": [int(topic) for topic in topics]}).to_parquet(path, index=False)
