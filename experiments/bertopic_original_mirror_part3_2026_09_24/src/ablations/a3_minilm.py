"""Fit the original corpus with MiniLM embeddings instead of Titan."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from experiments.bertopic_original_mirror_part3_2026_09_24.src import paths
from experiments.bertopic_original_mirror_part3_2026_09_24.src.ablations.fitting import (
    fit_topics,
    original_corpus,
    topic_counts,
    write_assignments,
)
from experiments.bertopic_original_mirror_part3_2026_09_24.src.ablations.summary import spearman_q5_keep_rate
from experiments.bertopic_original_mirror_part3_2026_09_24.src.analyze_cross_role import (
    centroids_for_assignments,
    match_topics_hungarian,
)
from experiments.bertopic_original_mirror_part3_2026_09_24.src.load_embeddings import (
    EMBEDDINGS_FILENAME,
    INDEX_FILENAME,
)
from experiments.bertopic_original_mirror_part3_2026_09_24.src.outcomes import (
    load_outcome_corpus,
    summarize_outcomes_by_topic,
)
from experiments.bertopic_original_mirror_part3_2026_09_24.src import data as data_mod

FIT_SEED = 42
PRODUCTION_MIN_CLUSTER_SIZE = 15
NOISE_TOPIC_ID = -1
RANK_EDGE = 5


def minilm_matrix(post_ids: list[str]) -> np.ndarray:
    """MiniLM rows aligned to ``post_ids``."""
    cache = paths.embeddings_minilm_dir("original")
    matrix = np.load(cache / EMBEDDINGS_FILENAME)
    index = pd.read_parquet(cache / INDEX_FILENAME)
    by_id = {str(row.post_id): matrix[int(row.row_id)] for row in index.itertuples(index=False)}
    return np.vstack([by_id[post_id] for post_id in post_ids])


def aligned_spearman(
    production_assignments: pd.DataFrame,
    ablation_assignments: pd.DataFrame,
    vectors: dict[str, np.ndarray],
    production_rates: dict[int, float],
    ablation_rates: dict[int, float],
) -> tuple[float, dict[int, int]]:
    """Spearman of keep rates after matching topics on centroid cosine."""
    production_ids, production_centroids = centroids_for_assignments(production_assignments, vectors)
    ablation_ids, ablation_centroids = centroids_for_assignments(ablation_assignments, vectors)
    mapping = match_topics_hungarian(
        production_centroids @ ablation_centroids.T,
        production_ids,
        ablation_ids,
    )
    left = []
    right = []
    for production_topic, ablation_topic in mapping.items():
        if production_topic not in production_rates or ablation_topic not in ablation_rates:
            continue
        left.append(production_rates[production_topic])
        right.append(ablation_rates[ablation_topic])
    return spearman_q5_keep_rate(left, right), mapping


def _rate_map(assignments: pd.DataFrame, labels: pd.DataFrame) -> dict[int, float]:
    joined = labels.merge(assignments[["post_id", "topic"]], on="post_id", how="inner")
    summary = summarize_outcomes_by_topic(joined)
    summary = summary.loc[summary["topic"] != NOISE_TOPIC_ID]
    return {int(row.topic): float(row.keep_rate) for row in summary.itertuples(index=False)}


def _edge_topics(rates: dict[int, float]) -> tuple[list[int], list[int]]:
    ordered = sorted(rates, key=rates.get)
    return ordered[:RANK_EDGE], ordered[-RANK_EDGE:]


def run_a3_minilm(output_dir: Path, production_run: Path) -> dict:
    """Fit MiniLM and compare topic counts and keep-rate ranks with production."""
    corpus = original_corpus()
    embeddings = minilm_matrix(corpus.post_ids)
    model, topics, _after = fit_topics(corpus.docs, embeddings, FIT_SEED, PRODUCTION_MIN_CLUSTER_SIZE)
    n_topics, n_noise, noise_share = topic_counts(topics)
    output_dir.mkdir(parents=True, exist_ok=True)
    assignments = pd.DataFrame({"post_id": corpus.post_ids, "topic": [int(topic) for topic in topics]})
    write_assignments(output_dir / "assignments.parquet", corpus.post_ids, topics)
    model.get_topic_info().to_parquet(output_dir / "topic_info.parquet", index=False)
    model.save(str(output_dir / "model"), serialization="safetensors", save_ctfidf=True, save_embedding_model=False)
    production = pd.read_parquet(production_run / "assignments.parquet")
    production = production.loc[production["text_role"] == "original", ["post_id", "topic"]]
    labels = load_outcome_corpus(data_mod.load_keep_remove_posts(), min_raters=3)
    production_rates = _rate_map(production, labels)
    ablation_rates = _rate_map(assignments, labels)
    cache = paths.embeddings_dir("original")
    titan = np.load(cache / EMBEDDINGS_FILENAME)
    index = pd.read_parquet(cache / INDEX_FILENAME)
    vectors = {str(row.post_id): titan[int(row.row_id)] for row in index.itertuples(index=False)}
    rho, mapping = aligned_spearman(production, assignments, vectors, production_rates, ablation_rates)
    production_low, production_high = _edge_topics(production_rates)
    ablation_low, ablation_high = _edge_topics(ablation_rates)
    matched_low = {mapping[topic] for topic in production_low if topic in mapping}
    matched_high = {mapping[topic] for topic in production_high if topic in mapping}
    payload = {
        "n_topics": n_topics,
        "n_noise": n_noise,
        "noise_share": noise_share,
        "spearman_q5_keep_rate": rho,
        "q5_rank_shift": {
            "entered_lowest_5": sorted(set(ablation_low) - matched_low),
            "left_lowest_5": sorted(set(production_low) - set(mapping)),
            "entered_highest_5": sorted(set(ablation_high) - matched_high),
            "left_highest_5": sorted(set(production_high) - set(mapping)),
        },
    }
    (output_dir / "metrics.json").write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    (output_dir / "q5_rank_shift.json").write_text(
        json.dumps(payload["q5_rank_shift"], indent=2) + "\n",
        encoding="utf-8",
    )
    return payload
