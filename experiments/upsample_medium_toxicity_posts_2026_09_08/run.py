"""Sample 2,000 unused medium toxicity posts from leftover cleaned cells.

given AWS credentials from LAB_AWS_ACCESS_KEY_ID and LAB_AWS_ACCESS_KEY_SECRET
and the pinned combined parquet exists at SHA-256 f24ad1fd8c3709ffbbba9fb5dc953dcaee2f11ad8916ae21612b7f25cb5ca3f0
and the pinned 10200 sample exists at SHA-256 9788331f898aa27352dcdf32a962b5722aecc1da61a4638b7bbd77a404415ab9
when PYTHONPATH=. uv run python experiments/upsample_medium_toxicity_posts_2026_09_08/run.py
then sampled_rows=2000
and left_medium=1000
and right_medium=1000
and leftover_left_medium=15203
and right_medium_leftover_before_sample=3865
and every output llm_toxicity_tier is medium
and no output record_id is in the 10200 sample
and S3 object experiments/filter_posts_used_for_stimulus_dataset_2026_09_08/upsample_2000_medium_toxicity_posts.parquet exists
and its SHA-256 matches the local file
and RESULTS.md records those counts

given the S3 upsample key already exists
when the command is run again
then the process raises FileExistsError and does not change the combined source or the 10200 sample

Run from the repo root:

    PYTHONPATH=. uv run python experiments/upsample_medium_toxicity_posts_2026_09_08/run.py
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
from experiments.upsample_medium_toxicity_posts_2026_09_08.sample_leftover_medium import (
    sample_leftover_medium,
)
from experiments.upsample_medium_toxicity_posts_2026_09_08.sources import (
    combined_cache_dir,
    pinned_combined_source,
    pinned_sample_source,
    sample_cache_dir,
)
from experiments.upsample_medium_toxicity_posts_2026_09_08.write import (
    print_run_summary,
    write_upsampled_dataset,
)


def main() -> int:
    """Sample unused medium posts, write the parquet, and print counts."""
    leftover = sample_leftover_medium(_load_cleaned_combined(), _load_sample())
    result = write_upsampled_dataset(leftover)
    print_run_summary(result)
    return 0


def _load_cleaned_combined() -> pd.DataFrame:
    candidate = load_raw_candidate_dataset(
        pinned_combined_source(), cache_dir=combined_cache_dir()
    )
    cleaned, _summary = cleanup_raw_candidate_dataset(candidate)
    return cleaned


def _load_sample() -> pd.DataFrame:
    return load_raw_candidate_dataset(
        pinned_sample_source(), cache_dir=sample_cache_dir()
    )


if __name__ == "__main__":
    sys.exit(main())
