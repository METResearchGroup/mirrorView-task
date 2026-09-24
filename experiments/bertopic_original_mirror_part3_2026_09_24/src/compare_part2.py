"""Compare Part 3 original topics with committed Part 2 assignments.

Run from repo root::

    PYTHONPATH=. uv run --extra bertopic python \\
      experiments/bertopic_original_mirror_part3_2026_09_24/src/compare_part2.py \\
      --topics-run-dir <part3 original topics run>
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.express as px
from sklearn.metrics import adjusted_rand_score, normalized_mutual_info_score

from experiments.bertopic_modeling_2026_08_05.src import paths as part2_paths
from experiments.bertopic_original_mirror_part3_2026_09_24.src import data as data_mod
from experiments.bertopic_original_mirror_part3_2026_09_24.src import paths
from experiments.bertopic_original_mirror_part3_2026_09_24.src.load_embeddings import (
    EMBEDDINGS_FILENAME,
    INDEX_FILENAME,
)
from shared.data.dataloader import load_dataset
from shared.data.registry import STUDY_PHASE_2_PART_2_STIMULI

PART2_SOURCE_ASSIGNED = "assigned"
PART2_SOURCE_CENTROID = "centroid"
NOISE_TOPIC_ID = -1
FACET_MIN_POSTS = 30
SHARE_FACETS = ("sampled_stance", "sample_toxicity_type", "platform")


def find_carryover_post_ids(part2_stimuli: pd.DataFrame, part3_posts: pd.DataFrame) -> set[str]:
    """Intersect Part 2 stimulus keys with Part 3 post ids."""
    part2_ids = set(part2_stimuli["post_primary_key"].astype(str).str.strip())
    part3_ids = set(part3_posts["post_id"].astype(str).str.strip())
    return part2_ids & part3_ids


def assign_part2_topics(carryover_ids: set[str], part2_assignments: pd.DataFrame) -> pd.DataFrame:
    """Mark carryover posts that already have a Part 2 topic as assigned."""
    assignments = part2_assignments.copy()
    assignments["post_id"] = assignments["message_id"].astype(str).str.strip()
    matched = assignments.loc[assignments["post_id"].isin(carryover_ids), ["post_id", "topic"]].copy()
    matched["part2_topic"] = matched["topic"].astype(int)
    matched["part2_topic_source"] = PART2_SOURCE_ASSIGNED
    return matched[["post_id", "part2_topic", "part2_topic_source"]].reset_index(drop=True)


def centroid_assign_part2_topic(post_embedding: np.ndarray, centroids: dict[int, np.ndarray]) -> dict:
    """Assign the topic whose L2-normalized centroid has the highest cosine."""
    post = np.asarray(post_embedding, dtype=np.float64)
    post = post / np.linalg.norm(post)
    best_topic = None
    best_score = -np.inf
    for topic, centroid in centroids.items():
        unit = np.asarray(centroid, dtype=np.float64)
        unit = unit / np.linalg.norm(unit)
        score = float(np.dot(post, unit))
        if score > best_score:
            best_topic = int(topic)
            best_score = score
    return {"part2_topic": best_topic, "part2_topic_source": PART2_SOURCE_CENTROID, "cosine": best_score}


def compute_topic_agreement(
    paired: pd.DataFrame,
    primary_only: bool,
) -> dict:
    """ARI and NMI between Part 2 and Part 3 topics.

    Parameters
    ----------
    paired
        Columns ``part2_topic``, ``part3_topic``, ``part2_topic_source``.
    primary_only
        When true, drop centroid-assigned rows.

    Returns
    -------
    dict
        ``ari``, ``nmi``, and ``n_posts``.
    """
    rows = paired
    if primary_only:
        rows = paired.loc[paired["part2_topic_source"] == PART2_SOURCE_ASSIGNED]
    part2 = rows["part2_topic"].astype(int).tolist()
    part3 = rows["part3_topic"].astype(int).tolist()
    if len(part2) < 2:
        return {"ari": float("nan"), "nmi": float("nan"), "n_posts": len(part2)}
    return {
        "ari": float(adjusted_rand_score(part2, part3)),
        "nmi": float(normalized_mutual_info_score(part2, part3)),
        "n_posts": len(part2),
    }


def _part2_centroids() -> dict[int, np.ndarray]:
    """Mean L2-normalized Titan vector per non-noise Part 2 topic."""
    cache = part2_paths.embeddings_dir("original")
    embeddings = np.load(cache / EMBEDDINGS_FILENAME)
    index = pd.read_parquet(cache / INDEX_FILENAME)
    run = part2_paths.topics_dir("original") / "20260805T135853Z"
    assignments = pd.read_parquet(run / "assignments.parquet")
    by_id = {
        str(row.message_id): embeddings[int(row.row_id)]
        for row in index.itertuples(index=False)
    }
    grouped: dict[int, list[np.ndarray]] = {}
    for row in assignments.itertuples(index=False):
        topic = int(row.topic)
        if topic == NOISE_TOPIC_ID:
            continue
        vector = by_id.get(str(row.message_id))
        if vector is None:
            continue
        unit = vector / np.linalg.norm(vector)
        grouped.setdefault(topic, []).append(unit)
    return {topic: np.mean(vectors, axis=0) for topic, vectors in grouped.items()}


def _part3_original_vectors() -> dict[str, np.ndarray]:
    """Part 3 original Titan vectors keyed by post id."""
    cache = paths.embeddings_dir("original")
    embeddings = np.load(cache / EMBEDDINGS_FILENAME)
    index = pd.read_parquet(cache / INDEX_FILENAME)
    return {
        str(row.post_id): embeddings[int(row.row_id)]
        for row in index.itertuples(index=False)
    }


def run_compare_part2(topics_run_dir: Path, output_dir: Path | None = None) -> Path:
    """Write the Part 2 versus Part 3 topic comparison.

    Returns
    -------
    pathlib.Path
        Comparison run directory.
    """
    part2_stimuli = load_dataset(STUDY_PHASE_2_PART_2_STIMULI, low_memory=False)
    part3_posts = data_mod.load_stimuli_posts()
    carryover = find_carryover_post_ids(part2_stimuli, part3_posts)
    part2_run = part2_paths.topics_dir("original") / "20260805T135853Z"
    assigned = assign_part2_topics(carryover, pd.read_parquet(part2_run / "assignments.parquet"))
    missing = sorted(carryover - set(assigned["post_id"]))
    centroids = _part2_centroids()
    vectors = _part3_original_vectors()
    centroid_rows = []
    for post_id in missing:
        assigned_topic = centroid_assign_part2_topic(vectors[post_id], centroids)
        centroid_rows.append(
            {
                "post_id": post_id,
                "part2_topic": assigned_topic["part2_topic"],
                "part2_topic_source": assigned_topic["part2_topic_source"],
            }
        )
    part2_topics = pd.concat([assigned, pd.DataFrame(centroid_rows)], ignore_index=True)
    part3_assignments = pd.read_parquet(topics_run_dir / "assignments.parquet")
    part3_assignments = part3_assignments.loc[
        part3_assignments["text_role"] == "original", ["post_id", "topic"]
    ].rename(columns={"topic": "part3_topic"})
    paired = part2_topics.merge(part3_assignments, on="post_id", how="inner")
    primary = compute_topic_agreement(paired, primary_only=True)
    all_rows = compute_topic_agreement(paired, primary_only=False)
    run_dir = output_dir or (paths.analyses_dir() / "part2_comparison" / paths.new_run_timestamp())
    run_dir.mkdir(parents=True, exist_ok=True)
    pd.DataFrame({"post_id": sorted(carryover)}).to_parquet(run_dir / "carryover_post_ids.parquet", index=False)
    part2_topics.to_parquet(run_dir / "part2_assignments.parquet", index=False)
    part3_assignments.to_parquet(run_dir / "part3_assignments.parquet", index=False)
    primary_rows = paired.loc[paired["part2_topic_source"] == PART2_SOURCE_ASSIGNED]
    crosstab = pd.crosstab(primary_rows["part2_topic"], primary_rows["part3_topic"])
    crosstab.to_csv(run_dir / "crosstab_part2_part3_topics.csv")
    metrics = {
        "ari": primary["ari"],
        "nmi": primary["nmi"],
        "ari_including_centroid": all_rows["ari"],
        "nmi_including_centroid": all_rows["nmi"],
        "n_carryover_primary": int((part2_topics.part2_topic_source == PART2_SOURCE_ASSIGNED).sum()),
        "n_carryover_centroid": int((part2_topics.part2_topic_source == PART2_SOURCE_CENTROID).sum()),
        "n_carryover_total": int(len(carryover)),
        "n_paired_with_part3": int(len(paired)),
    }
    (run_dir / "agreement_metrics.json").write_text(json.dumps(metrics, indent=2) + "\n", encoding="utf-8")
    (run_dir / "metadata.json").write_text(
        json.dumps({"source_topics_run": str(topics_run_dir), "part2_run": str(part2_run), **metrics}, indent=2) + "\n",
        encoding="utf-8",
    )
    _write_share_tables(primary_rows, run_dir)
    _write_comparison_figures(primary_rows, crosstab, run_dir)
    print(f"part2_comparison_run_dir={run_dir}")
    print(json.dumps(metrics))
    return run_dir


def _share_table(topics: pd.Series) -> pd.DataFrame:
    """Document share of each topic id."""
    counts = topics.astype(int).value_counts()
    frame = counts.rename_axis("topic").reset_index(name="n_posts")
    frame["share"] = frame["n_posts"] / frame["n_posts"].sum()
    return frame.sort_values("topic")


def _write_share_tables(primary_rows: pd.DataFrame, run_dir: Path) -> None:
    """Write Part 2 shares, Part 3 shares, and their difference on shared ids."""
    part2 = _share_table(primary_rows["part2_topic"])
    part3 = _share_table(primary_rows["part3_topic"])
    part2.to_csv(run_dir / "topic_shares_part2.csv", index=False)
    part3.to_csv(run_dir / "topic_shares_part3.csv", index=False)
    merged = part2.merge(part3, on="topic", how="outer", suffixes=("_part2", "_part3")).fillna(0.0)
    merged["delta"] = merged["share_part3"] - merged["share_part2"]
    merged.to_csv(run_dir / "topic_share_delta.csv", index=False)


def _write_bar(frame: pd.DataFrame, path_stem: Path, color: str | None = None) -> None:
    """Write an HTML and PNG bar chart."""
    figure = px.bar(frame, x="topic", y="share", color=color)
    figure.write_html(path_stem.with_suffix(".html"))
    figure.write_image(path_stem.with_suffix(".png"))


def _facet_share_frame(primary_rows: pd.DataFrame, facet: str) -> pd.DataFrame:
    """Topic shares inside a facet value, dropping cells under 30 posts."""
    meta = data_mod.load_stimuli_posts()[["post_id", facet]]
    joined = primary_rows.merge(meta, on="post_id", how="left")
    rows: list[dict] = []
    for value, subset in joined.groupby(facet, dropna=False):
        for model, column in (("part2", "part2_topic"), ("part3", "part3_topic")):
            counts = subset[column].astype(int).value_counts()
            for topic, n_posts in counts.items():
                if int(n_posts) < FACET_MIN_POSTS:
                    continue
                rows.append(
                    {
                        "facet_value": value,
                        "model": model,
                        "topic": int(topic),
                        "n_posts": int(n_posts),
                        "share": float(n_posts) / float(len(subset)),
                    }
                )
    return pd.DataFrame(rows)


def _write_comparison_figures(primary_rows: pd.DataFrame, crosstab: pd.DataFrame, run_dir: Path) -> None:
    """Heatmap, overall share bars, and facet share bars for the primary subset."""
    figures = run_dir / "figures"
    figures.mkdir(parents=True, exist_ok=True)
    heatmap = px.imshow(
        crosstab.to_numpy(),
        x=[str(column) for column in crosstab.columns],
        y=[str(index) for index in crosstab.index],
        labels={"x": "part3_topic", "y": "part2_topic", "color": "n_posts"},
    )
    heatmap.write_html(figures / "crosstab_heatmap.html")
    heatmap.write_image(figures / "crosstab_heatmap.png")
    part2 = _share_table(primary_rows["part2_topic"]).assign(model="part2")
    part3 = _share_table(primary_rows["part3_topic"]).assign(model="part3")
    _write_bar(pd.concat([part2, part3], ignore_index=True), figures / "topic_share_comparison", color="model")
    for facet in SHARE_FACETS:
        facet_frame = _facet_share_frame(primary_rows, facet)
        if facet_frame.empty:
            continue
        figure = px.bar(facet_frame, x="topic", y="share", color="model", facet_col="facet_value")
        stem = figures / f"topic_share_facet_{facet}"
        figure.write_html(stem.with_suffix(".html"))
        figure.write_image(stem.with_suffix(".png"))


def main() -> None:
    """CLI entry for the Part 2 comparison."""
    parser = argparse.ArgumentParser(description="Compare Part 3 topics with Part 2 assignments.")
    parser.add_argument("--topics-run-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, default=None)
    args = parser.parse_args()
    run_compare_part2(args.topics_run_dir, args.output_dir)


if __name__ == "__main__":
    main()
