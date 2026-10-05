"""Few-shot vs zero-shot Study 2 figures."""

from __future__ import annotations

import shutil
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import FancyArrowPatch

EXPERIMENT_ROOT = Path(__file__).resolve().parents[1]
OUT_DIRS = (
    EXPERIMENT_ROOT / "static" / "few_shot",
    Path(__file__).resolve().parents[3]
    / "docs"
    / "study_updates"
    / "static"
    / "study_2_writeup"
    / "few_shot",
)

MODEL_ORDER = ("Nova", "Qwen", "Jev", "Terra", "Sonnet")
MODEL_LABELS = {
    "Nova": "Nova",
    "Qwen": "Qwen",
    "Jev": "Jev",
    "Terra": "Terra",
    "Sonnet": "Sonnet",
}
MODEL_COLORS = {
    "Nova": "#4C78A8",
    "Qwen": "#F58518",
    "Jev": "#54A24B",
    "Terra": "#E45756",
    "Sonnet": "#B279A2",
}

SLICE_ORDER = ("All", "Unanimous", "Split")
SLICE_TITLES = {
    "All": "All posts",
    "Unanimous": "Unanimous posts",
    "Split": "Split posts",
}
SLICE_MARKERS = {"All": "o", "Unanimous": "s", "Split": "D"}

METRIC_NAMES = ("f1", "accuracy", "recall", "precision")
HEATMAP_METRICS = ("f1", "precision", "recall", "accuracy")
HEATMAP_LABELS = ("F1", "Precision", "Recall", "Accuracy")

# (f1, accuracy, recall, precision)
ZERO_SHOT: dict[str, dict[str, tuple[float, float, float, float]]] = {
    "Nova": {
        "All": (0.426029, 0.550529, 0.786388, 0.292152),
        "Unanimous": (0.256932, 0.603061, 0.902597, 0.149784),
        "Split": (0.467645, 0.529122, 0.772932, 0.335236),
    },
    "Qwen": {
        "All": (0.498773, 0.649800, 0.821429, 0.358108),
        "Unanimous": (0.395946, 0.779314, 0.951299, 0.250000),
        "Split": (0.517117, 0.597022, 0.806391, 0.380589),
    },
    "Terra": {
        "All": (0.316304, 0.800100, 0.217992, 0.576135),
        "Unanimous": (0.478528, 0.937053, 0.379870, 0.646409),
        "Split": (0.294281, 0.744291, 0.199248, 0.562633),
    },
    "Sonnet": {
        "All": (0.223602, 0.803459, 0.133423, 0.689895),
        "Unanimous": (0.382134, 0.938534, 0.250000, 0.810526),
        "Split": (0.203249, 0.748416, 0.119925, 0.665971),
    },
    "Jev": {
        "All": (0.529322, 0.712621, 0.761792, 0.405561),
        "Unanimous": (0.493617, 0.853123, 0.941558, 0.334487),
        "Split": (0.535016, 0.655367, 0.740977, 0.418649),
    },
}

FEW_SHOT: dict[str, dict[str, tuple[float, float, float, float]]] = {
    "Nova": {
        "All": (0.428947, 0.580253, 0.743425, 0.301435),
        "Unanimous": (0.274428, 0.654968, 0.862745, 0.163164),
        "Split": (0.464521, 0.549844, 0.729699, 0.340706),
    },
    "Qwen": {
        "All": (0.463378, 0.566812, 0.881996, 0.314234),
        "Unanimous": (0.305225, 0.668067, 0.964052, 0.181315),
        "Split": (0.496046, 0.525601, 0.872556, 0.346521),
    },
    "Terra": {
        "All": (0.338110, 0.805176, 0.234659, 0.604692),
        "Unanimous": (0.526316, 0.942165, 0.424837, 0.691489),
        "Split": (0.312448, 0.749422, 0.212782, 0.587747),
    },
    "Sonnet": {
        "All": (0.330366, 0.806392, 0.225219, 0.619666),
        "Unanimous": (0.511931, 0.944390, 0.385621, 0.761290),
        "Split": (0.307005, 0.750226, 0.206767, 0.595883),
    },
    "Jev": {
        "All": (0.561910, 0.787517, 0.642616, 0.499214),
        "Unanimous": (0.664251, 0.931290, 0.898693, 0.526820),
        "Split": (0.547683, 0.729001, 0.613158, 0.494842),
    },
}

FIGURE_NAMES = (
    "f1_slope_zero_to_few.png",
    "delta_heatmap.png",
    "precision_recall_arrows.png",
    "f1_grouped_bars.png",
)


def _metric_value(metrics: tuple[float, float, float, float], name: str) -> float:
    return metrics[METRIC_NAMES.index(name)]


def _hide_top_right_spines(ax: plt.Axes) -> None:
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)


def _apply_rc() -> None:
    plt.rcParams.update(
        {
            "font.size": 11,
            "axes.titlesize": 12,
        }
    )


def _save_figure(fig: plt.Figure, filename: str) -> None:
    primary = OUT_DIRS[0]
    primary.mkdir(parents=True, exist_ok=True)
    path = primary / filename
    fig.savefig(path, dpi=160, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    OUT_DIRS[1].mkdir(parents=True, exist_ok=True)
    shutil.copy2(path, OUT_DIRS[1] / filename)


def _format_delta(value: float) -> str:
    if value >= 0:
        return f"+{value:.2f}"
    return f"{value:.2f}"


def plot_f1_slope() -> None:
    fig, axes = plt.subplots(1, 3, figsize=(12, 4), sharey=True)

    for ax, slice_name in zip(axes, SLICE_ORDER, strict=True):
        for model in MODEL_ORDER:
            z = _metric_value(ZERO_SHOT[model][slice_name], "f1")
            f = _metric_value(FEW_SHOT[model][slice_name], "f1")
            color = MODEL_COLORS[model]
            ax.plot([0, 1], [z, f], color=color, linewidth=2, zorder=1)
            ax.scatter([0, 1], [z, f], color=color, s=48, zorder=2)
        ax.set_xlim(-0.05, 1.05)
        ax.set_xticks([0, 1])
        ax.set_xticklabels(["Zero-shot", "Few-shot"])
        ax.set_ylim(0, 1)
        ax.set_yticks([0.0, 0.2, 0.4, 0.6, 0.8, 1.0])
        ax.set_title(SLICE_TITLES[slice_name])
        _hide_top_right_spines(ax)

    axes[0].set_ylabel("F1")

    handles = [
        plt.Line2D([0], [0], color=MODEL_COLORS[m], linewidth=2, marker="o", label=MODEL_LABELS[m])
        for m in MODEL_ORDER
    ]
    fig.legend(handles=handles, loc="upper center", ncol=5, bbox_to_anchor=(0.5, 1.08), frameon=False)
    fig.suptitle("Few-shot change in F1", y=1.14)
    fig.tight_layout()
    _save_figure(fig, "f1_slope_zero_to_few.png")


def plot_delta_heatmap() -> None:
    rows: list[list[float]] = []
    col_labels: list[str] = []
    for slice_name in SLICE_ORDER:
        for metric, label in zip(HEATMAP_METRICS, HEATMAP_LABELS, strict=True):
            col_labels.append(f"{slice_name}\n{label}")

    for model in MODEL_ORDER:
        row: list[float] = []
        for slice_name in SLICE_ORDER:
            for metric in HEATMAP_METRICS:
                z = _metric_value(ZERO_SHOT[model][slice_name], metric)
                f = _metric_value(FEW_SHOT[model][slice_name], metric)
                row.append(f - z)
        rows.append(row)

    data = np.array(rows)
    max_abs = float(np.max(np.abs(data)))
    if max_abs == 0:
        max_abs = 1.0

    fig, ax = plt.subplots(figsize=(14, 4.8))
    im = ax.imshow(data, cmap="RdBu_r", vmin=-max_abs, vmax=max_abs, aspect="auto")

    ax.set_xticks(np.arange(len(col_labels)))
    ax.set_xticklabels(col_labels, rotation=0, ha="center")
    ax.set_yticks(np.arange(len(MODEL_ORDER)))
    ax.set_yticklabels([MODEL_LABELS[m] for m in MODEL_ORDER])

    for i in range(data.shape[0]):
        for j in range(data.shape[1]):
            ax.text(
                j,
                i,
                _format_delta(data[i, j]),
                ha="center",
                va="center",
                fontsize=8,
                color="black",
            )

    ax.set_title("Few-shot minus zero-shot")
    cbar = fig.colorbar(im, ax=ax, fraction=0.02, pad=0.02)
    cbar.set_label("Δ (few − zero)")
    fig.tight_layout()
    _save_figure(fig, "delta_heatmap.png")


def _plot_iso_f1_contours(ax: plt.Axes, levels: tuple[float, ...]) -> None:
    p_grid = np.linspace(0.02, 0.99, 400)
    for f1 in levels:
        denom = 2 * p_grid - f1
        with np.errstate(divide="ignore", invalid="ignore"):
            recall = f1 * p_grid / denom
        valid = (denom > 1e-6) & (recall >= 0) & (recall <= 1)
        if not np.any(valid):
            continue
        ax.plot(p_grid[valid], recall[valid], color="#cccccc", linewidth=0.8, zorder=0)


def plot_precision_recall_arrows() -> None:
    fig, ax = plt.subplots(figsize=(7.5, 7))
    _plot_iso_f1_contours(ax, (0.2, 0.4, 0.6, 0.8))

    for model in MODEL_ORDER:
        color = MODEL_COLORS[model]
        for slice_name in SLICE_ORDER:
            z = ZERO_SHOT[model][slice_name]
            f = FEW_SHOT[model][slice_name]
            z_p, z_r = _metric_value(z, "precision"), _metric_value(z, "recall")
            f_p, f_r = _metric_value(f, "precision"), _metric_value(f, "recall")
            marker = SLICE_MARKERS[slice_name]

            ax.scatter(
                z_p,
                z_r,
                facecolors="white",
                edgecolors=color,
                marker=marker,
                s=40,
                linewidths=1.2,
                zorder=2,
            )
            ax.scatter(f_p, f_r, color=color, marker=marker, s=50, zorder=3)
            arrow = FancyArrowPatch(
                (z_p, z_r),
                (f_p, f_r),
                arrowstyle="-|>",
                mutation_scale=12,
                color=color,
                linewidth=1.4,
                shrinkA=0,
                shrinkB=0,
                clip_on=False,
                zorder=1,
            )
            ax.add_patch(arrow)

    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.set_xlabel("Precision")
    ax.set_ylabel("Recall")
    ax.set_title("Zero-shot to few-shot in precision-recall space")
    _hide_top_right_spines(ax)

    model_handles = [
        plt.Line2D([0], [0], color=MODEL_COLORS[m], linewidth=2, marker="o", label=MODEL_LABELS[m])
        for m in MODEL_ORDER
    ]
    leg1 = ax.legend(handles=model_handles, loc="upper left", bbox_to_anchor=(1.02, 1), frameon=False)
    ax.add_artist(leg1)
    ax.text(
        1.02,
        0.35,
        "Arrow points toward few-shot",
        transform=ax.transAxes,
        fontsize=10,
        va="top",
        ha="left",
    )
    fig.tight_layout()
    _save_figure(fig, "precision_recall_arrows.png")


def plot_f1_grouped_bars() -> None:
    fig, axes = plt.subplots(1, 3, figsize=(11, 4), sharey=True)
    x = np.arange(len(MODEL_ORDER))
    width = 0.65

    for ax, slice_name in zip(axes, SLICE_ORDER, strict=True):
        values = [_metric_value(FEW_SHOT[m][slice_name], "f1") for m in MODEL_ORDER]
        colors = [MODEL_COLORS[m] for m in MODEL_ORDER]
        ax.bar(x, values, width=width, color=colors)
        ax.set_xticks(x)
        ax.set_xticklabels([MODEL_LABELS[m] for m in MODEL_ORDER], rotation=30, ha="right")
        ax.set_ylim(0, 1)
        ax.set_title(SLICE_TITLES[slice_name])
        _hide_top_right_spines(ax)

    axes[0].set_ylabel("F1")
    handles = [
        plt.Rectangle((0, 0), 1, 1, color=MODEL_COLORS[m], label=MODEL_LABELS[m])
        for m in MODEL_ORDER
    ]
    fig.legend(handles=handles, loc="upper center", ncol=5, bbox_to_anchor=(0.5, 1.08), frameon=False)
    fig.suptitle("Few-shot F1", y=1.12)
    fig.tight_layout()
    _save_figure(fig, "f1_grouped_bars.png")


def _verify_outputs() -> None:
    for out_dir in OUT_DIRS:
        for name in FIGURE_NAMES:
            path = out_dir / name
            if not path.is_file():
                raise FileNotFoundError(path)
            size = path.stat().st_size
            if size <= 10_000:
                raise ValueError(f"{path} is only {size} bytes (expected >10KB)")


def main() -> None:
    _apply_rc()
    plot_f1_slope()
    plot_delta_heatmap()
    plot_precision_recall_arrows()
    plot_f1_grouped_bars()
    _verify_outputs()
    print("Wrote few-shot figures to:")
    for out_dir in OUT_DIRS:
        print(f"  {out_dir}")


if __name__ == "__main__":
    main()
