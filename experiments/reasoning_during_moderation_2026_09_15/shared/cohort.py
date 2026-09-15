"""Build the September three-group moderation cohort.

Run from the repo root:

    PYTHONPATH=. uv run python experiments/reasoning_during_moderation_2026_09_15/shared/cohort.py --write-counts
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd


def slim_trials(frame: pd.DataFrame) -> pd.DataFrame:
    raise NotImplementedError


def assert_stable_pair_text(trials: pd.DataFrame) -> None:
    raise NotImplementedError


def drop_conflicting_worker_posts(trials: pd.DataFrame) -> pd.DataFrame:
    raise NotImplementedError


def dedupe_worker_post(trials: pd.DataFrame) -> pd.DataFrame:
    raise NotImplementedError


def assign_group(keep_count: int, remove_count: int) -> str | None:
    raise NotImplementedError


def pair_order_for_post(post_id: str, seed: int = 0) -> tuple[str, str]:
    raise NotImplementedError


def build_cohort(trials: pd.DataFrame) -> pd.DataFrame:
    raise NotImplementedError


def write_cohort(
    cohort: pd.DataFrame,
    slim: pd.DataFrame,
    metadata: dict[str, object],
    experiment_dir: Path,
) -> None:
    raise NotImplementedError


def upload_cohort(body: bytes, key: str, store: object) -> None:
    raise NotImplementedError


def main() -> None:
    export = _download_export()
    trials = slim_trials(export)
    trials = drop_conflicting_worker_posts(trials)
    trials = dedupe_worker_post(trials)
    assert_stable_pair_text(trials)
    cohort = build_cohort(trials)
    _write_and_upload(cohort, trials)


def _download_export() -> pd.DataFrame:
    raise NotImplementedError


def _write_and_upload(cohort: pd.DataFrame, trials: pd.DataFrame) -> None:
    raise NotImplementedError


if __name__ == "__main__":
    main()
