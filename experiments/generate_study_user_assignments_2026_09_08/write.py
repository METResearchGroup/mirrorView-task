"""Write assignment CSV locally and upload it once.

Run from the repo root:

    PYTHONPATH=. uv run python experiments/generate_study_user_assignments_2026_09_08/run.py \
      --remaining-labels s3://mirrorview-experimental-artifacts/experiments/calculate_required_label_count_per_stimulus_post_2026_09_09/required_label_count_per_stimulus_post.csv
"""

from __future__ import annotations

from pathlib import Path

from data_platform.generate_features.s3_feature_campaign import CampaignObjectStore
from experiments.generate_study_user_assignments_2026_09_08.constants import (
    AssignmentRunResult,
    LocalCsvWrite,
    UserAssignment,
)


def write_assignment_csv(
    assignments: list[UserAssignment], experiment_dir: Path, created_at: str
) -> LocalCsvWrite:
    """Write one assignment row per user.

    Parameters
    ----------
    assignments
        Filled feeds in user-id order.
    experiment_dir
        Folder that receives the CSV.
    created_at
        Timestamp shared by every row in this run.

    Returns
    -------
    LocalCsvWrite
        Local path and CSV bytes.
    """
    raise NotImplementedError


def upload_csv(body: bytes, store: CampaignObjectStore) -> str:
    """Upload CSV bytes only if the S3 key does not already exist.

    Parameters
    ----------
    body
        CSV bytes already written locally.
    store
        Object store used only with ``put_new``.

    Returns
    -------
    str
        SHA-256 of the uploaded bytes.

    Raises
    ------
    FileExistsError
        When the destination S3 key already exists.
    """
    raise NotImplementedError


def write_results_md(result: AssignmentRunResult, experiment_dir: Path) -> Path:
    """Write RESULTS.md with feed-kind counts and extra labels.

    Parameters
    ----------
    result
        Counts and paths from the run.
    experiment_dir
        Folder that receives ``RESULTS.md``.

    Returns
    -------
    Path
        Path of the written report.
    """
    raise NotImplementedError


def print_run_summary(result: AssignmentRunResult) -> None:
    """Print feed-kind counts, extra labels, the S3 URI, and the CSV SHA-256."""
    raise NotImplementedError
