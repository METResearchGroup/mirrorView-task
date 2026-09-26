"""Compare a fit before and after embedding-based outlier reduction."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from experiments.bertopic_original_mirror_part3_2026_09_24.src import data as data_mod
from experiments.bertopic_original_mirror_part3_2026_09_24.src import paths
from experiments.bertopic_original_mirror_part3_2026_09_24.src.ablations.a3_minilm import aligned_spearman
from experiments.bertopic_original_mirror_part3_2026_09_24.src.ablations.fitting import (
    fit_topics,
    original_corpus,
    topic_counts,
    write_assignments,
)
from experiments.bertopic_original_mirror_part3_2026_09_24.src.load_embeddings import (
    EMBEDDINGS_FILENAME,
    INDEX_FILENAME,
)
from experiments.bertopic_original_mirror_part3_2026_09_24.src.outcomes import load_outcome_corpus

FIT_SEED = 42
PRODUCTION_MIN_CLUSTER_SIZE = 15


def _rate_map(assignments: pd.DataFrame, labels: pd.DataFrame) -> dict[int, float]:
    from experiments.bertopic_original_mirror_part3_2026_09_24.src.ablations.a3_minilm import _rate_map as rate_map

    return rate_map(assignments, labels)


def run_a5_outliers(output_dir: Path, production_run: Path) -> dict:
    """Fit once, then reassign noise documents with ``strategy='embeddings'``."""
    corpus = original_corpus()
    _model, before, after = fit_topics(
        corpus.docs,
        corpus.embeddings,
        FIT_SEED,
        PRODUCTION_MIN_CLUSTER_SIZE,
        reduce_outliers=True,
    )
    output_dir.mkdir(parents=True, exist_ok=True)
    write_assignments(output_dir / "assignments_off.parquet", corpus.post_ids, before)
    write_assignments(output_dir / "assignments_on.parquet", corpus.post_ids, after)
    _topics_off, noise_off, share_off = topic_counts(before)
    n_topics, noise_on, share_on = topic_counts(after)
    production = pd.read_parquet(production_run / "assignments.parquet")
    production = production.loc[production["text_role"] == "original", ["post_id", "topic"]]
    labels = load_outcome_corpus(data_mod.load_keep_remove_posts(), min_raters=3)
    on_assignments = pd.DataFrame({"post_id": corpus.post_ids, "topic": [int(topic) for topic in after]})
    cache = paths.embeddings_dir("original")
    matrix = np.load(cache / EMBEDDINGS_FILENAME)
    index = pd.read_parquet(cache / INDEX_FILENAME)
    vectors = {str(row.post_id): matrix[int(row.row_id)] for row in index.itertuples(index=False)}
    rho, _mapping = aligned_spearman(
        production,
        on_assignments,
        vectors,
        _rate_map(production, labels),
        _rate_map(on_assignments, labels),
    )
    payload = {
        "n_topics": n_topics,
        "noise_off": noise_off,
        "noise_on": noise_on,
        "noise_share_off": share_off,
        "noise_share_on": share_on,
        "spearman_q5_keep_rate": rho,
    }
    (output_dir / "noise_comparison.json").write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return payload
