"""Write the experiment 3 human response-time table.

Run from the repo root:

    PYTHONPATH=. uv run python experiments/reasoning_during_moderation_2026_09_15/experiment3/run.py
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from data_platform.generate_features.s3_feature_campaign import CampaignObjectStore
from experiments.reasoning_during_moderation_2026_09_15.experiment3.summarize import (
    LEVEL_POST_MEAN,
    LEVEL_TRIAL,
    post_mean_summary,
    trial_level_summary,
)
from experiments.reasoning_during_moderation_2026_09_15.shared.constants import (
    COHORT_OUTPUT_DIR,
    EXPERIMENT_DIR,
    EXPERIMENT_S3_PREFIX,
    OUTPUT_S3_BUCKET,
    SLIM_TRIALS_FILENAME,
)

RESPONSE_TIME_SUMMARY_FILENAME = "response_time_summary.csv"
EXPERIMENT3_OUTPUT_DIR = EXPERIMENT_DIR / "experiment3" / "outputs"
EXPERIMENT3_S3_KEY = f"{EXPERIMENT_S3_PREFIX}/experiment3/{RESPONSE_TIME_SUMMARY_FILENAME}"
ZERO_COUNT = 0


def main() -> None:
    slim = _load_slim()
    summary = _combined_summary(slim)
    _require_nonzero_groups(summary)
    path = _write_csv(summary)
    _print_summary(summary)
    _upload_summary(path)


def _load_slim() -> pd.DataFrame:
    path = COHORT_OUTPUT_DIR / SLIM_TRIALS_FILENAME
    if not path.is_file():
        raise FileNotFoundError(path)
    return pd.read_parquet(path)


def _combined_summary(slim: pd.DataFrame) -> pd.DataFrame:
    trial = trial_level_summary(slim)
    post_mean = post_mean_summary(slim)
    return pd.concat([trial, post_mean], ignore_index=True)


def _require_nonzero_groups(summary: pd.DataFrame) -> None:
    trial = summary[summary["level"] == LEVEL_TRIAL]
    empty = trial[trial["n"] == ZERO_COUNT]
    if not empty.empty:
        groups = empty["group"].tolist()
        raise ValueError(f"no usable response times for groups {groups}")


def _write_csv(summary: pd.DataFrame) -> Path:
    path = EXPERIMENT3_OUTPUT_DIR / RESPONSE_TIME_SUMMARY_FILENAME
    path.parent.mkdir(parents=True, exist_ok=True)
    summary.to_csv(path, index=False)
    return path


def _print_summary(summary: pd.DataFrame) -> None:
    print(f"rows={len(summary)}")
    for _, row in summary.iterrows():
        print(f"level={row['level']} group={row['group']} n={row['n']}")
    trial = summary[summary["level"] == LEVEL_TRIAL]
    post_mean = summary[summary["level"] == LEVEL_POST_MEAN]
    print(f"level={LEVEL_TRIAL} groups={len(trial)}")
    print(f"level={LEVEL_POST_MEAN} groups={len(post_mean)}")


def _upload_summary(path: Path) -> None:
    """Upload the csv with put_new when absent, else replace the same key."""
    store = CampaignObjectStore(OUTPUT_S3_BUCKET)
    body = path.read_bytes()
    existing = store.get(EXPERIMENT3_S3_KEY)
    if existing is None:
        store.put_new(EXPERIMENT3_S3_KEY, body)
        return
    store.replace(EXPERIMENT3_S3_KEY, body, etag=existing.etag)


if __name__ == "__main__":
    main()
