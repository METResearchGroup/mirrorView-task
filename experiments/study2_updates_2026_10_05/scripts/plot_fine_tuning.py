"""Generate fine-tuning classifier figures for Study 2 writeup."""

from __future__ import annotations

import shutil
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Patch

REPO_ROOT = Path(__file__).resolve().parents[3]
EXP_STATIC = REPO_ROOT / "experiments/study2_updates_2026_10_05/static/fine_tuning"
DOCS_STATIC = REPO_ROOT / "docs/study_updates/static/study_2_writeup/fine_tuning"

DPI = 160

ADAPTER_ORDER = ["Unanimous", "Split", "All-label"]
ADAPTER_COLORS = {
    "Unanimous": "#9e9ac8",
    "Split": "#6baed6",
    "All-label": "#2171b5",
}

# Heatmap: columns Unanimous, Split, All
HEATMAP_EVAL_ORDER = ["Unanimous", "Split", "All"]
# Faceted plots: All, Unanimous, Split
SLICE_ORDER = ["All", "Unanimous", "Split"]
SLICE_TITLES = {
    "All": "All posts",
    "Unanimous": "Unanimous posts",
    "Split": "Split posts",
}

PROMPTING_COLOR = "#54A24B"
PRECISION_COLOR = "#4C78A8"
RECALL_COLOR = "#F58518"

# (accuracy, precision, recall, f1) per adapter per eval slice
METRICS: dict[str, dict[str, tuple[float, float, float, float]]] = {
    "Unanimous": {
        "Unanimous": (0.9975, 0.9686, 1.0000, 0.9840),
        "Split": (0.7790, 0.6483, 0.3805, 0.4795),
        "All": (0.8423, 0.7025, 0.4447, 0.5447),
    },
    "Split": {
        "Unanimous": (0.9657, 0.7666, 0.7890, 0.7776),
        "Split": (0.9439, 0.8762, 0.9203, 0.8977),
        "All": (0.9502, 0.8650, 0.9067, 0.8853),
    },
    "All-label": {
        "Unanimous": (0.9938, 0.9521, 0.9675, 0.9597),
        "Split": (0.9506, 0.8880, 0.9331, 0.9100),
        "All": (0.9631, 0.8945, 0.9367, 0.9151),
    },
}

# Jev prompting F1 by eval slice
PROMPTING_F1: dict[str, dict[str, float]] = {
    "Zero-shot": {
        "All": 0.529322,
        "Unanimous": 0.493617,
        "Split": 0.535016,
    },
    "Few-shot": {
        "All": 0.561910,
        "Unanimous": 0.664251,
        "Split": 0.547683,
    },
    "Prompt-tuned": {
        "All": 0.542148,
        "Unanimous": 0.549451,
        "Split": 0.541099,
    },
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


def _metric_matrix(metric_idx: int) -> np.ndarray:
    """Rows = adapters, columns = HEATMAP_EVAL_ORDER."""
    return np.array(
        [
            [METRICS[adapter][eval_key][metric_idx] for eval_key in HEATMAP_EVAL_ORDER]
            for adapter in ADAPTER_ORDER
        ]
    )


def _annotate_heatmap(ax: plt.Axes, data: np.ndarray) -> None:
    for i in range(data.shape[0]):
        for j in range(data.shape[1]):
            val = data[i, j]
            ax.text(j, i, f"{val:.2f}", ha="center", va="center", fontsize=10, color="black")


def plot_train_eval_f1_heatmap() -> None:
    f1 = _metric_matrix(3)
    fig, ax = plt.subplots(figsize=(5.5, 4.2), constrained_layout=True)
    im = ax.imshow(f1, cmap="YlGn", vmin=0, vmax=1, aspect="auto")
    ax.set_xticks(np.arange(len(HEATMAP_EVAL_ORDER)))
    ax.set_yticks(np.arange(len(ADAPTER_ORDER)))
    ax.set_xticklabels(HEATMAP_EVAL_ORDER)
    ax.set_yticklabels(ADAPTER_ORDER)
    ax.set_xlabel("Evaluation set")
    ax.set_ylabel("Training set (adapter)")
    ax.set_title("Fine-tuned F1 by training set and evaluation set")
    _annotate_heatmap(ax, f1)
    fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04, label="F1")
    _save_fig(fig, "train_eval_f1_heatmap.png")


def plot_train_eval_other_metrics() -> None:
    metric_specs = [
        ("Precision", 1),
        ("Recall", 2),
        ("Accuracy", 0),
    ]
    fig, axes = plt.subplots(1, 3, figsize=(12, 4.2), constrained_layout=True)
    for ax, (title, idx) in zip(axes, metric_specs, strict=True):
        data = _metric_matrix(idx)
        im = ax.imshow(data, cmap="YlGn", vmin=0, vmax=1, aspect="auto")
        ax.set_xticks(np.arange(len(HEATMAP_EVAL_ORDER)))
        ax.set_yticks(np.arange(len(ADAPTER_ORDER)))
        ax.set_xticklabels(HEATMAP_EVAL_ORDER)
        ax.set_yticklabels(ADAPTER_ORDER)
        ax.set_xlabel("Evaluation set")
        ax.set_ylabel("Training set (adapter)")
        ax.set_title(title)
        _annotate_heatmap(ax, data)
        fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)

    fig.suptitle("Precision, recall, and accuracy", fontsize=12, y=1.02)
    _save_fig(fig, "train_eval_other_metrics.png")


def plot_ft_vs_prompting_f1() -> None:
    bar_labels = [
        "Zero-shot (Jev)",
        "Few-shot (Jev)",
        "Prompt-tuned (Jev)",
        "Unanimous adapter",
        "Split adapter",
        "All-label adapter",
    ]
    eval_slice = "All"
    bar_values = [
        PROMPTING_F1["Zero-shot"][eval_slice],
        PROMPTING_F1["Few-shot"][eval_slice],
        PROMPTING_F1["Prompt-tuned"][eval_slice],
        METRICS["Unanimous"][eval_slice][3],
        METRICS["Split"][eval_slice][3],
        METRICS["All-label"][eval_slice][3],
    ]
    bar_colors = [
        PROMPTING_COLOR,
        PROMPTING_COLOR,
        PROMPTING_COLOR,
        ADAPTER_COLORS["Unanimous"],
        ADAPTER_COLORS["Split"],
        ADAPTER_COLORS["All-label"],
    ]

    fig, ax = plt.subplots(figsize=(8, 4.5), constrained_layout=True)
    x = np.arange(len(bar_labels))
    width = 0.65
    bars = ax.bar(x, bar_values, width=width, color=bar_colors, edgecolor="none")
    ax.set_xticks(x)
    ax.set_xticklabels(bar_labels, rotation=25, ha="right")
    ax.set_ylim(0, 1)
    ax.set_ylabel("F1")
    ax.set_title("All posts: prompting baselines and fine-tuned adapters")
    _hide_top_right(ax)
    for bar, val in zip(bars, bar_values, strict=True):
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height() + 0.02,
            f"{val:.2f}",
            ha="center",
            va="bottom",
            fontsize=9,
        )

    legend_handles = [
        Patch(facecolor=PROMPTING_COLOR, edgecolor="none", label="Zero-shot (Jev)"),
        Patch(facecolor=PROMPTING_COLOR, edgecolor="none", label="Few-shot (Jev)"),
        Patch(facecolor=PROMPTING_COLOR, edgecolor="none", label="Prompt-tuned (Jev)"),
        Patch(facecolor=ADAPTER_COLORS["Unanimous"], edgecolor="none", label="Unanimous adapter"),
        Patch(facecolor=ADAPTER_COLORS["Split"], edgecolor="none", label="Split adapter"),
        Patch(
            facecolor=ADAPTER_COLORS["All-label"],
            edgecolor="none",
            label="All-label adapter",
        ),
    ]
    ax.legend(handles=legend_handles, loc="upper left", frameon=False, fontsize=9)
    _save_fig(fig, "ft_vs_prompting_f1.png")


def plot_precision_recall_by_adapter() -> None:
    fig, axes = plt.subplots(1, 3, figsize=(11, 4), sharey=True, constrained_layout=True)
    n_adapters = len(ADAPTER_ORDER)
    x = np.arange(n_adapters)
    bar_width = 0.32

    for ax, slice_key in zip(axes, SLICE_ORDER, strict=True):
        prec_vals = [METRICS[a][slice_key][1] for a in ADAPTER_ORDER]
        rec_vals = [METRICS[a][slice_key][2] for a in ADAPTER_ORDER]
        ax.bar(
            x - bar_width / 2,
            prec_vals,
            width=bar_width,
            color=PRECISION_COLOR,
            edgecolor="none",
            label="Precision",
        )
        bars_rec = ax.bar(
            x + bar_width / 2,
            rec_vals,
            width=bar_width,
            color=RECALL_COLOR,
            edgecolor="none",
            label="Recall",
        )
        ax.set_xticks(x)
        ax.set_xticklabels(ADAPTER_ORDER, rotation=0)
        ax.set_ylim(0, 1)
        ax.set_title(SLICE_TITLES[slice_key])
        _hide_top_right(ax)

        for xi, val in enumerate(prec_vals):
            ax.text(
                xi - bar_width / 2,
                val + 0.02,
                f"{val:.2f}",
                ha="center",
                va="bottom",
                fontsize=8,
            )
        for bar, val, adapter in zip(bars_rec, rec_vals, ADAPTER_ORDER, strict=True):
            offset = 0.02
            fontsize = 8
            if slice_key == "Split" and adapter == "Unanimous" and abs(val - 0.3805) < 0.001:
                ax.annotate(
                    f"{val:.2f}",
                    xy=(bar.get_x() + bar.get_width() / 2, val),
                    xytext=(0, 14),
                    textcoords="offset points",
                    ha="center",
                    va="bottom",
                    fontsize=9,
                    fontweight="bold",
                    arrowprops=dict(arrowstyle="-", color="#333333", lw=0.8),
                )
            else:
                ax.text(
                    bar.get_x() + bar.get_width() / 2,
                    val + offset,
                    f"{val:.2f}",
                    ha="center",
                    va="bottom",
                    fontsize=fontsize,
                )

    axes[0].set_ylabel("Score")
    fig.suptitle("Fine-tuned precision and recall", fontsize=12, y=1.02)
    handles = [
        Patch(facecolor=PRECISION_COLOR, edgecolor="none", label="Precision"),
        Patch(facecolor=RECALL_COLOR, edgecolor="none", label="Recall"),
    ]
    fig.legend(handles=handles, loc="upper center", bbox_to_anchor=(0.5, -0.02), ncol=2, frameon=False)
    _save_fig(fig, "precision_recall_by_adapter.png")


def main() -> None:
    _apply_style()
    plot_train_eval_f1_heatmap()
    plot_train_eval_other_metrics()
    plot_ft_vs_prompting_f1()
    plot_precision_recall_by_adapter()
    print(f"Wrote figures to {EXP_STATIC} and {DOCS_STATIC}")


if __name__ == "__main__":
    main()
