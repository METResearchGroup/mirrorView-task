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

from data_platform.generate_features.s3_feature_campaign import CampaignObjectStore
from experiments.curate_study_2_phase_3_stimuli.join_flips import (
    available_cell_counts,
    cells_meet_targets,
    join_posts_to_flips,
)
from experiments.curate_study_2_phase_3_stimuli.load import load_flips, load_posts
from experiments.curate_study_2_phase_3_stimuli.sample_catalog import sample_catalog
from experiments.curate_study_2_phase_3_stimuli.sources import (
    JoinedFlipPool,
    OUTPUT_S3_BUCKET,
    pinned_sample_flips,
    pinned_sample_source,
    pinned_unified_flips,
    pinned_unified_source,
    sample_flips_cache_dir,
    sample_posts_cache_dir,
    unified_flips_cache_dir,
    unified_posts_cache_dir,
)
from experiments.curate_study_2_phase_3_stimuli.write import (
    print_run_summary,
    write_catalog,
    write_pause_results,
)

PAUSE_EXIT_CODE = 1


def main() -> int:
    """Write the 10,000 post catalog, or pause when a cell is short."""
    pool = _load_joined_pool()
    available = available_cell_counts(pool.rows)
    if not cells_meet_targets(available):
        print_run_summary(write_pause_results(available))
        return PAUSE_EXIT_CODE
    result = write_catalog(sample_catalog(pool.rows), available)
    print_run_summary(result)
    return 0


def _load_joined_pool() -> JoinedFlipPool:
    store = CampaignObjectStore(OUTPUT_S3_BUCKET)
    sample_posts = load_posts(pinned_sample_source(), store, sample_posts_cache_dir())
    unified_posts = load_posts(
        pinned_unified_source(), store, unified_posts_cache_dir()
    )
    sample_flips = load_flips(pinned_sample_flips(), store, sample_flips_cache_dir())
    unified_flips = load_flips(
        pinned_unified_flips(), store, unified_flips_cache_dir()
    )
    return join_posts_to_flips(sample_posts, sample_flips, unified_posts, unified_flips)


if __name__ == "__main__":
    sys.exit(main())
