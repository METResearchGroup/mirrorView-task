"""Compare Jev remove probabilities with five-labeler human remove counts.

Run from the repo root::

    PYTHONPATH=. uv run python experiments/compare_jev_human_uncertainty_2026_09_25/run.py
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from experiments.compare_jev_human_uncertainty_2026_09_25.compare import (
    build_comparison_frame,
)
from experiments.compare_jev_human_uncertainty_2026_09_25.constants import (
    FIGURE_DIRNAME,
    JEV_BUCKET,
    JOINED_FILENAME,
    RESULTS_FILENAME,
    TABLE_DIRNAME,
)
from experiments.compare_jev_human_uncertainty_2026_09_25.human_counts import (
    build_five_labeler_counts,
)
from experiments.compare_jev_human_uncertainty_2026_09_25.jev_labels import (
    load_jev_labels,
)
from experiments.compare_jev_human_uncertainty_2026_09_25.plots import write_figures
from experiments.compare_jev_human_uncertainty_2026_09_25.report import (
    assert_pinned_counts,
    upload_outputs,
    write_count_tables,
    write_results,
)
from shared.data.dataloader import load_dataset
from shared.data.registry import STUDY_PHASE_2_PART_2_AND_3_RESULTS_FULL


def _experiment_dir() -> Path:
    """Return the experiment directory."""
    return Path(__file__).resolve().parent


def _write_outputs(comparison: pd.DataFrame) -> tuple[Path, ...]:
    """Write the joined rows, tables, figures, and results file."""
    root = _experiment_dir()
    joined_path = root / JOINED_FILENAME
    joined_path.parent.mkdir(parents=True, exist_ok=True)
    comparison.to_parquet(joined_path, index=False)
    tables = write_count_tables(comparison, root / TABLE_DIRNAME)
    figures = write_figures(comparison, root / FIGURE_DIRNAME)
    results_path = write_results(comparison, root / RESULTS_FILENAME)
    return (results_path, joined_path, *figures, *tables)


def _print_summary(jev: pd.DataFrame, human: pd.DataFrame, comparison: pd.DataFrame) -> None:
    """Print the pinned row counts."""
    null_p_remove = int(jev["p_remove"].isna().sum())
    print(f"jev_rows={len(jev)}")
    print(f"null_p_remove={null_p_remove}")
    print(f"five_labeler_posts={len(human)}")
    print(f"inner_join_posts={len(comparison)}")


def main() -> None:
    """Load both sources, write the figures and tables, and upload them."""
    raw = load_dataset(STUDY_PHASE_2_PART_2_AND_3_RESULTS_FULL, low_memory=False)
    human = build_five_labeler_counts(raw)
    jev = load_jev_labels()
    comparison = build_comparison_frame(human, jev)
    assert_pinned_counts(comparison)
    upload_outputs(_write_outputs(comparison), JEV_BUCKET)
    _print_summary(jev, human, comparison)


if __name__ == "__main__":
    main()
