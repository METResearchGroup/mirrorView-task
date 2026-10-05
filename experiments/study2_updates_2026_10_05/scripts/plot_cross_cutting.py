"""Cross-cutting F1 summary figure for Study 2 writeup."""

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
EXP_STATIC = REPO_ROOT / "experiments/study2_updates_2026_10_05/static/cross_cutting"
DOCS_STATIC = REPO_ROOT / "docs/study_updates/static/study_2_writeup/cross_cutting"

DPI = 160
JEV_GREEN = "#54A24B"

MODEL_COLORS = {
    "Nova": "#4C78A8",
    "Qwen": "#F58518",
    "Terra": "#E45756",
    "Sonnet": "#B279A2",
}
DOT_MODELS = ["Nova", "Qwen", "Terra", "Sonnet"]
PROMPT_TUNED_DOT_MODELS = ["Nova", "Qwen"]

ADAPTER_COLORS = {
    "Unanimous": "#9e9ac8",
    "Split": "#6baed6",
    "All-label": "#2171b5",
}
ADAPTER_ORDER = ["Unanimous", "Split", "All-label"]

APPROACH_LABELS = ["Zero-shot", "Few-shot", "Prompt-tuned", "Fine-tuned"]
SLICE_KEYS = ["All", "Unanimous", "Split"]
SLICE_TITLES = {
    "All": "All posts",
    "Unanimous": "Unanimous posts",
    "Split": "Split posts",
}

# Jev bar F1 per approach and slice; other models as dots
PROMPTING_F1: dict[str, dict[str, dict[str, float]]] = {
    "Zero-shot": {
        "All": {
            "Jev": 0.529322,
            "Nova": 0.426029,
            "Qwen": 0.498773,
            "Terra": 0.316304,
            "Sonnet": 0.223602,
        },
        "Unanimous": {
            "Jev": 0.493617,
            "Nova": 0.256932,
            "Qwen": 0.395946,
            "Terra": 0.478528,
            "Sonnet": 0.382134,
        },
        "Split": {
            "Jev": 0.535016,
            "Nova": 0.467645,
            "Qwen": 0.517117,
            "Terra": 0.294281,
            "Sonnet": 0.203249,
        },
    },
    "Few-shot": {
        "All": {
            "Jev": 0.561910,
            "Nova": 0.428947,
            "Qwen": 0.463378,
            "Terra": 0.338110,
            "Sonnet": 0.330366,
        },
        "Unanimous": {
            "Jev": 0.664251,
            "Nova": 0.274428,
            "Qwen": 0.305225,
            "Terra": 0.526316,
            "Sonnet": 0.511931,
        },
        "Split": {
            "Jev": 0.547683,
            "Nova": 0.464521,
            "Qwen": 0.496046,
            "Terra": 0.312448,
            "Sonnet": 0.307005,
        },
    },
    "Prompt-tuned": {
        "All": {"Jev": 0.542148, "Nova": 0.281617, "Qwen": 0.466164},
        "Unanimous": {"Jev": 0.549451, "Nova": 0.452489, "Qwen": 0.355202},
        "Split": {"Jev": 0.541099, "Nova": 0.259358, "Qwen": 0.487348},
    },
}

FINETUNED_F1: dict[str, dict[str, float]] = {
    "All": {"Unanimous": 0.5447, "Split": 0.8853, "All-label": 0.9151},
    "Unanimous": {"Unanimous": 0.9840, "Split": 0.7776, "All-label": 0.9597},
    "Split": {"Unanimous": 0.4795, "Split": 0.8977, "All-label": 0.9100},
}

PROMPT_BAR_WIDTH = 0.55
ADAPTER_BAR_WIDTH = 0.22
ADAPTER_OFFSETS = np.array([-0.24, 0.0, 0.24])
DOT_SIZE = 36
JITTER_MAX = 0.06


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


def _jitter_x_positions(xs: list[float], ys: list[float]) -> list[float]:
    """Spread x positions when y values are nearly equal at the same base x."""
    out = list(xs)
    n = len(out)
    for i in range(n):
        for j in range(i + 1, n):
            if abs(out[i] - out[j]) < 1e-9 and abs(ys[i] - ys[j]) < 0.008:
                shift = min(JITTER_MAX, 0.03)
                out[i] -= shift / 2
                out[j] += shift / 2
    return out


def _annotate_bar(ax: plt.Axes, x: float, height: float, label_y_positions: list[float]) -> None:
    text_y = height + 0.015
    if text_y + 0.04 > 1.0:
        return
    for other_y in label_y_positions:
        if abs(text_y - other_y) < 0.035:
            return
    ax.text(
        x,
        text_y,
        f"{height:.2f}",
        ha="center",
        va="bottom",
        fontsize=8,
    )
    label_y_positions.append(text_y)


def _plot_panel(ax: plt.Axes, slice_key: str) -> None:
    x_ticks = np.arange(len(APPROACH_LABELS))
    label_y_positions: list[float] = []

    for ai, approach in enumerate(APPROACH_LABELS[:-1]):
        x_center = float(x_ticks[ai])
        jev_f1 = PROMPTING_F1[approach][slice_key]["Jev"]
        ax.bar(
            x_center,
            jev_f1,
            width=PROMPT_BAR_WIDTH,
            color=JEV_GREEN,
            edgecolor="none",
            zorder=1,
        )
        _annotate_bar(ax, x_center, jev_f1, label_y_positions)

        dot_models = (
            PROMPT_TUNED_DOT_MODELS if approach == "Prompt-tuned" else DOT_MODELS
        )
        ys = [PROMPTING_F1[approach][slice_key][m] for m in dot_models]
        xs = [x_center] * len(dot_models)
        xs = _jitter_x_positions(xs, ys)
        for x_dot, y_dot, model in zip(xs, ys, dot_models, strict=True):
            ax.scatter(
                x_dot,
                y_dot,
                s=DOT_SIZE,
                c=MODEL_COLORS[model],
                edgecolors="white",
                linewidths=0.8,
                zorder=3,
            )

    ft_idx = len(APPROACH_LABELS) - 1
    ft_center = float(x_ticks[ft_idx])
    for adapter, offset in zip(ADAPTER_ORDER, ADAPTER_OFFSETS, strict=True):
        val = FINETUNED_F1[slice_key][adapter]
        x_bar = ft_center + offset
        ax.bar(
            x_bar,
            val,
            width=ADAPTER_BAR_WIDTH,
            color=ADAPTER_COLORS[adapter],
            edgecolor="none",
            zorder=1,
        )
        if adapter == "All-label":
            _annotate_bar(ax, x_bar, val, label_y_positions)

    ax.set_title(SLICE_TITLES[slice_key])
    ax.set_xticks(x_ticks)
    ax.set_xticklabels(APPROACH_LABELS, rotation=0)
    ax.set_ylim(0, 1)
    ax.set_xlim(-0.55, len(APPROACH_LABELS) - 0.45)
    ax.set_yticks(np.linspace(0, 1, 6))
    ax.grid(True, axis="y", color="#eeeeee", linewidth=0.8, zorder=0)
    _hide_top_right(ax)


def _save_fig(fig: plt.Figure, filename: str) -> None:
    EXP_STATIC.mkdir(parents=True, exist_ok=True)
    DOCS_STATIC.mkdir(parents=True, exist_ok=True)
    exp_path = EXP_STATIC / filename
    fig.savefig(exp_path, dpi=DPI, bbox_inches="tight", facecolor="white")
    shutil.copy2(exp_path, DOCS_STATIC / filename)
    plt.close(fig)


def main() -> None:
    _apply_style()
    fig, axes = plt.subplots(
        1,
        3,
        figsize=(12.5, 4.6),
        sharey=True,
        constrained_layout=False,
    )
    fig.subplots_adjust(bottom=0.28, top=0.88, wspace=0.12)
    for ax, slice_key in zip(axes, SLICE_KEYS, strict=True):
        _plot_panel(ax, slice_key)
    axes[0].set_ylabel("F1")
    fig.suptitle("F1 by approach", fontsize=12)
    model_handles = [
        Line2D(
            [0],
            [0],
            marker="o",
            color="w",
            markerfacecolor=MODEL_COLORS[m],
            markeredgecolor="white",
            markeredgewidth=0.8,
            markersize=7,
            label=m,
        )
        for m in DOT_MODELS
    ]
    model_handles.append(
        Patch(facecolor=JEV_GREEN, edgecolor="none", label="Best prompting (Jev)")
    )
    adapter_handles = [
        Patch(facecolor=ADAPTER_COLORS[a], edgecolor="none", label=a)
        for a in ADAPTER_ORDER
    ]
    fig.legend(
        handles=model_handles + adapter_handles,
        loc="upper center",
        bbox_to_anchor=(0.5, 0.02),
        ncol=4,
        frameon=False,
        fontsize=10,
    )
    _save_fig(fig, "approach_f1.png")
    print(f"Wrote approach_f1.png to {EXP_STATIC} and {DOCS_STATIC}")


if __name__ == "__main__":
    main()
