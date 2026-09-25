"""Draw the Jev and human comparison figures.

Run from the repo root::

    PYTHONPATH=. uv run pytest experiments/compare_jev_human_uncertainty_2026_09_25/tests/test_plots.py -q
"""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

from experiments.compare_jev_human_uncertainty_2026_09_25.constants import (
    BAR_WIDTH,
    DIFFERENCE_SCORE_MAX,
    DIFFERENCE_SCORE_MIN,
    FIGURE_FILENAMES,
    JEV_BIN_COUNT,
    JEV_BIN_EDGES,
    PROBABILITY_HIST_BINS,
    REQUIRED_LABELERS,
    Y_AXIS_LABEL,
)

_BAR_OFFSET = BAR_WIDTH / 2
_HUMAN_LABEL = "Human remove votes"
_JEV_LABEL = "Jev bin"
_REMOVE_AXIS = "Remove votes"
_PROBABILITY_AXIS = "Jev p_remove"
_DIFFERENCE_AXIS = "Human remove count minus Jev bin"


def _save(figure: plt.Figure, path: Path) -> Path:
    """Write one PNG and close the figure."""
    path.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(path, bbox_inches="tight")
    plt.close(figure)
    return path


def _heights(series: pd.Series, keys: range) -> list[int]:
    """Return post counts for each key, using 0 when a key is absent."""
    counts = series.value_counts()
    return [int(counts.get(key, 0)) for key in keys]


def plot_human_remove_counts(frame: pd.DataFrame, path: Path) -> Path:
    """Write bars for remove-vote counts 0 through 5.

    Returns
    -------
    pathlib.Path
        The PNG path.
    """
    keys = range(REQUIRED_LABELERS + 1)
    figure, axis = plt.subplots()
    axis.bar(list(keys), _heights(frame["n_remove"], keys))
    axis.set_xlabel(_REMOVE_AXIS)
    axis.set_ylabel(Y_AXIS_LABEL)
    return _save(figure, path)


def plot_jev_probabilities(frame: pd.DataFrame, path: Path) -> Path:
    """Write a 20-bin histogram of ``p_remove`` on 0 to 1.

    Returns
    -------
    pathlib.Path
        The PNG path.
    """
    figure, axis = plt.subplots()
    axis.hist(
        frame["p_remove"],
        bins=PROBABILITY_HIST_BINS,
        range=(JEV_BIN_EDGES[0], JEV_BIN_EDGES[-1]),
    )
    axis.set_xlabel(_PROBABILITY_AXIS)
    axis.set_ylabel(Y_AXIS_LABEL)
    return _save(figure, path)


def plot_jev_six_bins(frame: pd.DataFrame, path: Path) -> Path:
    """Write bars for Jev bins 0 through 5.

    Returns
    -------
    pathlib.Path
        The PNG path.
    """
    keys = range(JEV_BIN_COUNT)
    figure, axis = plt.subplots()
    axis.bar(list(keys), _heights(frame["jev_bin"], keys))
    axis.set_xticks(list(keys))
    axis.set_xticklabels([f"{key} remove" for key in keys])
    axis.set_ylabel(Y_AXIS_LABEL)
    return _save(figure, path)


def plot_overlay(frame: pd.DataFrame, path: Path) -> Path:
    """Write grouped bars of human remove counts and Jev bins.

    Returns
    -------
    pathlib.Path
        The PNG path.
    """
    keys = range(JEV_BIN_COUNT)
    human = _heights(frame["n_remove"], keys)
    jev = _heights(frame["jev_bin"], keys)
    left = [value - _BAR_OFFSET for value in keys]
    right = [value + _BAR_OFFSET for value in keys]
    figure, axis = plt.subplots()
    axis.bar(left, human, width=BAR_WIDTH, label=_HUMAN_LABEL)
    axis.bar(right, jev, width=BAR_WIDTH, label=_JEV_LABEL)
    axis.set_xticks(list(keys))
    axis.legend()
    axis.set_ylabel(Y_AXIS_LABEL)
    return _save(figure, path)


def plot_difference_scores(frame: pd.DataFrame, path: Path) -> Path:
    """Write bars for every difference score from -5 to 5.

    Returns
    -------
    pathlib.Path
        The PNG path.
    """
    keys = range(DIFFERENCE_SCORE_MIN, DIFFERENCE_SCORE_MAX + 1)
    figure, axis = plt.subplots()
    axis.bar(list(keys), _heights(frame["difference_score"], keys))
    axis.set_xlabel(_DIFFERENCE_AXIS)
    axis.set_ylabel(Y_AXIS_LABEL)
    return _save(figure, path)


def write_figures(
    frame: pd.DataFrame, figure_dir: Path
) -> tuple[Path, Path, Path, Path, Path]:
    """Write the five comparison figures and return their paths.

    Returns
    -------
    tuple
        PNG paths in figure order: human counts, probability histogram,
        six bins, overlay, and difference scores.
    """
    plotters = (
        plot_human_remove_counts,
        plot_jev_probabilities,
        plot_jev_six_bins,
        plot_overlay,
        plot_difference_scores,
    )
    paths = [
        plotter(frame, figure_dir / name)
        for plotter, name in zip(plotters, FIGURE_FILENAMES, strict=True)
    ]
    return (paths[0], paths[1], paths[2], paths[3], paths[4])
