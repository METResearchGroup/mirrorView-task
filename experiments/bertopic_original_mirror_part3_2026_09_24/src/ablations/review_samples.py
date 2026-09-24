"""Nearest-centroid and random document samples for topic review."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

NOISE_TOPIC_ID = -1
EXCERPT_CHARS = 200
CENTROID_N = 10
RANDOM_N = 10
NOISE_N = 30


def select_centroid_samples(post_ids: list[str], embeddings: np.ndarray, n: int) -> list[str]:
    """Return the ``n`` post ids closest to the mean embedding."""
    centroid = np.mean(embeddings, axis=0)
    norm = float(np.linalg.norm(centroid))
    if norm:
        centroid = centroid / norm
    row_norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
    units = np.divide(embeddings, row_norms, out=np.zeros_like(embeddings), where=row_norms > 0)
    order = np.argsort(-(units @ centroid))
    return [post_ids[int(index)] for index in order[:n]]


def _excerpt(text: str) -> str:
    return text.replace("\n", " ")[:EXCERPT_CHARS]


def build_review_markdown(
    assignments: pd.DataFrame,
    texts: dict[str, str],
    embeddings: dict[str, np.ndarray],
    labels: dict[int, str],
    keywords: dict[int, str],
    centroid_n: int = CENTROID_N,
    random_n: int = RANDOM_N,
    noise_n: int = NOISE_N,
    seed: int = 42,
) -> tuple[str, pd.DataFrame]:
    """Markdown review plus a sample table.

    Noise is its own section. Other topics list centroid neighbors, then a random draw.
    """
    rng = np.random.default_rng(seed)
    lines = ["# Topic review", ""]
    rows: list[dict] = []
    topics = sorted(int(topic) for topic in assignments["topic"].unique() if int(topic) != NOISE_TOPIC_ID)
    for topic in topics:
        members = assignments.loc[assignments["topic"] == topic]
        lines.append(f"## Topic {topic}")
        lines.append("")
        lines.append(f"Label: {labels.get(topic, '')}")
        lines.append("")
        lines.append(f"Keywords: {keywords.get(topic, '')}")
        lines.append("")
        vectors = np.vstack([embeddings[post_id] for post_id in members["post_id"] if post_id in embeddings])
        present = [post_id for post_id in members["post_id"] if post_id in embeddings]
        centroid_ids = select_centroid_samples(present, vectors, min(centroid_n, len(present)))
        lines.append("### Nearest to centroid")
        lines.append("")
        for post_id in centroid_ids:
            lines.append(f"- `{post_id}` {_excerpt(texts.get(post_id, ''))}")
            rows.append(_sample_row(topic, "centroid", post_id, texts))
        lines.append("")
        remaining = [post_id for post_id in members["post_id"].tolist() if post_id not in set(centroid_ids)]
        draw_n = min(random_n, len(remaining))
        random_ids = list(rng.choice(remaining, size=draw_n, replace=False)) if draw_n else []
        lines.append("### Random")
        lines.append("")
        for post_id in random_ids:
            lines.append(f"- `{post_id}` {_excerpt(texts.get(post_id, ''))}")
            rows.append(_sample_row(topic, "random", post_id, texts))
        lines.append("")
    noise = assignments.loc[assignments["topic"] == NOISE_TOPIC_ID, "post_id"].tolist()
    draw_n = min(noise_n, len(noise))
    noise_ids = list(rng.choice(noise, size=draw_n, replace=False)) if draw_n else []
    lines.append("## Topic -1 (noise)")
    lines.append("")
    for post_id in noise_ids:
        lines.append(f"- `{post_id}` {_excerpt(texts.get(post_id, ''))}")
        rows.append(_sample_row(NOISE_TOPIC_ID, "noise", post_id, texts))
    lines.append("")
    return "\n".join(lines), pd.DataFrame(rows)


def _sample_row(topic: int, kind: str, post_id: str, texts: dict[str, str]) -> dict:
    return {
        "topic": topic,
        "sample_kind": kind,
        "post_id": post_id,
        "text_excerpt": _excerpt(texts.get(post_id, "")),
    }


def _vector_lookup(role: str, paths, embeddings_filename: str, index_filename: str) -> dict[str, np.ndarray]:
    """Titan vectors for one role."""
    cache = paths.embeddings_dir(role)
    matrix = np.load(cache / embeddings_filename)
    index = pd.read_parquet(cache / index_filename)
    return {str(row.post_id): matrix[int(row.row_id)] for row in index.itertuples(index=False)}


def _review_inputs(role, assignments, data_mod, paths, embeddings_filename, index_filename):
    """Texts and embeddings keyed the same way as the assignment rows."""
    if role != "joint":
        assignments = assignments.loc[assignments["text_role"] == role].copy()
        corpus = data_mod.load_fit_corpus(role)
        texts = dict(zip(corpus["post_id"].astype(str), corpus["text"].astype(str)))
        embeddings = _vector_lookup(role, paths, embeddings_filename, index_filename)
        return texts, embeddings, assignments
    corpus = data_mod.load_fit_corpus("joint")
    texts = {
        f"{row.post_id}|{row.text_role}": str(row.text)
        for row in corpus.itertuples(index=False)
    }
    by_role = {
        "original": _vector_lookup("original", paths, embeddings_filename, index_filename),
        "mirror": _vector_lookup("mirror", paths, embeddings_filename, index_filename),
    }
    embeddings = {}
    work = assignments.copy()
    work["post_id"] = work["post_id"].astype(str) + "|" + work["text_role"].astype(str)
    for row in assignments.itertuples(index=False):
        key = f"{row.post_id}|{row.text_role}"
        vector = by_role[str(row.text_role)].get(str(row.post_id))
        if vector is not None:
            embeddings[key] = vector
    return texts, embeddings, work


def write_review(
    role: str,
    topics_run: Path,
    labels_run: Path,
    output_dir: Path,
    seed: int = 42,
) -> Path:
    """Write one model's review markdown and append its rows to ``samples.parquet``."""
    from experiments.bertopic_original_mirror_part3_2026_09_24.src import data as data_mod
    from experiments.bertopic_original_mirror_part3_2026_09_24.src.load_embeddings import (
        EMBEDDINGS_FILENAME,
        INDEX_FILENAME,
    )
    from experiments.bertopic_original_mirror_part3_2026_09_24.src import paths

    assignments = pd.read_parquet(topics_run / "assignments.parquet")
    texts, embeddings, assignments = _review_inputs(role, assignments, data_mod, paths, EMBEDDINGS_FILENAME, INDEX_FILENAME)
    label_frame = pd.read_parquet(labels_run / "topic_labels.parquet")
    labels = {
        int(row.topic_id): "" if pd.isna(row.llm_label) else str(row.llm_label)
        for row in label_frame.itertuples(index=False)
    }
    info = pd.read_parquet(topics_run / "topic_info.parquet")
    name_column = "Name" if "Name" in info.columns else "name"
    topic_column = "Topic" if "Topic" in info.columns else "topic"
    keywords = {int(row[topic_column]): str(row[name_column]) for _, row in info.iterrows()}
    markdown, samples = build_review_markdown(assignments, texts, embeddings, labels, keywords, seed=seed)
    if role == "joint":
        samples["post_id"] = samples["post_id"].astype(str).str.split("|").str[0]
    samples.insert(0, "model_role", role)
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / f"review_{role}.md").write_text(markdown, encoding="utf-8")
    sample_path = output_dir / "samples.parquet"
    if sample_path.exists():
        prior = pd.read_parquet(sample_path)
        samples = pd.concat([prior, samples], ignore_index=True)
    samples.to_parquet(sample_path, index=False)
    return output_dir / f"review_{role}.md"
