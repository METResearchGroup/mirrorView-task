"""Generate zero-shot comparison figures for Study 2 writeup."""

from __future__ import annotations

import shutil
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.lines import Line2D
from matplotlib.patches import Patch

REPO_ROOT = Path(__file__).resolve().parents[3]
EXP_STATIC = REPO_ROOT / "experiments/study2_updates_2026_10_05/static/zero_shot"
DOCS_STATIC = REPO_ROOT / "docs/study_updates/static/study_2_writeup/zero_shot"

DPI = 160

MODEL_ORDER = ["Nova", "Qwen", "Jev", "Terra", "Sonnet"]
MODEL_COLORS = {
    "Nova": "#4C78A8",
    "Qwen": "#F58518",
    "Jev": "#54A24B",
    "Terra": "#E45756",
    "Sonnet": "#B279A2",
}

SLICE_ORDER = ["All", "Unanimous", "Split"]
SLICE_TITLES = {
    "All": "All posts",
    "Unanimous": "Unanimous posts",
    "Split": "Split posts",
}
SLICE_MARKERS = {"All": "o", "Unanimous": "s", "Split": "D"}

# (f1, accuracy, recall, precision) per model per slice
METRICS: dict[str, dict[str, tuple[float, float, float, float]]] = {
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

SLICE_META = {
    "All": {"prevalence": 0.212121, "majority_accuracy": 0.787879, "n": 13992},
    "Unanimous": {"prevalence": 0.076031, "majority_accuracy": 0.923969, "n": 4051},
    "Split": {"prevalence": 0.267579, "majority_accuracy": 0.732421, "n": 9941},
}


def _apply_style() -> None:
    plt.rcParams.update(
        {
            "font.size": 11,
            "axes.titlesize": 12,
            "figure.facecolor": "white",
            "axes.facecolor": "white",
        }
    )


def _hide_top_right(ax: plt.Axes) -> None:
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)


def _save_fig(fig: plt.Figure, filename: str) -> None:
    EXP_STATIC.mkdir(parents=True, exist_ok=True)
    DOCS_STATIC.mkdir(parents=True, exist_ok=True)
    exp_path = EXP_STATIC / filename
    fig.savefig(
        exp_path,
        dpi=DPI,
        bbox_inches="tight",
        facecolor="white",
    )
    shutil.copy2(exp_path, DOCS_STATIC / filename)
    plt.close(fig)


def predicted_remove_rate(recall: float, precision: float, prevalence: float) -> float:
    if precision == 0:
        return float("nan")
    return recall * prevalence / precision


def plot_f1_grouped_bars() -> None:
    fig, axes = plt.subplots(1, 3, figsize=(11, 3.6), sharey=True, constrained_layout=True)
    x = np.arange(len(MODEL_ORDER))
    width = 0.65

    for ax, slice_key in zip(axes, SLICE_ORDER, strict=True):
        f1_vals = [METRICS[m][slice_key][0] for m in MODEL_ORDER]
        colors = [MODEL_COLORS[m] for m in MODEL_ORDER]
        bars = ax.bar(x, f1_vals, width=width, color=colors, edgecolor="none")
        ax.set_title(SLICE_TITLES[slice_key])
        ax.set_xticks(x)
        ax.set_xticklabels(MODEL_ORDER, rotation=0)
        ax.set_ylim(0, 1)
        ax.set_xlim(-0.6, len(MODEL_ORDER) - 0.4)
        _hide_top_right(ax)
        for bar, val in zip(bars, f1_vals, strict=True):
            ax.text(
                bar.get_x() + bar.get_width() / 2,
                bar.get_height() + 0.02,
                f"{val:.2f}",
                ha="center",
                va="bottom",
                fontsize=9,
            )

    axes[0].set_ylabel("F1")
    fig.suptitle("Zero-shot F1", fontsize=12, y=1.02)
    legend_handles = [
        Patch(facecolor=MODEL_COLORS[m], edgecolor="none", label=m) for m in MODEL_ORDER
    ]
    fig.legend(
        handles=legend_handles,
        loc="upper center",
        bbox_to_anchor=(0.5, -0.02),
        ncol=5,
        frameon=False,
    )
    _save_fig(fig, "f1_grouped_bars.png")


def _iso_f1_recall(precision: np.ndarray, f1: float) -> np.ndarray:
    denom = 2 * precision - f1
    with np.errstate(divide="ignore", invalid="ignore"):
        recall = f1 * precision / denom
    recall = np.where((precision > f1 / 2) & (denom > 0), recall, np.nan)
    return recall


def plot_precision_recall_scatter() -> None:
    fig, ax = plt.subplots(figsize=(7, 6), constrained_layout=True)
    p_grid = np.linspace(0.501, 0.999, 400)
    for f1_level in (0.2, 0.4, 0.6, 0.8):
        r_curve = _iso_f1_recall(p_grid, f1_level)
        ax.plot(p_grid, r_curve, color="#cccccc", linewidth=0.9, zorder=0)
        p_label = min(0.98, f1_level + 0.02)
        r_label = _iso_f1_recall(np.array([p_label]), f1_level)[0]
        if np.isfinite(r_label):
            ax.text(
                p_label + 0.005,
                r_label,
                f"F1={f1_level:.1f}",
                fontsize=8,
                color="#888888",
                va="center",
            )

    for model in MODEL_ORDER:
        for slice_key in SLICE_ORDER:
            f1, _acc, recall, precision = METRICS[model][slice_key]
            ax.scatter(
                precision,
                recall,
                c=MODEL_COLORS[model],
                marker=SLICE_MARKERS[slice_key],
                s=70,
                edgecolors="white",
                linewidths=0.6,
                zorder=3,
            )

    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.set_xlabel("Precision")
    ax.set_ylabel("Recall")
    ax.set_title("Zero-shot precision and recall")
    ax.grid(True, color="#eeeeee", linewidth=0.8)
    _hide_top_right(ax)

    model_handles = [
        Line2D(
            [0],
            [0],
            marker="o",
            color="w",
            markerfacecolor=MODEL_COLORS[m],
            markersize=8,
            label=m,
        )
        for m in MODEL_ORDER
    ]
    slice_handles = [
        Line2D(
            [0],
            [0],
            marker=SLICE_MARKERS[s],
            color="w",
            markerfacecolor="#666666",
            markeredgecolor="#666666",
            markersize=8,
            label=SLICE_TITLES[s],
        )
        for s in SLICE_ORDER
    ]
    leg1 = ax.legend(handles=model_handles, title="Model", loc="upper left", frameon=False)
    ax.add_artist(leg1)
    ax.legend(handles=slice_handles, title="Slice", loc="lower left", frameon=False)
    _save_fig(fig, "precision_recall_scatter.png")


def plot_predicted_remove_rate() -> None:
    rates_by_slice: dict[str, list[float]] = {}
    for slice_key in SLICE_ORDER:
        prev = SLICE_META[slice_key]["prevalence"]
        rates_by_slice[slice_key] = [
            predicted_remove_rate(METRICS[m][slice_key][2], METRICS[m][slice_key][3], prev)
            for m in MODEL_ORDER
        ]
    ymax = max(max(v) for v in rates_by_slice.values()) * 1.08

    fig, axes = plt.subplots(1, 3, figsize=(11, 3.6), sharey=True, constrained_layout=True)
    x = np.arange(len(MODEL_ORDER))
    width = 0.65

    for ax, slice_key in zip(axes, SLICE_ORDER, strict=True):
        prev = SLICE_META[slice_key]["prevalence"]
        vals = rates_by_slice[slice_key]
        colors = [MODEL_COLORS[m] for m in MODEL_ORDER]
        bars = ax.bar(x, vals, width=width, color=colors, edgecolor="none")
        ax.axhline(prev, color="#333333", linestyle="--", linewidth=1.2, zorder=0)
        ax.set_title(SLICE_TITLES[slice_key])
        ax.set_xticks(x)
        ax.set_xticklabels(MODEL_ORDER)
        ax.set_ylim(0, ymax)
        _hide_top_right(ax)
        for bar, val in zip(bars, vals, strict=True):
            ax.text(
                bar.get_x() + bar.get_width() / 2,
                bar.get_height() + 0.01,
                f"{val:.2f}",
                ha="center",
                va="bottom",
                fontsize=9,
            )

    axes[0].set_ylabel("Share of posts flagged remove")
    fig.suptitle("Zero-shot predicted remove rate", fontsize=12, y=1.02)
    prev_handle = Line2D([0], [0], color="#333333", linestyle="--", label="Actual remove rate")
    model_handles = [
        Patch(facecolor=MODEL_COLORS[m], edgecolor="none", label=m) for m in MODEL_ORDER
    ]
    fig.legend(
        handles=model_handles + [prev_handle],
        loc="upper center",
        bbox_to_anchor=(0.5, -0.02),
        ncol=3,
        frameon=False,
    )
    _save_fig(fig, "predicted_remove_rate.png")


def plot_accuracy_f1_dumbbell() -> None:
    y_positions = np.arange(len(MODEL_ORDER))
    model_labels_top_to_bottom = list(MODEL_ORDER)

    fig, axes = plt.subplots(1, 3, figsize=(11, 4.2), sharex=True, constrained_layout=True)

    for ax, slice_key in zip(axes, SLICE_ORDER, strict=True):
        majority = SLICE_META[slice_key]["majority_accuracy"]
        ax.axvline(
            majority,
            color="#666666",
            linestyle=":",
            linewidth=1.2,
            zorder=0,
        )
        for yi, model in zip(y_positions, model_labels_top_to_bottom, strict=True):
            f1, acc, _, _ = METRICS[model][slice_key]
            color = MODEL_COLORS[model]
            ax.plot([acc, f1], [yi, yi], color="#bbbbbb", linewidth=1.0, zorder=1)
            ax.scatter([acc], [yi], c=color, marker="o", s=55, zorder=2)
            ax.scatter([f1], [yi], c=color, marker="D", s=55, zorder=2)

        ax.set_yticks(y_positions)
        ax.set_yticklabels(model_labels_top_to_bottom)
        ax.invert_yaxis()
        ax.set_xlim(0, 1)
        ax.set_title(SLICE_TITLES[slice_key])
        _hide_top_right(ax)

    axes[0].set_xlabel("Score")
    axes[1].set_xlabel("Score")
    axes[2].set_xlabel("Score")

    fig.suptitle("Zero-shot accuracy and F1", fontsize=12, y=1.02)
    acc_handle = Line2D(
        [0],
        [0],
        marker="o",
        color="w",
        markerfacecolor="#666666",
        markersize=8,
        label="Accuracy",
    )
    f1_handle = Line2D(
        [0],
        [0],
        marker="D",
        color="w",
        markerfacecolor="#666666",
        markersize=8,
        label="F1",
    )
    keep_handle = Line2D([0], [0], color="#666666", linestyle=":", label="Always keep")
    fig.legend(
        handles=[acc_handle, f1_handle, keep_handle],
        loc="upper center",
        bbox_to_anchor=(0.5, -0.02),
        ncol=3,
        frameon=False,
    )
    _save_fig(fig, "accuracy_f1_dumbbell.png")


def main() -> None:
    _apply_style()
    plot_f1_grouped_bars()
    plot_precision_recall_scatter()
    plot_predicted_remove_rate()
    plot_accuracy_f1_dumbbell()
    print(f"Wrote figures to {EXP_STATIC} and {DOCS_STATIC}")


if __name__ == "__main__":
    main()
