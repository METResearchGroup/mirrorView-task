"""Naive term groups and a K-Means sweep on Titan embeddings."""

from __future__ import annotations

from pathlib import Path

import json

import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.metrics import silhouette_score

SILHOUETTE_SAMPLE_SIZE = 2000
INSPECTED_K = (5, 10, 15, 20, 25, 30)
TOP_TERMS = 50
DOCS_PER_CLUSTER = 20


def run_kmeans_sweep(
    embeddings: np.ndarray,
    doc_ids: list[str],
    k_min: int,
    k_max: int,
    seed: int,
) -> pd.DataFrame:
    """Silhouette for every k from ``k_min`` through ``k_max``.

    Silhouette uses a fixed sample of rows so the sweep stays reproducible
    on the full corpus. ``doc_ids`` is accepted so callers keep row identity
    beside the embedding matrix.
    """
    if len(doc_ids) != len(embeddings):
        raise ValueError("doc_ids and embeddings must have the same length")
    sample_size = min(SILHOUETTE_SAMPLE_SIZE, len(embeddings))
    rows = []
    for k in range(k_min, k_max + 1):
        model = KMeans(n_clusters=k, random_state=seed, n_init=10)
        labels = model.fit_predict(embeddings)
        score = silhouette_score(embeddings, labels, sample_size=sample_size, random_state=seed)
        rows.append({"k": k, "silhouette_score": float(score)})
    return pd.DataFrame(rows)


def top_term_groups(docs: list[str], doc_ids: list[str], n_terms: int = TOP_TERMS) -> pd.DataFrame:
    """Document-frequency groups for the most common non-stopword terms."""
    vectorizer = CountVectorizer(stop_words="english")
    matrix = vectorizer.fit_transform(docs)
    document_frequency = np.asarray((matrix > 0).sum(axis=0)).ravel()
    order = np.argsort(-document_frequency)[:n_terms]
    terms = vectorizer.get_feature_names_out()
    rows = []
    for rank, column in enumerate(order, start=1):
        member_rows = matrix[:, int(column)].nonzero()[0]
        sample_ids = [doc_ids[int(row)] for row in member_rows[:5]]
        rows.append(
            {
                "rank": rank,
                "term": terms[int(column)],
                "n_docs": int(document_frequency[int(column)]),
                "sample_post_ids": ",".join(sample_ids),
            }
        )
    return pd.DataFrame(rows)


def write_cluster_samples(
    path: Path,
    doc_ids: list[str],
    docs: list[str],
    labels: np.ndarray,
    n_docs: int,
    seed: int,
) -> None:
    """Write a markdown sample of documents from each K-Means cluster."""
    rng = np.random.default_rng(seed)
    lines = ["# K-Means samples", ""]
    for cluster in sorted(set(int(label) for label in labels)):
        members = [index for index, label in enumerate(labels) if int(label) == cluster]
        chosen = rng.choice(members, size=min(n_docs, len(members)), replace=False)
        lines.append(f"## Cluster {cluster}")
        lines.append("")
        for index in chosen:
            excerpt = docs[int(index)].replace("\n", " ")[:200]
            lines.append(f"- `{doc_ids[int(index)]}` {excerpt}")
        lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def run_a0_naive(output_dir: Path, seed: int, k_chosen: int | None = None) -> dict:
    """Write the term groups, the k sweep, and samples for the inspected k grid."""
    from experiments.bertopic_original_mirror_part3_2026_09_24.src.ablations.fitting import original_corpus

    corpus = original_corpus()
    output_dir.mkdir(parents=True, exist_ok=True)
    groups = top_term_groups(corpus.docs, corpus.post_ids)
    groups.to_csv(output_dir / "doc_freq_groups.csv", index=False)
    sweep = run_kmeans_sweep(corpus.embeddings, corpus.post_ids, k_min=2, k_max=30, seed=seed)
    sweep.to_csv(output_dir / "kmeans_sweep.csv", index=False)
    inspected = sweep.loc[sweep["k"].isin(INSPECTED_K)]
    if k_chosen is None:
        k_chosen = int(inspected.sort_values("silhouette_score", ascending=False).iloc[0]["k"])
    chosen_labels = None
    for k in INSPECTED_K:
        model = KMeans(n_clusters=k, random_state=seed, n_init=10)
        labels = model.fit_predict(corpus.embeddings)
        write_cluster_samples(
            output_dir / f"samples_k{k}.md",
            corpus.post_ids,
            corpus.docs,
            labels,
            DOCS_PER_CLUSTER,
            seed,
        )
        if k == k_chosen:
            chosen_labels = labels
    if chosen_labels is not None:
        frame = pd.DataFrame({"post_id": corpus.post_ids, "cluster": chosen_labels.astype(int)})
        frame.to_parquet(output_dir / f"kmeans_assignments_k{k_chosen}.parquet", index=False)
    metadata = {
        "k_chosen": k_chosen,
        "k_chosen_justification": (
            "Highest silhouette among k in {5, 10, 15, 20, 25, 30}. "
            "A human can replace k_chosen after reading the sample files."
        ),
        "silhouette_sample_size": SILHOUETTE_SAMPLE_SIZE,
    }
    (output_dir / "metadata.json").write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    return metadata
