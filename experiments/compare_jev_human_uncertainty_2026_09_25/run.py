"""Compare Jev remove probabilities with five-labeler human remove counts.

Run from the repo root::

    PYTHONPATH=. uv run python experiments/compare_jev_human_uncertainty_2026_09_25/run.py
"""

from __future__ import annotations

from experiments.compare_jev_human_uncertainty_2026_09_25.compare import (
    build_comparison_frame,
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


def main() -> None:
    """Load both sources, write the figures and tables, and upload them."""
    raw = load_dataset(STUDY_PHASE_2_PART_2_AND_3_RESULTS_FULL, low_memory=False)
    human = build_five_labeler_counts(raw)
    jev = load_jev_labels()
    comparison = build_comparison_frame(human, jev)
    assert_pinned_counts(comparison)
    raise NotImplementedError


if __name__ == "__main__":
    main()
