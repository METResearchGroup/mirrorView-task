"""Generate prompt-tuning comparison figures for Study 2 writeup."""

from __future__ import annotations

import shutil
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Patch

REPO_ROOT = Path(__file__).resolve().parents[3]
EXP_STATIC = REPO_ROOT / "experiments/study2_updates_2026_10_05/static/prompt_tuning"
DOCS_STATIC = REPO_ROOT / "docs/study_updates/static/study_2_writeup/prompt_tuning"

DPI = 160

TUNED_MODELS = ["Nova", "Qwen", "Jev"]
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

STAGE_ORDER = ["Zero-shot", "Few-shot", "Optimized"]
STAGE_KEYS = ["zero", "few", "optimized"]

# (f1, accuracy, recall, precision) per model per slice
ZERO: dict[str, dict[str, tuple[float, float, float, float]]] = {
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
    "Jev": {
        "All": (0.529322, 0.712621, 0.761792, 0.405561),
        "Unanimous": (0.493617, 0.853123, 0.941558, 0.334487),
        "Split": (0.535016, 0.655367, 0.740977, 0.418649),
    },
}

FEW: dict[str, dict[str, tuple[float, float, float, float]]] = {
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
    "Jev": {
        "All": (0.561910, 0.787517, 0.642616, 0.499214),
        "Unanimous": (0.664251, 0.931290, 0.898693, 0.526820),
        "Split": (0.547683, 0.729001, 0.613158, 0.494842),
    },
}

OPTIMIZED: dict[str, dict[str, tuple[float, float, float, float]]] = {
    "Nova": {
        "All": (0.281617, 0.803031, 0.182063, 0.621404),
        "Unanimous": (0.452489, 0.940188, 0.326797, 0.735294),
        "Split": (0.259358, 0.747209, 0.165414, 0.600273),
    },
    "Qwen": {
        "All": (0.466164, 0.640738, 0.739717, 0.340313),
        "Unanimous": (0.355202, 0.759516, 0.875817, 0.222776),
        "Split": (0.487348, 0.592395, 0.724060, 0.367277),
    },
    "Jev": {
        "All": (0.542148, 0.739043, 0.728591, 0.431682),
        "Unanimous": (0.549451, 0.888532, 0.898693, 0.395683),
        "Split": (0.541099, 0.678201, 0.709023, 0.437486),
    },
}

STAGE_METRICS = {"zero": ZERO, "few": FEW, "optimized": OPTIMIZED}

TERRA_HOLDOUT_ORIGINAL = np.array([[30, 1], [14, 16]], dtype=int)
TERRA_HOLDOUT_OPTIMIZED = np.array([[22, 9], [2, 28]], dtype=int)
TERRA_HOLDOUT_STATS = {
    "original": {"precision": 0.94, "recall": 0.53},
    "optimized": {"precision": 0.76, "recall": 0.93},
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


def _f1_by_stage(model: str, slice_key: str) -> list[float]:
    return [STAGE_METRICS[stage][model][slice_key][0] for stage in STAGE_KEYS]


def plot_f1_three_stage() -> None:
    fig, axes = plt.subplots(1, 3, figsize=(11.5, 3.8), sharey=True, constrained_layout=True)
    n_models = len(TUNED_MODELS)
    n_stages = len(STAGE_ORDER)
    x = np.arange(n_stages)
    group_width = 0.75
    bar_width = group_width / n_models

    for ax, slice_key in zip(axes, SLICE_ORDER, strict=True):
        for i, model in enumerate(TUNED_MODELS):
            offsets = x - group_width / 2 + bar_width / 2 + i * bar_width
            f1_vals = _f1_by_stage(model, slice_key)
            bars = ax.bar(
                offsets,
                f1_vals,
                width=bar_width * 0.95,
                color=MODEL_COLORS[model],
                label=model if slice_key == "All" else None,
                edgecolor="none",
            )
            for bar, val in zip(bars, f1_vals, strict=True):
                if bar.get_height() > 0.08:
                    ax.text(
                        bar.get_x() + bar.get_width() / 2,
                        bar.get_height() + 0.02,
                        f"{val:.2f}",
                        ha="center",
                        va="bottom",
                        fontsize=8,
                        color="#333333",
                    )
        ax.set_title(SLICE_TITLES[slice_key])
        ax.set_xticks(x)
        ax.set_xticklabels(STAGE_ORDER, rotation=0)
        ax.set_ylim(0, 1)
        ax.set_ylabel("F1")
        _hide_top_right(ax)

    handles = [Patch(facecolor=MODEL_COLORS[m], edgecolor="none", label=m) for m in TUNED_MODELS]
    fig.suptitle("F1 across prompting stages", y=1.02, fontsize=13)
    fig.legend(handles=handles, loc="upper center", bbox_to_anchor=(0.5, -0.02), ncol=3, frameon=False)
    _save_fig(fig, "f1_three_stage.png")


def _annotate_confusion(ax: plt.Axes, matrix: np.ndarray, im: plt.AxesImage) -> None:
    vmax = float(matrix.max()) if matrix.max() > 0 else 1.0
    for row in range(matrix.shape[0]):
        for col in range(matrix.shape[1]):
            value = int(matrix[row, col])
            color = "white" if value > vmax * 0.55 else "black"
            ax.text(col, row, str(value), ha="center", va="center", color=color, fontsize=12)


def plot_terra_holdout_confusion() -> None:
    fig, axes = plt.subplots(1, 2, figsize=(8.5, 4.2), constrained_layout=True)
    tick_labels = ["Keep", "Remove"]
    panels = [
        ("Original prompt", TERRA_HOLDOUT_ORIGINAL, TERRA_HOLDOUT_STATS["original"]),
        ("Optimized prompt", TERRA_HOLDOUT_OPTIMIZED, TERRA_HOLDOUT_STATS["optimized"]),
    ]

    for ax, (title, matrix, stats) in zip(axes, panels, strict=True):
        im = ax.imshow(matrix, cmap="Blues", vmin=0, vmax=max(matrix.max(), 1))
        _annotate_confusion(ax, matrix, im)
        ax.set_title(title, pad=8)
        ax.set_xticks([0, 1], labels=tick_labels)
        ax.set_yticks([0, 1], labels=tick_labels)
        ax.set_xlabel("Predicted")
        ax.set_ylabel("True")
        subtitle = (
            f"Precision {stats['precision']:.2f}, recall {stats['recall']:.2f}"
        )
        ax.text(0.5, -0.22, subtitle, transform=ax.transAxes, ha="center", va="top", fontsize=10)

    fig.suptitle("GPT-5.6 Terra hold-out (n=61)", y=1.02, fontsize=13)
    fig.text(
        0.5,
        -0.06,
        "Counts reconstructed from reported rates.",
        ha="center",
        va="top",
        fontsize=9,
        color="#555555",
    )
    _save_fig(fig, "terra_holdout_confusion.png")


def plot_transfer_f1_delta() -> None:
    fig, axes = plt.subplots(1, 3, figsize=(11, 3.6), sharey=True, constrained_layout=True)
    x = np.arange(len(TUNED_MODELS))
    width = 0.6

    for ax, slice_key in zip(axes, SLICE_ORDER, strict=True):
        deltas = [
            OPTIMIZED[m][slice_key][0] - FEW[m][slice_key][0] for m in TUNED_MODELS
        ]
        colors = [MODEL_COLORS[m] for m in TUNED_MODELS]
        ax.bar(x, deltas, width=width, color=colors, edgecolor="none")
        ax.axhline(0, color="#333333", linewidth=0.8, linestyle="-")
        ax.set_title(SLICE_TITLES[slice_key])
        ax.set_xticks(x, labels=TUNED_MODELS)
        ax.set_ylabel("Optimized F1 minus few-shot F1")
        y_min = min(deltas + [0])
        y_max = max(deltas + [0])
        pad = max(0.05, (y_max - y_min) * 0.15)
        ax.set_ylim(y_min - pad, y_max + pad)
        _hide_top_right(ax)

    fig.suptitle("F1 change from the Terra-tuned prompt", y=1.02, fontsize=13)
    _save_fig(fig, "transfer_f1_delta.png")


def main() -> None:
    _apply_style()
    plot_f1_three_stage()
    plot_terra_holdout_confusion()
    plot_transfer_f1_delta()
    print(f"Wrote figures to {EXP_STATIC} and {DOCS_STATIC}")


if __name__ == "__main__":
    main()
