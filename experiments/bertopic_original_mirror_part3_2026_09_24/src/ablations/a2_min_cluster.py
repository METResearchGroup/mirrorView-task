"""Refit the original model at three HDBSCAN minimum cluster sizes."""

from __future__ import annotations

import json
from pathlib import Path

from experiments.bertopic_original_mirror_part3_2026_09_24.src.ablations.fitting import (
    fit_topics,
    original_corpus,
    topic_counts,
    write_assignments,
)

MIN_CLUSTER_SIZES = (15, 30, 50)
FIT_SEED = 42


def run_a2_min_cluster(output_dir: Path) -> list[dict]:
    """Fit minimum cluster sizes 15, 30, and 50."""
    corpus = original_corpus()
    output_dir.mkdir(parents=True, exist_ok=True)
    rows = []
    for min_cluster_size in MIN_CLUSTER_SIZES:
        model, topics, _after = fit_topics(corpus.docs, corpus.embeddings, FIT_SEED, min_cluster_size)
        n_topics, n_noise, noise_share = topic_counts(topics)
        run_dir = output_dir / f"mcs_{min_cluster_size}"
        write_assignments(run_dir / "assignments.parquet", corpus.post_ids, topics)
        model.get_topic_info().to_parquet(run_dir / "topic_info.parquet", index=False)
        model.save(str(run_dir / "model"), serialization="safetensors", save_ctfidf=True, save_embedding_model=False)
        row = {
            "min_cluster_size": min_cluster_size,
            "n_topics": n_topics,
            "n_noise": n_noise,
            "noise_share": noise_share,
        }
        (run_dir / "metrics.json").write_text(json.dumps(row, indent=2) + "\n", encoding="utf-8")
        rows.append(row)
    return rows
