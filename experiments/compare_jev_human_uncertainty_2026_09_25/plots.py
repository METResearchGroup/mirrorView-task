"""Draw the five Jev and human comparison figures.

Run from the repo root::

    PYTHONPATH=. uv run pytest experiments/compare_jev_human_uncertainty_2026_09_25/tests/test_plots.py -q
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd


def plot_human_remove_counts(frame: pd.DataFrame, path: Path) -> Path:
    """Write bars for remove-vote counts 0 through 5.

    Returns
    -------
    pathlib.Path
        The PNG path.
    """
    raise NotImplementedError


def plot_jev_probabilities(frame: pd.DataFrame, path: Path) -> Path:
    """Write a 20-bin histogram of ``p_remove`` on 0 to 1.

    Returns
    -------
    pathlib.Path
        The PNG path.
    """
    raise NotImplementedError


def plot_jev_five_bins(frame: pd.DataFrame, path: Path) -> Path:
    """Write bars for Jev bins 0 through 4.

    Returns
    -------
    pathlib.Path
        The PNG path.
    """
    raise NotImplementedError


def plot_overlay(frame: pd.DataFrame, path: Path) -> Path:
    """Write grouped bars of human remove counts and Jev bins.

    Returns
    -------
    pathlib.Path
        The PNG path.
    """
    raise NotImplementedError


def plot_difference_scores(frame: pd.DataFrame, path: Path) -> Path:
    """Write bars for every difference score from -4 to 5.

    Returns
    -------
    pathlib.Path
        The PNG path.
    """
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
