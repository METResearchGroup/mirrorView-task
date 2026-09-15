"""Write the experiment 3 human response-time table.

Run from the repo root:

    PYTHONPATH=. uv run python experiments/reasoning_during_moderation_2026_09_15/experiment3/run.py
"""

from __future__ import annotations

import pandas as pd

from experiments.reasoning_during_moderation_2026_09_15.experiment3.summarize import (
    post_mean_summary,
    trial_level_summary,
    usable_times,
)
from experiments.reasoning_during_moderation_2026_09_15.shared.constants import (
    COHORT_OUTPUT_DIR,
    SLIM_TRIALS_FILENAME,
)


def main() -> None:
    slim = _load_slim()
    _write_summary(slim)


def _load_slim() -> pd.DataFrame:
    path = COHORT_OUTPUT_DIR / SLIM_TRIALS_FILENAME
    if not path.is_file():
        raise FileNotFoundError(path)
    return pd.read_parquet(path)


def _write_summary(slim: pd.DataFrame) -> None:
    raise NotImplementedError


if __name__ == "__main__":
    main()
