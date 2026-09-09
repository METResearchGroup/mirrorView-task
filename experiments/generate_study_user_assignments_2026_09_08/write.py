"""Write assignment CSV locally and upload it once.

Run from the repo root:

    PYTHONPATH=. uv run python experiments/generate_study_user_assignments_2026_09_08/run.py \
      --remaining-labels s3://mirrorview-experimental-artifacts/experiments/calculate_required_label_count_per_stimulus_post_2026_09_09/required_label_count_per_stimulus_post.csv
"""

from __future__ import annotations

from pathlib import Path

from data_platform.generate_features.s3_feature_campaign import CampaignObjectStore


def write_assignment_csv(assignments: list[object], experiment_dir: Path) -> object:
    raise NotImplementedError


def upload_csv(body: bytes, store: CampaignObjectStore) -> str:
    raise NotImplementedError


def write_results_md(result: object, experiment_dir: Path) -> Path:
    raise NotImplementedError


def print_run_summary(result: object) -> None:
    raise NotImplementedError
