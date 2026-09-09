"""Promote 300 leftover right-medium posts to high and write the unified upsample.

given AWS credentials from LAB_AWS_ACCESS_KEY_ID and LAB_AWS_ACCESS_KEY_SECRET
and GOOGLE_API_KEY is set
and Step 1 wrote the 2000 medium parquet
when PYTHONPATH=. uv run python experiments/upsample_right_leaning_high_toxicity_posts_2026_09_08/run.py
then candidate_rows is at least 300
and promotions=300
and every promoted row is right and high
and unified_rows=2300
and unified_medium=2000
and unified_high=300
and no unified record_id is in the 10200 sample
and no promoted record_id is in the 2000 medium parquet
and no promoted source_record_id is in the pull request 260 JSON
and both S3 objects exist
and RESULTS.md records those counts

given the unified S3 key already exists
when the command is run again
then the process raises FileExistsError

Run from the repo root:

    PYTHONPATH=. uv run python experiments/upsample_right_leaning_high_toxicity_posts_2026_09_08/run.py
"""

from __future__ import annotations

import sys

import pandas as pd

from experiments.filter_posts_used_for_stimulus_dataset_2026_09_08.cleanup_raw_candidate_dataset import (
    cleanup_raw_candidate_dataset,
)
from experiments.filter_posts_used_for_stimulus_dataset_2026_09_08.load_raw_candidate_dataset import (
    load_raw_candidate_dataset,
)
from experiments.upsample_right_leaning_high_toxicity_posts_2026_09_08.candidates import (
    build_perspective_candidates,
)
from experiments.upsample_right_leaning_high_toxicity_posts_2026_09_08.promote import (
    promote_top_candidates,
)
from experiments.upsample_right_leaning_high_toxicity_posts_2026_09_08.score import (
    score_candidates,
)
from experiments.upsample_right_leaning_high_toxicity_posts_2026_09_08.sources import (
    pinned_combined_source,
    pinned_medium_upsample_source,
    pinned_sample_source,
)
from experiments.upsample_right_leaning_high_toxicity_posts_2026_09_08.write import (
    print_run_summary,
    write_unified_upsample,
)


def main() -> int:
    """Load, build candidates, score, promote, write, and print."""
    cleaned = _load_cleaned_combined()
    sample = _load_sample()
    medium_upsample = _load_medium_upsample()
    candidates = build_perspective_candidates(
        cleaned, sample, medium_upsample, _pr260_ids()
    )
    scores = score_candidates(candidates.rows)
    promotion = promote_top_candidates(candidates.rows, scores, medium_upsample)
    result = write_unified_upsample(candidates, promotion)
    print_run_summary(result)
    return 0


def _load_cleaned_combined() -> pd.DataFrame:
    raise NotImplementedError


def _load_sample() -> pd.DataFrame:
    raise NotImplementedError


def _load_medium_upsample() -> pd.DataFrame:
    raise NotImplementedError


def _pr260_ids() -> set[str]:
    raise NotImplementedError


if __name__ == "__main__":
    sys.exit(main())
