"""Compare union-fit original topics with committed June topic assignments.

Run from repo root::

    PYTHONPATH=. uv run --extra bertopic python \\
      experiments/bertopic_original_mirror_study_2_2026_09_24/src/compare_june_run.py \\
      --topics-run-dir <union original topics run>
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.express as px
from sklearn.metrics import adjusted_rand_score, normalized_mutual_info_score

from experiments.bertopic_modeling_2026_08_05.src import paths as june_paths
from experiments.bertopic_original_mirror_study_2_2026_09_24.src import data as data_mod
from experiments.bertopic_original_mirror_study_2_2026_09_24.src import paths
from experiments.bertopic_original_mirror_study_2_2026_09_24.src.load_embeddings import (
    EMBEDDINGS_FILENAME,
    INDEX_FILENAME,
)
from shared.data.dataloader import load_dataset
from shared.data.registry import STUDY_PHASE_2_PART_2_STIMULI

JUNE_RUN_ID = "20260805T135853Z"
JUNE_SOURCE_ASSIGNED = "assigned"
JUNE_SOURCE_CENTROID = "centroid"
NOISE_TOPIC_ID = -1
FACET_MIN_POSTS = 30
SHARE_FACETS = ("sampled_stance", "sample_toxicity_type", "platform")
Q1_FRAMING = "study_2_fit_vs_june_run"


def june_catalog_post_ids(june_stimuli: pd.DataFrame) -> set[str]:
    """All post ids in the June stimulus catalog."""
    return set(june_stimuli["post_primary_key"].astype(str).str.strip())


def catalog_overlap_post_ids(june_stimuli: pd.DataFrame, study_posts: pd.DataFrame) -> set[str]:
    """Posts that appear in both the June catalog and the Study 2 catalog."""
    june_ids = june_catalog_post_ids(june_stimuli)
    study_ids = set(study_posts["post_id"].astype(str).str.strip())
    return june_ids & study_ids


def september_only_post_ids(union_post_ids: set[str], june_catalog_ids: set[str]) -> set[str]:
    """Union-fit posts that are not in the June catalog."""
    return union_post_ids - june_catalog_ids


def june_run_post_ids(june_assignments: pd.DataFrame) -> set[str]:
    """Post ids with a direct topic in the committed June topic run."""
    return set(june_assignments["message_id"].astype(str).str.strip())


def assign_june_topics(post_ids: set[str], june_assignments: pd.DataFrame) -> pd.DataFrame:
    """June topic ids for posts that have a direct assignment row."""
    assignments = june_assignments.copy()
    assignments["post_id"] = assignments["message_id"].astype(str).str.strip()
    matched = assignments.loc[assignments["post_id"].isin(post_ids), ["post_id", "topic"]].copy()
    matched["june_topic"] = matched["topic"].astype(int)
    matched["june_topic_source"] = JUNE_SOURCE_ASSIGNED
    return matched[["post_id", "june_topic", "june_topic_source"]].reset_index(drop=True)


def centroid_assign_june_topic(post_embedding: np.ndarray, centroids: dict[int, np.ndarray]) -> dict:
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
    return {"june_topic": best_topic, "june_topic_source": JUNE_SOURCE_CENTROID, "cosine": best_score}


def compute_topic_agreement(
    paired: pd.DataFrame,
    primary_only: bool,
) -> dict:
    """ARI and NMI between June and union-fit topics.

    Parameters
    ----------
    paired
        Columns ``june_topic``, ``study_topic``, ``june_topic_source``.
    primary_only
        When true, drop centroid-assigned rows.

    Returns
    -------
    dict
        ``ari``, ``nmi``, and ``n_posts``.
    """
    rows = paired
    if primary_only:
        rows = paired.loc[paired["june_topic_source"] == JUNE_SOURCE_ASSIGNED]
    june_labels = rows["june_topic"].astype(int).tolist()
    study_labels = rows["study_topic"].astype(int).tolist()
    if len(june_labels) < 2:
        return {"ari": float("nan"), "nmi": float("nan"), "n_posts": len(june_labels)}
    return {
        "ari": float(adjusted_rand_score(june_labels, study_labels)),
        "nmi": float(normalized_mutual_info_score(june_labels, study_labels)),
        "n_posts": len(june_labels),
    }


def _outlier_rate(topic_ids: pd.Series) -> float:
    """Share of rows assigned to the noise topic."""
    if topic_ids.empty:
        return float("nan")
    return float((topic_ids.astype(int) == NOISE_TOPIC_ID).mean())


def _june_centroids() -> dict[int, np.ndarray]:
    """Mean L2-normalized Titan vector per non-noise June topic."""
    cache = june_paths.embeddings_dir("original")
    embeddings = np.load(cache / EMBEDDINGS_FILENAME)
    index = pd.read_parquet(cache / INDEX_FILENAME)
    run = june_paths.topics_dir("original") / JUNE_RUN_ID
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


def _union_original_vectors() -> dict[str, np.ndarray]:
    """Union-fit original Titan vectors keyed by post id."""
    cache = paths.embeddings_dir("original")
    embeddings = np.load(cache / EMBEDDINGS_FILENAME)
    index = pd.read_parquet(cache / INDEX_FILENAME)
    return {
        str(row.post_id): embeddings[int(row.row_id)]
        for row in index.itertuples(index=False)
    }


def run_compare_june_run(topics_run_dir: Path, output_dir: Path | None = None) -> Path:
    """Write the June versus union-fit topic comparison.

    Returns
    -------
    pathlib.Path
        Comparison run directory.
    """
    june_stimuli = load_dataset(STUDY_PHASE_2_PART_2_STIMULI, low_memory=False)
    study_posts = data_mod.load_stimuli_posts()
    june_catalog = june_catalog_post_ids(june_stimuli)
    catalog_overlap = catalog_overlap_post_ids(june_stimuli, study_posts)
    june_run = june_paths.topics_dir("original") / JUNE_RUN_ID
    june_assignments = pd.read_parquet(june_run / "assignments.parquet")
    june_run_ids = june_run_post_ids(june_assignments)

    union_assignments = pd.read_parquet(topics_run_dir / "assignments.parquet")
    union_assignments = union_assignments.loc[
        union_assignments["text_role"] == "original", ["post_id", "topic"]
    ].rename(columns={"topic": "study_topic"})
    union_assignments["post_id"] = union_assignments["post_id"].astype(str).str.strip()
    union_post_ids = set(union_assignments["post_id"])
    september_only = september_only_post_ids(union_post_ids, june_catalog)
    june_catalog_in_union = union_post_ids & june_catalog

    direct_scope = union_post_ids & june_run_ids
    assigned = assign_june_topics(direct_scope, june_assignments)
    centroid_scope = sorted(june_catalog_in_union - set(assigned["post_id"]))
    centroids = _june_centroids()
    vectors = _union_original_vectors()
    centroid_rows = []
    for post_id in centroid_scope:
        assigned_topic = centroid_assign_june_topic(vectors[post_id], centroids)
        centroid_rows.append(
            {
                "post_id": post_id,
                "june_topic": assigned_topic["june_topic"],
                "june_topic_source": assigned_topic["june_topic_source"],
            }
        )
    june_topics = pd.concat([assigned, pd.DataFrame(centroid_rows)], ignore_index=True)
    paired = june_topics.merge(union_assignments, on="post_id", how="inner")
    primary = compute_topic_agreement(paired, primary_only=True)
    all_rows = compute_topic_agreement(paired, primary_only=False)
    run_dir = output_dir or (paths.analyses_dir() / "june_comparison" / paths.new_run_timestamp())
    run_dir.mkdir(parents=True, exist_ok=True)
    pd.DataFrame({"post_id": sorted(catalog_overlap)}).to_parquet(run_dir / "overlap_post_ids.parquet", index=False)
    pd.DataFrame({"post_id": sorted(september_only)}).to_parquet(run_dir / "september_only_post_ids.parquet", index=False)
    june_topics.to_parquet(run_dir / "june_assignments.parquet", index=False)
    union_assignments.to_parquet(run_dir / "study_assignments.parquet", index=False)
    primary_rows = paired.loc[paired["june_topic_source"] == JUNE_SOURCE_ASSIGNED]
    crosstab = pd.crosstab(primary_rows["june_topic"], primary_rows["study_topic"])
    crosstab.to_csv(run_dir / "crosstab_june_study_topics.csv")
    june_catalog_rows = union_assignments.loc[union_assignments["post_id"].isin(june_catalog_in_union)]
    september_only_rows = union_assignments.loc[union_assignments["post_id"].isin(september_only)]
    metrics = {
        "framing": Q1_FRAMING,
        "ari": primary["ari"],
        "nmi": primary["nmi"],
        "ari_including_centroid": all_rows["ari"],
        "nmi_including_centroid": all_rows["nmi"],
        "n_june_run_assignments": int(len(june_run_ids)),
        "n_union_fit_posts": int(len(union_post_ids)),
        "n_june_catalog_in_union": int(len(june_catalog_in_union)),
        "n_september_only_posts": int(len(september_only)),
        "n_catalog_overlap": int(len(catalog_overlap)),
        "n_june_direct_in_union": int((june_topics.june_topic_source == JUNE_SOURCE_ASSIGNED).sum()),
        "n_june_centroid_in_union": int((june_topics.june_topic_source == JUNE_SOURCE_CENTROID).sum()),
        "n_paired_with_union_fit": int(len(paired)),
        "n_paired_direct_primary": int(len(primary_rows)),
        "outlier_rate_june_catalog_in_union": _outlier_rate(june_catalog_rows["study_topic"]),
        "outlier_rate_september_only": _outlier_rate(september_only_rows["study_topic"]),
    }
    (run_dir / "agreement_metrics.json").write_text(json.dumps(metrics, indent=2) + "\n", encoding="utf-8")
    (run_dir / "metadata.json").write_text(
        json.dumps(
            {
                "source_topics_run": str(topics_run_dir),
                "june_run": str(june_run),
                "june_run_id": JUNE_RUN_ID,
                **metrics,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    _write_share_tables(primary_rows, run_dir)
    _write_subset_share_tables(june_catalog_rows, september_only_rows, run_dir)
    _write_comparison_figures(primary_rows, crosstab, run_dir)
    print(f"june_comparison_run_dir={run_dir}")
    print(json.dumps(metrics))
    return run_dir


def _share_table(topics: pd.Series) -> pd.DataFrame:
    """Document share of each topic id."""
    counts = topics.astype(int).value_counts()
    frame = counts.rename_axis("topic").reset_index(name="n_posts")
    frame["share"] = frame["n_posts"] / frame["n_posts"].sum()
    return frame.sort_values("topic")


def _write_share_tables(primary_rows: pd.DataFrame, run_dir: Path) -> None:
    """Write June shares, union-fit shares, and their difference on shared ids."""
    june_shares = _share_table(primary_rows["june_topic"])
    study_shares = _share_table(primary_rows["study_topic"])
    june_shares.to_csv(run_dir / "topic_shares_june.csv", index=False)
    study_shares.to_csv(run_dir / "topic_shares_study.csv", index=False)
    merged = june_shares.merge(study_shares, on="topic", how="outer", suffixes=("_june", "_study")).fillna(0.0)
    merged["delta"] = merged["share_study"] - merged["share_june"]
    merged.to_csv(run_dir / "topic_share_delta.csv", index=False)


def _write_subset_share_tables(
    june_catalog_rows: pd.DataFrame,
    september_only_rows: pd.DataFrame,
    run_dir: Path,
) -> None:
    """Topic shares within June catalog vs September only union subsets."""
    if not june_catalog_rows.empty:
        _share_table(june_catalog_rows["study_topic"]).to_csv(
            run_dir / "topic_shares_june_catalog_in_union.csv",
            index=False,
        )
    if not september_only_rows.empty:
        _share_table(september_only_rows["study_topic"]).to_csv(
            run_dir / "topic_shares_september_only.csv",
            index=False,
        )


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
        for model, column in (("june", "june_topic"), ("study", "study_topic")):
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
        labels={"x": "study_topic", "y": "june_topic", "color": "n_posts"},
    )
    heatmap.write_html(figures / "crosstab_heatmap.html")
    heatmap.write_image(figures / "crosstab_heatmap.png")
    june_shares = _share_table(primary_rows["june_topic"]).assign(model="june")
    study_shares = _share_table(primary_rows["study_topic"]).assign(model="study")
    _write_bar(pd.concat([june_shares, study_shares], ignore_index=True), figures / "topic_share_comparison", color="model")
    for facet in SHARE_FACETS:
        facet_frame = _facet_share_frame(primary_rows, facet)
        if facet_frame.empty:
            continue
        figure = px.bar(facet_frame, x="topic", y="share", color="model", facet_col="facet_value")
        stem = figures / f"topic_share_facet_{facet}"
        figure.write_html(stem.with_suffix(".html"))
        figure.write_image(stem.with_suffix(".png"))


def main() -> None:
    """CLI entry for the June topic run comparison."""
    parser = argparse.ArgumentParser(
        description="Compare union-fit original topics with June topic assignments.",
    )
    parser.add_argument("--topics-run-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, default=None)
    args = parser.parse_args()
    run_compare_june_run(args.topics_run_dir, args.output_dir)


if __name__ == "__main__":
    main()
