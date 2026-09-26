"""Refit the original model across UMAP seeds."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from experiments.bertopic_original_mirror_part3_2026_09_24.src.ablations.fitting import (
    fit_topics,
    original_corpus,
    topic_counts,
    write_assignments,
)
from experiments.bertopic_original_mirror_part3_2026_09_24.src.ablations.summary import pairwise_ari_hungarian

UMAP_SEEDS = (42, 43, 44, 45, 46)
PRODUCTION_MIN_CLUSTER_SIZE = 15


def run_a1_umap_seeds(output_dir: Path, production_topics: list[int] | None = None) -> dict:
    """Fit seeds 42 through 46 and record pairwise adjusted Rand scores."""
    corpus = original_corpus()
    output_dir.mkdir(parents=True, exist_ok=True)
    stored: dict[int, list[int]] = {}
    seed_rows = []
    for seed in UMAP_SEEDS:
        _model, topics, _after = fit_topics(
            corpus.docs,
            corpus.embeddings,
            seed,
            PRODUCTION_MIN_CLUSTER_SIZE,
        )
        n_topics, n_noise, noise_share = topic_counts(topics)
        seed_dir = output_dir / f"seed_{seed}"
        write_assignments(seed_dir / "assignments.parquet", corpus.post_ids, topics)
        _model.get_topic_info().to_parquet(seed_dir / "topic_info.parquet", index=False)
        _model.save(str(seed_dir / "model"), serialization="safetensors", save_ctfidf=True, save_embedding_model=False)
        stored[seed] = [int(topic) for topic in topics]
        seed_rows.append(
            {"seed": seed, "n_topics": n_topics, "n_noise": n_noise, "noise_share": noise_share}
        )
    pairs = []
    for left in UMAP_SEEDS:
        for right in UMAP_SEEDS:
            if right <= left:
                continue
            pairs.append(
                {
                    "seed_a": left,
                    "seed_b": right,
                    "ari": pairwise_ari_hungarian(stored[left], stored[right]),
                }
            )
    pd.DataFrame(seed_rows).to_csv(output_dir / "seed_summary.csv", index=False)
    pairwise = pd.DataFrame(pairs)
    pairwise.to_csv(output_dir / "pairwise_ari.csv", index=False)
    production_ari = None
    if production_topics is not None:
        production_ari = pairwise_ari_hungarian(production_topics, stored[42])
    payload = {
        "pairwise_mean_ari": float(pairwise["ari"].mean()) if not pairwise.empty else float("nan"),
        "ari_seed42_vs_production": production_ari,
        "seed_rows": seed_rows,
    }
    (output_dir / "metrics.json").write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return payload
