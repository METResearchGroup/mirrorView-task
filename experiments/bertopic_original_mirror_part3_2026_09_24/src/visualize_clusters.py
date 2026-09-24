"""Plot 2-D topic maps colored by topic, keep/remove, and unanimous decision.

Run from repo root::

    PYTHONPATH=. uv run --extra bertopic python \\
      experiments/bertopic_original_mirror_part3_2026_09_24/src/visualize_clusters.py \\
      --text-role original --topics-run-dir <topics> --labels-run-dir <labels>
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.express as px

from experiments.bertopic_original_mirror_part3_2026_09_24.src import data as data_mod
from experiments.bertopic_original_mirror_part3_2026_09_24.src import paths

FIGURE_STEMS = ("clusters_by_topic", "clusters_by_keep_remove", "clusters_by_unanimous")
UNRATED = "unrated"
SINGLE_RATER = "single rater"


def unanimous_category(value: object) -> str:
    """Map a nullable unanimous flag to a plot category.

    Parameters
    ----------
    value
        True, False, or null.

    Returns
    -------
    str
        ``unanimous``, ``split``, or ``single rater``.
    """
    if pd.isna(value):
        return SINGLE_RATER
    if bool(value):
        return "unanimous"
    return "split"


def build_plot_frame(topics_run: Path, labels_run: Path) -> pd.DataFrame:
    """Join UMAP coordinates, labels, and keep/remove overlays.

    Posts missing from the label table are marked ``unrated``. Null
    ``is_unanimous`` stays ``single rater`` and is not coerced to false.
    """
    assignments = pd.read_parquet(topics_run / "assignments.parquet")
    umap_2d = np.load(topics_run / "umap_2d.npy")
    if umap_2d.shape != (len(assignments), 2):
        raise ValueError(f"umap_2d shape {umap_2d.shape} != {len(assignments)} assignments")
    labels = pd.read_parquet(labels_run / "topic_labels.parquet")
    label_by_topic = {
        int(row.topic_id): row.llm_label if isinstance(row.llm_label, str) else row.ctfidf_name
        for row in labels.itertuples(index=False)
    }
    overlay = data_mod.load_keep_remove_posts()[["post_id", "decision", "is_unanimous"]]
    frame = assignments.copy()
    frame["umap_x"] = umap_2d[:, 0]
    frame["umap_y"] = umap_2d[:, 1]
    frame["post_id"] = frame["post_id"].astype(str)
    merged = frame.merge(overlay, on="post_id", how="left")
    merged["decision"] = merged["decision"].fillna(UNRATED)
    merged["unanimous_category"] = [
        UNRATED if decision == UNRATED else unanimous_category(flag)
        for decision, flag in zip(merged["decision"], merged["is_unanimous"])
    ]
    merged["topic_label"] = merged["topic"].map(lambda topic: label_by_topic.get(int(topic), str(topic)))
    return merged


def _write_scatter(frame: pd.DataFrame, color: str, html_path: Path, png_path: Path) -> None:
    """Write one HTML scatter and one PNG."""
    figure = px.scatter(frame, x="umap_x", y="umap_y", color=color, hover_data=["post_id", "topic"])
    html_path.parent.mkdir(parents=True, exist_ok=True)
    figure.write_html(html_path)
    figure.write_image(png_path)


def run_visualize_clusters(role: str, topics_run: Path, labels_run: Path) -> Path:
    """Write the six figure files for one role.

    Returns
    -------
    pathlib.Path
        Figure run directory.
    """
    validated = paths.require_text_role(role)
    frame = build_plot_frame(topics_run, labels_run)
    run_dir = paths.figures_dir(validated) / paths.new_run_timestamp()
    columns = {
        "clusters_by_topic": "topic_label",
        "clusters_by_keep_remove": "decision",
        "clusters_by_unanimous": "unanimous_category",
    }
    for stem, column in columns.items():
        _write_scatter(frame, column, run_dir / f"{stem}.html", run_dir / f"{stem}.png")
    metadata = {
        "text_role": validated,
        "source_topics_run": str(topics_run),
        "source_labels_run": str(labels_run),
        "n_docs": int(len(frame)),
        "figure_stems": list(FIGURE_STEMS),
    }
    (run_dir / "metadata.json").write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    print(f"figures_run_dir={run_dir}")
    return run_dir


def main() -> None:
    """CLI entry for cluster plots."""
    parser = argparse.ArgumentParser(description="Plot Part 3 BERTopic overlays.")
    parser.add_argument("--text-role", choices=["original", "mirror", "joint"], required=True)
    parser.add_argument("--topics-run-dir", type=Path, required=True)
    parser.add_argument("--labels-run-dir", type=Path, required=True)
    args = parser.parse_args()
    run_visualize_clusters(args.text_role, args.topics_run_dir, args.labels_run_dir)


if __name__ == "__main__":
    main()
