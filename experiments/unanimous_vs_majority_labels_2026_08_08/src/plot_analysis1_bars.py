"""Plot Analysis 1 bar charts by cohort.

Run from repo root::

    PYTHONPATH=. uv run python experiments/unanimous_vs_majority_labels_2026_08_08/src/plot_analysis1_bars.py
"""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

EXPERIMENT_ROOT = Path(__file__).resolve().parents[1]
SUMMARY_CSV = EXPERIMENT_ROOT / "outputs" / "analysis1" / "cell_summary.csv"
FIGURES_DIR = EXPERIMENT_ROOT / "outputs" / "analysis1" / "figures"

_COHORT_ORDER = (
    "unanimous_keep",
    "majority_keep",
    "majority_remove",
    "unanimous_remove",
)
_COHORT_LABELS = (
    "unanimous keep",
    "majority keep",
    "majority remove",
    "unanimous remove",
)

_PLOTS = (
    ("punctuation_density", "Median punctuation density", "bar_median_punctuation_density.png"),
    ("flesch_kincaid_grade", "Median FK grade", "bar_median_fk_grade.png"),
    ("flesch_reading_ease", "Median reading ease", "bar_median_reading_ease.png"),
    ("is_positive", "Proportion of positive content", "bar_proportion_positive.png"),
    ("is_intergroup", "Proportion with intergroup content", "bar_proportion_intergroup.png"),
    ("is_prime", "Proportion with PRIME content", "bar_proportion_prime.png"),
)


def _load_summary(path: Path) -> pd.DataFrame:
    """Load the Analysis 1 cohort summary in locked cohort order.

    Parameters
    ----------
    path
        Path to ``cell_summary.csv``.

    Returns
    -------
    pandas.DataFrame
        Summary rows ordered by cohort.

    Raises
    ------
    FileNotFoundError
        When the summary file is missing.
    ValueError
        When required cohorts or columns are missing.
    """
    if not path.is_file():
        raise FileNotFoundError(path.resolve())
    frame = pd.read_csv(path)
    if "cell" not in frame.columns:
        raise ValueError("Summary is missing the cell column")
    missing_cohorts = [c for c in _COHORT_ORDER if c not in set(frame["cell"])]
    if missing_cohorts:
        raise ValueError(f"Summary is missing cohorts: {missing_cohorts}")
    ordered = frame.set_index("cell").loc[list(_COHORT_ORDER)].reset_index()
    return ordered


def _plot_metric(
    values: list[float],
    *,
    title: str,
    output_path: Path,
) -> None:
    """Write one cohort bar chart.

    Parameters
    ----------
    values
        Metric values in ``_COHORT_ORDER``.
    title
        Chart title and y-axis label.
    output_path
        PNG path to write.
    """
    fig, ax = plt.subplots(figsize=(8, 4.5))
    ax.bar(_COHORT_LABELS, values, color="#4C78A8", width=0.7)
    ax.set_xlabel("Cohort")
    ax.set_ylabel(title)
    ax.set_title(title)
    ax.tick_params(axis="x", rotation=15)
    fig.tight_layout()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=160)
    plt.close(fig)


def write_analysis1_bar_charts(
    summary_csv: Path = SUMMARY_CSV,
    figures_dir: Path = FIGURES_DIR,
) -> list[Path]:
    """Write the locked Analysis 1 bar charts.

    Parameters
    ----------
    summary_csv
        Cohort summary CSV path.
    figures_dir
        Directory for PNG outputs.

    Returns
    -------
    list[pathlib.Path]
        Written figure paths.
    """
    summary = _load_summary(summary_csv)
    written: list[Path] = []
    for column, title, filename in _PLOTS:
        if column not in summary.columns:
            raise ValueError(f"Summary is missing column {column}")
        values = [float(v) for v in summary[column].tolist()]
        out_path = figures_dir / filename
        _plot_metric(values, title=title, output_path=out_path)
        written.append(out_path)
    return written


def main() -> None:
    """CLI entrypoint."""
    paths = write_analysis1_bar_charts()
    for path in paths:
        print(f"Wrote {path}")


if __name__ == "__main__":
    main()
