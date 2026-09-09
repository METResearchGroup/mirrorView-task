"""Curate the 10,000 post catalog, or stop if a cell is short.

given AWS credentials from LAB_AWS_ACCESS_KEY_ID and LAB_AWS_ACCESS_KEY_SECRET
and the 10200 sample flips and the unified flips exist
when PYTHONPATH=. uv run python experiments/curate_study_2_phase_3_stimuli/run.py
then stdout prints the available stance by toxicity table
and if every cell meets its target then catalog_rows=10000
and the CSV has the five old-catalog columns
and S3 object experiments/curate_study_2_phase_3_stimuli/flips.csv exists
and if any cell is short then exit code is 1
and flips.csv is not uploaded

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
