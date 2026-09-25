"""Draw the five Jev and human comparison figures.

Run from the repo root::

    PYTHONPATH=. uv run pytest experiments/compare_jev_human_uncertainty_2026_09_25/tests/test_plots.py -q
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd


def plot_human_remove_counts(frame: pd.DataFrame, path: Path) -> Path:
    raise NotImplementedError


def plot_jev_probabilities(frame: pd.DataFrame, path: Path) -> Path:
    raise NotImplementedError


def plot_jev_five_bins(frame: pd.DataFrame, path: Path) -> Path:
    raise NotImplementedError


def plot_overlay(frame: pd.DataFrame, path: Path) -> Path:
    raise NotImplementedError


def plot_difference_scores(frame: pd.DataFrame, path: Path) -> Path:
    raise NotImplementedError


def write_figures(frame: pd.DataFrame, figure_dir: Path) -> tuple[Path, Path, Path, Path, Path]:
    """Write the five comparison figures and return their paths."""
    return (
        plot_human_remove_counts(frame, figure_dir / "human_remove_counts.png"),
        plot_jev_probabilities(frame, figure_dir / "jev_probability.png"),
        plot_jev_five_bins(frame, figure_dir / "jev_five_bins.png"),
        plot_overlay(frame, figure_dir / "overlay_human_vs_jev.png"),
        plot_difference_scores(frame, figure_dir / "difference_score.png"),
    )
