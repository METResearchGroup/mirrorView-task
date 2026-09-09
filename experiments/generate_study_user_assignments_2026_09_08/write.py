"""Write assignment CSV locally and upload it once.

Run from the repo root:

    PYTHONPATH=. uv run python experiments/generate_study_user_assignments_2026_09_08/run.py \
      --remaining-labels s3://mirrorview-experimental-artifacts/experiments/calculate_required_label_count_per_stimulus_post_2026_09_09/required_label_count_per_stimulus_post.csv
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from data_platform.generate_features.s3_feature_campaign import (
    CampaignObjectStore,
    s3_uri,
)
from data_platform.utils.object_store import sha256_hex
from experiments.calculate_required_label_count_per_stimulus_post_2026_09_09.constants import (
    pinned_new_catalog,
)
from experiments.generate_study_user_assignments_2026_09_08.constants import (
    ASSIGNED_POST_IDS_COLUMN,
    ASSIGNMENT_COLUMNS,
    ASSIGNMENT_ID_COLUMN,
    AssignmentRunResult,
    CONDITION_COLUMN,
    CREATED_AT_COLUMN,
    CSV_ENCODING,
    CSV_INDEX,
    DATASET_FILENAME,
    EMPTY_POLITICAL_PARTY,
    LocalCsvWrite,
    OUTPUT_S3_BUCKET,
    OUTPUT_S3_KEY,
    PINNED_REMAINING_LABELS_S3_URI,
    PINNED_REMAINING_LABELS_SHA256,
    POLITICAL_PARTY_COLUMN,
    RESULTS_FILENAME,
    TRAINING_ASSISTED_CONDITION,
    USER_ID_PREFIX,
    USER_ID_WIDTH,
    UserAssignment,
)

RUN_COMMAND = """export AWS_ACCESS_KEY_ID="$LAB_AWS_ACCESS_KEY_ID"
export AWS_SECRET_ACCESS_KEY="$LAB_AWS_ACCESS_KEY_SECRET"

PYTHONPATH=. uv run python experiments/generate_study_user_assignments_2026_09_08/run.py \\
  --remaining-labels s3://mirrorview-experimental-artifacts/experiments/calculate_required_label_count_per_stimulus_post_2026_09_09/required_label_count_per_stimulus_post.csv"""

PYTEST_COMMAND = (
    "PYTHONPATH=. uv run pytest "
    "experiments/generate_study_user_assignments_2026_09_08/tests -q"
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
    frame = pd.DataFrame(
        [_assignment_row(assignment, created_at) for assignment in assignments]
    )
    ordered = frame.loc[:, list(ASSIGNMENT_COLUMNS)].sort_values(ASSIGNMENT_ID_COLUMN)
    body = ordered.to_csv(index=CSV_INDEX).encode(CSV_ENCODING)
    path = experiment_dir / DATASET_FILENAME
    path.write_bytes(body)
    return LocalCsvWrite(path=path, body=body)


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
    store.put_new(OUTPUT_S3_KEY, body)
    return sha256_hex(body)


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
    path = experiment_dir / RESULTS_FILENAME
    path.write_text(_results_markdown(result))
    return path


def print_run_summary(result: AssignmentRunResult) -> None:
    """Print feed-kind counts, extra labels, the S3 URI, and the CSV SHA-256."""
    print(f"ten_ten_count={result.ten_ten_count}")
    print(f"left_only_count={result.left_only_count}")
    print(f"user_count={result.user_count}")
    print(f"assignment_rows={result.assignment_rows}")
    print(f"assignment_slots={result.assignment_slots}")
    print(f"extra_labels={result.extra_labels}")
    print(f"unused_remaining={result.unused_remaining}")
    print(f"s3_uri={result.s3_uri}")
    print(f"csv_sha256={result.csv_sha256}")


def _assignment_row(assignment: UserAssignment, created_at: str) -> dict[str, str]:
    return {
        ASSIGNMENT_ID_COLUMN: f"{USER_ID_PREFIX}{assignment.user_id:0{USER_ID_WIDTH}d}",
        ASSIGNED_POST_IDS_COLUMN: json.dumps(list(assignment.post_ids)),
        POLITICAL_PARTY_COLUMN: EMPTY_POLITICAL_PARTY,
        CONDITION_COLUMN: TRAINING_ASSISTED_CONDITION,
        CREATED_AT_COLUMN: created_at,
    }


def _results_markdown(result: AssignmentRunResult) -> str:
    return "\n".join(
        [
            "# Generate study user assignments, results",
            "",
            "## Tests",
            "",
            f"`{PYTEST_COMMAND}` exited 0.",
            "",
            "## Command",
            "",
            "```bash",
            RUN_COMMAND,
            "```",
            "",
            "## Files",
            "",
            "| File | Path | SHA-256 |",
            "| ---- | ---- | ------- |",
            f"| Remaining labels | `{PINNED_REMAINING_LABELS_S3_URI}` | `{PINNED_REMAINING_LABELS_SHA256}` |",
            f"| New catalog | `{pinned_new_catalog().s3_uri}` | `{pinned_new_catalog().sha256}` |",
            f"| Local CSV | `{result.local_path}` | `{result.csv_sha256}` |",
            f"| S3 CSV | `{result.s3_uri}` | `{result.csv_sha256}` |",
            "",
            "## Feed kinds",
            "",
            f"Users 1 through {result.ten_ten_count} have 10 left and 10 right. "
            f"Users {result.ten_ten_count + 1} through {result.user_count} have "
            "20 left and 0 right.",
            "",
            "| Count | Value |",
            "| ----- | ----: |",
            f"| 10:10 feeds | {result.ten_ten_count} |",
            f"| Left-only feeds | {result.left_only_count} |",
            f"| Users | {result.user_count} |",
            f"| Assignment slots | {result.assignment_slots} |",
            f"| Extra labels | {result.extra_labels} |",
            f"| Extra left | {result.extra_left} |",
            f"| Extra right | {result.extra_right} |",
            f"| Unused remaining | {result.unused_remaining} |",
            "",
            "## Remaining versus assigned slots by cell",
            "",
            "| Cell | Remaining | Assigned slots |",
            "| ---- | --------: | -------------: |",
            *_cell_rows(result),
            "",
        ]
    )


def _cell_rows(result: AssignmentRunResult) -> list[str]:
    labels = (
        "1 left low",
        "2 left middle",
        "3 left high",
        "4 right low",
        "5 right middle",
        "6 right high",
    )
    return [
        f"| {label} | {remaining} | {assigned} |"
        for label, remaining, assigned in zip(
            labels, result.remaining_by_cell, result.assigned_by_cell
        )
    ]
