"""Stage 4: three cluster-map overlays from a shared 2-D UMAP projection.

Recolors one ``umap_2d.npy`` for topic / keep-remove / unanimous overlays.
Emits Plotly HTML and PNG for each.

Run from repo root::

    PYTHONPATH=. uv run --extra bertopic python \\
      experiments/bertopic_modeling_2026_08_05/src/visualize_clusters.py \\
      --topics-run-dir experiments/bertopic_modeling_2026_08_05/outputs/topics/original/<UTC_TS>
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.express as px

from experiments.bertopic_modeling_2026_08_05.src import data as data_mod
from experiments.bertopic_modeling_2026_08_05.src import paths

TEXT_ROLE = paths.TEXT_ROLE_V1
COLOR_KEEP = "green"
COLOR_REMOVE = "red"
COLOR_UNANIMOUS = "green"
COLOR_NOT_UNANIMOUS = "red"
FIGURE_STEMS = (
    "clusters_by_topic",
    "clusters_by_keep_remove",
    "clusters_by_unanimous",
)


@dataclass(frozen=True)
class VizResult:
    """Paths from a Stage-4 visualization run."""

    run_dir: Path
    source_topics_run: Path
    n_points: int


def _latest_topics_run() -> Path:
    root = paths.topics_dir(TEXT_ROLE)
    runs = sorted([p for p in root.iterdir() if p.is_dir() and (p / "metadata.json").is_file()])
    if not runs:
        raise FileNotFoundError(f"No topics runs under {root}")
    return runs[-1]


def _build_plot_frame(topics_run: Path) -> pd.DataFrame:
    """Join umap_2d, assignments, and overlay columns on message_id order."""
    umap_path = topics_run / "umap_2d.npy"
    assignments_path = topics_run / "assignments.parquet"
    if not umap_path.is_file() or not assignments_path.is_file():
        raise FileNotFoundError(f"Missing umap_2d/assignments under {topics_run}")

    umap_2d = np.load(umap_path)
    assignments = pd.read_parquet(assignments_path)
    if umap_2d.shape != (len(assignments), 2):
        raise ValueError(
            f"umap_2d shape {umap_2d.shape} != assignments rows {len(assignments)}"
        )

    posts = data_mod.load_posts_with_unanimous()
    overlay = posts[["message_id", "decision", "is_unanimous"]].copy()
    overlay["message_id"] = overlay["message_id"].astype(str)

    frame = assignments.copy()
    frame["message_id"] = frame["message_id"].astype(str)
    frame["umap_x"] = umap_2d[:, 0]
    frame["umap_y"] = umap_2d[:, 1]
    merged = frame.merge(overlay, on="message_id", how="left")
    if merged["decision"].isna().any() or merged["is_unanimous"].isna().any():
        missing = int(merged["decision"].isna().sum())
        raise ValueError(f"Overlay join missing rows: n={missing}")
    merged["topic_label"] = merged["topic"].astype(str)
    merged["keep_remove_color"] = merged["decision"].map(
        {"keep": COLOR_KEEP, "remove": COLOR_REMOVE}
    )
    merged["unanimous_color"] = merged["is_unanimous"].map(
        {True: COLOR_UNANIMOUS, False: COLOR_NOT_UNANIMOUS}
    )
    merged["unanimous_label"] = merged["is_unanimous"].map(
        {True: "unanimous", False: "not_unanimous"}
    )
    return merged


def _write_scatter(
    frame: pd.DataFrame,
    color_col: str,
    title: str,
    out_html: Path,
    out_png: Path,
    color_discrete_map: dict[str, str] | None,
) -> None:
    """Write one Plotly HTML + PNG scatter."""
    fig = px.scatter(
        frame,
        x="umap_x",
        y="umap_y",
        color=color_col,
        hover_data=["message_id", "topic", "decision", "is_unanimous"],
        title=title,
        color_discrete_map=color_discrete_map,
    )
    fig.update_layout(template="plotly_white")
    fig.write_html(str(out_html))
    fig.write_image(str(out_png))


def run_visualize_clusters(
    topics_run_dir: Path | None,
    labels_run_dir: Path | None,
) -> VizResult:
    """Emit six figure files from one shared UMAP-2D projection.

    Parameters
    ----------
    topics_run_dir
        Stage-2 run containing ``umap_2d.npy`` and assignments.
    labels_run_dir
        Optional Stage-3 labels run (recorded in metadata only for provenance).

    Returns
    -------
    VizResult
        Figures run directory and point count.
    """
    topics_run = topics_run_dir if topics_run_dir is not None else _latest_topics_run()
    frame = _build_plot_frame(topics_run)

    run_dir = paths.figures_dir(TEXT_ROLE) / paths.new_run_timestamp()
    run_dir.mkdir(parents=True, exist_ok=True)

    _write_scatter(
        frame=frame,
        color_col="topic_label",
        title="Clusters by topic",
        out_html=run_dir / "clusters_by_topic.html",
        out_png=run_dir / "clusters_by_topic.png",
        color_discrete_map=None,
    )
    _write_scatter(
        frame=frame,
        color_col="decision",
        title="Clusters by keep/remove",
        out_html=run_dir / "clusters_by_keep_remove.html",
        out_png=run_dir / "clusters_by_keep_remove.png",
        color_discrete_map={"keep": COLOR_KEEP, "remove": COLOR_REMOVE},
    )
    _write_scatter(
        frame=frame,
        color_col="unanimous_label",
        title="Clusters by unanimous vs not",
        out_html=run_dir / "clusters_by_unanimous.html",
        out_png=run_dir / "clusters_by_unanimous.png",
        color_discrete_map={
            "unanimous": COLOR_UNANIMOUS,
            "not_unanimous": COLOR_NOT_UNANIMOUS,
        },
    )

    metadata = {
        "source_topics_run": str(topics_run),
        "source_labels_run": str(labels_run_dir) if labels_run_dir else None,
        "unanimous_rule_id": data_mod.UNANIMOUS_RULE_ID,
        "n_points": len(frame),
        "figures": [f"{stem}.{ext}" for stem in FIGURE_STEMS for ext in ("html", "png")],
        "color_legend": {
            "keep_remove": {"keep": COLOR_KEEP, "remove": COLOR_REMOVE},
            "unanimous": {
                "unanimous": COLOR_UNANIMOUS,
                "not_unanimous": COLOR_NOT_UNANIMOUS,
            },
        },
    }
    (run_dir / "metadata.json").write_text(
        json.dumps(metadata, indent=2) + "\n",
        encoding="utf-8",
    )

    print(f"figures_run_dir={run_dir}")
    print(f"n_points={len(frame)} source_topics_run={topics_run}")
    return VizResult(
        run_dir=run_dir,
        source_topics_run=topics_run,
        n_points=len(frame),
    )


def main() -> None:
    """CLI entrypoint for Stage 4."""
    parser = argparse.ArgumentParser(
        description="Three UMAP overlays: topic / keep-remove / unanimous (HTML+PNG)."
    )
    parser.add_argument(
        "--topics-run-dir",
        type=Path,
        default=None,
        help="Stage-2 topics run directory (default: latest).",
    )
    parser.add_argument(
        "--labels-run-dir",
        type=Path,
        default=None,
        help="Optional Stage-3 labels run (provenance only).",
    )
    args = parser.parse_args()
    run_visualize_clusters(
        topics_run_dir=args.topics_run_dir,
        labels_run_dir=args.labels_run_dir,
    )


if __name__ == "__main__":
    main()
