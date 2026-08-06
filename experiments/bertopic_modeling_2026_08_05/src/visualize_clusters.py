"""Stage 4: three cluster-map overlays from a shared 2-D UMAP projection.

Recolors one ``umap_2d.npy`` for topic / keep-remove / unanimous overlays.
Topic colors use LLM labels from Stage 3. Emits Plotly HTML and PNG for each.

Run from repo root::

    PYTHONPATH=. uv run --extra bertopic python \\
      experiments/bertopic_modeling_2026_08_05/src/visualize_clusters.py \\
      --topics-run-dir experiments/bertopic_modeling_2026_08_05/outputs/topics/original/<UTC_TS> \\
      --labels-run-dir experiments/bertopic_modeling_2026_08_05/outputs/labels/original/<UTC_TS>
"""

from __future__ import annotations

import argparse
import json
import math
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
NOISE_TOPIC_ID = -1
NOISE_TOPIC_LABEL = "Outliers / noise"
MARKER_OPACITY = 0.2
AXIS_LABEL_X = "Dimension 1"
AXIS_LABEL_Y = "Dimension 2"
LEGEND_TITLE_TOPIC = "Topic Label"
LEGEND_TITLE_DECISION = (
    "Did human annotators choose to keep or remove this post?"
)
LEGEND_TITLE_UNANIMOUS = "Were human annotators unanimous?"
TOP_N_TOPICS = 10
TOPIC_LEGEND_MAX_PER_COLUMN = 3
TOPIC_LEGEND_LABEL_MAX_CHARS = 42
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


def _latest_labels_run() -> Path:
    root = paths.labels_dir(TEXT_ROLE)
    runs = sorted([p for p in root.iterdir() if p.is_dir() and (p / "metadata.json").is_file()])
    if not runs:
        raise FileNotFoundError(f"No labels runs under {root}")
    return runs[-1]


def _topic_display_label(topic_id: int, llm_label: object, ctfidf_name: object) -> str:
    """Map a topic id to a human-readable legend/hover label."""
    if int(topic_id) == NOISE_TOPIC_ID:
        return NOISE_TOPIC_LABEL
    if isinstance(llm_label, str) and llm_label.strip():
        return llm_label.strip()
    if isinstance(ctfidf_name, str) and ctfidf_name.strip():
        return ctfidf_name.strip()
    return str(topic_id)


def _build_plot_frame(topics_run: Path, labels_run: Path) -> pd.DataFrame:
    """Join umap_2d, assignments, LLM labels, and overlay columns on message_id order."""
    umap_path = topics_run / "umap_2d.npy"
    assignments_path = topics_run / "assignments.parquet"
    labels_path = labels_run / "topic_labels.parquet"
    if not umap_path.is_file() or not assignments_path.is_file():
        raise FileNotFoundError(f"Missing umap_2d/assignments under {topics_run}")
    if not labels_path.is_file():
        raise FileNotFoundError(f"Missing topic_labels.parquet under {labels_run}")

    umap_2d = np.load(umap_path)
    assignments = pd.read_parquet(assignments_path)
    if umap_2d.shape != (len(assignments), 2):
        raise ValueError(
            f"umap_2d shape {umap_2d.shape} != assignments rows {len(assignments)}"
        )

    labels = pd.read_parquet(labels_path)
    label_map = {
        int(row.topic_id): _topic_display_label(row.topic_id, row.llm_label, row.ctfidf_name)
        for row in labels.itertuples(index=False)
    }

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
    missing_topics = sorted(set(int(t) for t in merged["topic"]) - set(label_map))
    if missing_topics:
        raise ValueError(f"Labels missing topic_ids: {missing_topics[:10]}")
    merged["topic_label"] = merged["topic"].map(lambda t: label_map[int(t)])
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


def _top_topic_ids(frame: pd.DataFrame, n: int = TOP_N_TOPICS) -> list[int]:
    """Return the ``n`` most common non-noise topic ids (descending count)."""
    counts = (
        frame.loc[frame["topic"] != NOISE_TOPIC_ID, "topic"]
        .value_counts()
        .sort_values(ascending=False)
    )
    return [int(topic_id) for topic_id in counts.head(n).index.tolist()]


def _shorten_legend_label(label: str, max_chars: int = TOPIC_LEGEND_LABEL_MAX_CHARS) -> str:
    """Truncate long LLM labels so multi-column bottom legends stay readable."""
    text = label.strip()
    if len(text) <= max_chars:
        return text
    return text[: max_chars - 1].rstrip() + "…"


def _bottom_legend(*, font_size: int | None = None) -> dict:
    """Native Plotly legend anchored under the x-axis (for 2-item overlays)."""
    legend: dict = {
        "orientation": "h",
        "yanchor": "top",
        "y": -0.14,
        "xanchor": "center",
        "x": 0.5,
        "title": {"side": "top"},
        "itemsizing": "constant",
    }
    if font_size is not None:
        legend["font"] = {"size": font_size}
    return legend


def _trace_color(trace) -> str:
    """Extract a single marker color from a Plotly scatter trace."""
    color = trace.marker.color if trace.marker is not None else None
    if isinstance(color, (list, tuple)) and color:
        color = color[0]
    if color is None:
        return "#636EFA"
    return str(color)


def _apply_topic_multicolumn_legend(
    fig,
    *,
    labels: list[str],
    legend_title: str,
    max_per_column: int = TOPIC_LEGEND_MAX_PER_COLUMN,
) -> None:
    """Replace the native legend with a bottom grid (≤ ``max_per_column`` per column)."""
    color_by_name = {trace.name: _trace_color(trace) for trace in fig.data}
    n_items = len(labels)
    n_cols = max(1, math.ceil(n_items / max_per_column))
    x0, x1 = 0.0, 1.0
    col_w = (x1 - x0) / n_cols
    y_title = -0.12
    y_top = -0.18
    row_h = 0.055

    annotations: list[dict] = [
        {
            "text": f"<b>{legend_title}</b>",
            "xref": "paper",
            "yref": "paper",
            "x": 0.5,
            "y": y_title,
            "showarrow": False,
            "xanchor": "center",
            "font": {"size": 12},
        }
    ]
    for i, label in enumerate(labels):
        col = i // max_per_column
        row = i % max_per_column
        x = x0 + col * col_w + 0.01
        y = y_top - row * row_h
        color = color_by_name.get(label, "#636EFA")
        annotations.append(
            {
                "text": (
                    f'<span style="color:{color}; font-size:14px">●</span> '
                    f'<span style="font-size:10px">{label}</span>'
                ),
                "xref": "paper",
                "yref": "paper",
                "x": x,
                "y": y,
                "showarrow": False,
                "xanchor": "left",
                "align": "left",
            }
        )
    fig.update_layout(showlegend=False, annotations=annotations)


def _write_scatter(
    frame: pd.DataFrame,
    color_col: str,
    legend_title: str,
    title: str,
    out_html: Path,
    out_png: Path,
    color_discrete_map: dict[str, str] | None,
    category_orders: dict[str, list[str]] | None = None,
    legend: dict | None = None,
    width: int | None = None,
    height: int | None = None,
    bottom_margin: int = 120,
    hover_data: list[str] | None = None,
    topic_legend_labels: list[str] | None = None,
) -> None:
    """Write one Plotly HTML + PNG scatter."""
    fig = px.scatter(
        frame,
        x="umap_x",
        y="umap_y",
        color=color_col,
        hover_data=hover_data
        if hover_data is not None
        else ["message_id", "topic", "topic_label", "decision", "is_unanimous"],
        title=title,
        labels={
            "umap_x": AXIS_LABEL_X,
            "umap_y": AXIS_LABEL_Y,
            color_col: legend_title,
        },
        color_discrete_map=color_discrete_map,
        category_orders=category_orders,
        opacity=MARKER_OPACITY,
    )
    layout_kwargs: dict = {
        "template": "plotly_white",
        "legend_title_text": legend_title,
        "xaxis_title": AXIS_LABEL_X,
        "yaxis_title": AXIS_LABEL_Y,
        "margin": {"b": bottom_margin, "t": 60, "l": 60, "r": 40},
        "legend": legend if legend is not None else _bottom_legend(),
    }
    if width is not None:
        layout_kwargs["width"] = width
    if height is not None:
        layout_kwargs["height"] = height
    fig.update_layout(**layout_kwargs)
    fig.update_traces(marker={"opacity": MARKER_OPACITY})
    if topic_legend_labels is not None:
        _apply_topic_multicolumn_legend(
            fig,
            labels=topic_legend_labels,
            legend_title=legend_title,
            max_per_column=TOPIC_LEGEND_MAX_PER_COLUMN,
        )
    fig.write_html(str(out_html))
    fig.write_image(str(out_png))


def run_visualize_clusters(
    topics_run_dir: Path | None,
    labels_run_dir: Path | None,
    figures_run_dir: Path | None = None,
) -> VizResult:
    """Emit six figure files from one shared UMAP-2D projection.

    Parameters
    ----------
    topics_run_dir
        Stage-2 run containing ``umap_2d.npy`` and assignments.
    labels_run_dir
        Stage-3 labels run with ``topic_labels.parquet`` (LLM display names).
    figures_run_dir
        Optional existing figures run directory to overwrite; default is a new stamp.

    Returns
    -------
    VizResult
        Figures run directory and point count.
    """
    topics_run = topics_run_dir if topics_run_dir is not None else _latest_topics_run()
    labels_run = labels_run_dir if labels_run_dir is not None else _latest_labels_run()
    frame = _build_plot_frame(topics_run, labels_run)

    run_dir = (
        figures_run_dir
        if figures_run_dir is not None
        else paths.figures_dir(TEXT_ROLE) / paths.new_run_timestamp()
    )
    run_dir.mkdir(parents=True, exist_ok=True)

    top_topic_ids = _top_topic_ids(frame, TOP_N_TOPICS)
    topic_frame = frame.loc[frame["topic"].isin(top_topic_ids)].copy()
    topic_id_to_label = (
        topic_frame.drop_duplicates("topic").set_index("topic")["topic_label"].to_dict()
    )
    topic_order_full = [topic_id_to_label[topic_id] for topic_id in top_topic_ids]
    topic_order_short = [_shorten_legend_label(label) for label in topic_order_full]
    short_by_full = dict(zip(topic_order_full, topic_order_short, strict=True))
    topic_frame["topic_legend"] = topic_frame["topic_label"].map(short_by_full)

    _write_scatter(
        frame=topic_frame,
        color_col="topic_legend",
        legend_title=LEGEND_TITLE_TOPIC,
        title=f"Clusters by topic (top {TOP_N_TOPICS})",
        out_html=run_dir / "clusters_by_topic.html",
        out_png=run_dir / "clusters_by_topic.png",
        color_discrete_map=None,
        category_orders={"topic_legend": topic_order_short},
        width=1400,
        height=900,
        bottom_margin=280,
        hover_data=["message_id", "topic", "topic_label", "decision", "is_unanimous"],
        topic_legend_labels=topic_order_short,
    )
    _write_scatter(
        frame=frame,
        color_col="decision",
        legend_title=LEGEND_TITLE_DECISION,
        title="Clusters by keep/remove",
        out_html=run_dir / "clusters_by_keep_remove.html",
        out_png=run_dir / "clusters_by_keep_remove.png",
        color_discrete_map={"keep": COLOR_KEEP, "remove": COLOR_REMOVE},
        legend=_bottom_legend(),
        width=900,
        height=700,
        bottom_margin=140,
    )
    _write_scatter(
        frame=frame,
        color_col="unanimous_label",
        legend_title=LEGEND_TITLE_UNANIMOUS,
        title="Clusters by unanimous vs not",
        out_html=run_dir / "clusters_by_unanimous.html",
        out_png=run_dir / "clusters_by_unanimous.png",
        color_discrete_map={
            "unanimous": COLOR_UNANIMOUS,
            "not_unanimous": COLOR_NOT_UNANIMOUS,
        },
        legend=_bottom_legend(),
        width=900,
        height=700,
        bottom_margin=140,
    )

    metadata = {
        "source_topics_run": str(topics_run),
        "source_labels_run": str(labels_run),
        "unanimous_rule_id": data_mod.UNANIMOUS_RULE_ID,
        "n_points": len(frame),
        "n_points_topic_plot": len(topic_frame),
        "topic_plot_top_n": TOP_N_TOPICS,
        "topic_plot_topic_ids": top_topic_ids,
        "topic_plot_labels": topic_order_full,
        "topic_legend_max_per_column": TOPIC_LEGEND_MAX_PER_COLUMN,
        "figures": [f"{stem}.{ext}" for stem in FIGURE_STEMS for ext in ("html", "png")],
        "color_legend": {
            "keep_remove": {"keep": COLOR_KEEP, "remove": COLOR_REMOVE},
            "unanimous": {
                "unanimous": COLOR_UNANIMOUS,
                "not_unanimous": COLOR_NOT_UNANIMOUS,
            },
            "titles": {
                "topic_label": LEGEND_TITLE_TOPIC,
                "decision": LEGEND_TITLE_DECISION,
                "unanimous_label": LEGEND_TITLE_UNANIMOUS,
            },
        },
        "marker_opacity": MARKER_OPACITY,
        "axis_labels": {"umap_x": AXIS_LABEL_X, "umap_y": AXIS_LABEL_Y},
        "legend_position": "bottom",
    }
    (run_dir / "metadata.json").write_text(
        json.dumps(metadata, indent=2) + "\n",
        encoding="utf-8",
    )

    print(f"figures_run_dir={run_dir}")
    print(f"n_points={len(frame)} source_topics_run={topics_run}")
    print(f"source_labels_run={labels_run}")
    print(f"topic_plot_top_n={TOP_N_TOPICS} topic_ids={top_topic_ids}")
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
        help="Stage-3 labels run with topic_labels.parquet (default: latest).",
    )
    parser.add_argument(
        "--figures-run-dir",
        type=Path,
        default=None,
        help="Optional figures run directory to overwrite (default: new timestamp).",
    )
    args = parser.parse_args()
    run_visualize_clusters(
        topics_run_dir=args.topics_run_dir,
        labels_run_dir=args.labels_run_dir,
        figures_run_dir=args.figures_run_dir,
    )


if __name__ == "__main__":
    main()
