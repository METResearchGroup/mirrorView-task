"""Curate the 10,000 post catalog, or stop if a cell is short.

Run from the repo root:

    PYTHONPATH=. uv run python experiments/curate_study_2_phase_3_stimuli/run.py
"""

from __future__ import annotations

import sys

from experiments.curate_study_2_phase_3_stimuli.join_flips import (
    available_cell_counts,
    cells_meet_targets,
    join_posts_to_flips,
)
from experiments.curate_study_2_phase_3_stimuli.load import load_flips, load_posts
from experiments.curate_study_2_phase_3_stimuli.sample_catalog import sample_catalog
from experiments.curate_study_2_phase_3_stimuli.sources import (
    pinned_sample_flips,
    pinned_sample_source,
    pinned_unified_flips,
    pinned_unified_source,
)
from experiments.curate_study_2_phase_3_stimuli.write import (
    print_run_summary,
    write_catalog,
    write_pause_results,
)


def main() -> int:
    """Load, join, count, then sample and write or pause."""
    raise NotImplementedError


if __name__ == "__main__":
    sys.exit(main())
