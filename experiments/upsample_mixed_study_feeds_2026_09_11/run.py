"""Clone 1000 mixed feeds and write study_user_assignments_overprovisioned.csv.

Run from the repo root:

    PYTHONPATH=. uv run python experiments/upsample_mixed_study_feeds_2026_09_11/run.py
"""

from __future__ import annotations

import sys

from experiments.upsample_mixed_study_feeds_2026_09_11.constants import (
    UpsampleRunResult,
)
from experiments.upsample_mixed_study_feeds_2026_09_11.split_batch import (
    require_original_party_prefix,
    split_rewritten,
)
from experiments.upsample_mixed_study_feeds_2026_09_11.upsample import (
    clone_mixed_feeds,
    concat_source_rows,
    sample_mixed_feeds,
    select_mixed_rows,
)
from experiments.upsample_mixed_study_feeds_2026_09_11.write import (
    upload_overprovisioned_csv,
    write_overprovisioned_batch,
)


def main() -> int:
    """Load, clone mixed feeds, write the overprovisioned CSV, and print counts."""
    _print_run_summary(_run_pipeline())
    return 0


def _run_pipeline() -> UpsampleRunResult:
    """Load, select mixed, sample, clone, concat, split, write, upload."""
    raise NotImplementedError


def _print_run_summary(result: UpsampleRunResult) -> None:
    raise NotImplementedError


if __name__ == "__main__":
    sys.exit(main())
