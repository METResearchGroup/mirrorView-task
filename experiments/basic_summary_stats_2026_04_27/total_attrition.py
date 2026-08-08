"""Assignment-to-completion attrition by party × condition for Part 1 full results.

Compares DynamoDB ``user_assignments`` for the Part 1 study iteration against
prolific IDs in ``STUDY_PHASE_2_PART_1_RESULTS_FULL``. Assignments newer than the
results-file mtime minus a grace window are excluded so in-flight participants
are not counted as attrition.

Run from the repo root:

    PYTHONPATH=. uv run python experiments/basic_summary_stats_2026_04_27/total_attrition.py
"""

from __future__ import annotations

import argparse
from datetime import datetime, timedelta
import json
from pathlib import Path
from typing import Any

import boto3
import pandas as pd

from shared.data import registry
from shared.data.registry import STUDY_PHASE_2_PART_1_RESULTS_FULL


AWS_REGION = "us-east-2"
USER_ASSIGNMENTS_TABLE = "user_assignments"
STUDY_ID = "mirrorview"
STUDY_ITERATION_ID = "pilot-phase2-v3"
DEFAULT_GRACE_MINUTES = 20

TIMESTAMP_FORMAT = "%Y_%m_%d-%H:%M:%S"

CONDITION_DISPLAY_MAP = {
    "control": "control",
    "training": "training",
    "training_assisted": "training-assisted",
}
CONDITION_ORDER = ["control", "training", "training-assisted"]
PARTY_ORDER = ["democrat", "republican"]


def resolve_results_csv() -> tuple[Path, datetime]:
    """Resolve the registered full-results CSV and treat its mtime as export time.

    Returns
    -------
    path, export_timestamp
        Absolute path and local-time mtime used for the grace-period cutoff.

    Raises
    ------
    FileNotFoundError
        If the registered CSV is missing on disk.
    """
    path = registry.resolve_path(STUDY_PHASE_2_PART_1_RESULTS_FULL)
    if not path.is_file():
        raise FileNotFoundError(f"Dataset file not found: {path}")
    export_timestamp = datetime.fromtimestamp(path.stat().st_mtime)
    return path, export_timestamp


def is_valid_user_id(user_id: object) -> bool:
    """Return whether ``user_id`` looks like a real Prolific ID (not a test stub)."""
    text = str(user_id or "").strip().lower()
    return bool(text) and "pid" not in text and not text.startswith("manual-test-")


def parse_payload(item: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    """Decode an assignment item's ``payload`` and nested ``metadata`` JSON.

    Accepts values that are already dicts or JSON strings.
    """
    raw_payload = item.get("payload") or "{}"
    payload = json.loads(raw_payload) if isinstance(raw_payload, str) else raw_payload

    raw_metadata = payload.get("metadata") or "{}"
    metadata = json.loads(raw_metadata) if isinstance(raw_metadata, str) else raw_metadata
    return payload, metadata


def scan_user_assignments() -> list[dict[str, Any]]:
    """Scan all items from the configured DynamoDB assignments table."""
    table = boto3.resource("dynamodb", region_name=AWS_REGION).Table(USER_ASSIGNMENTS_TABLE)
    items: list[dict[str, Any]] = []
    kwargs: dict[str, Any] = {}

    while True:
        response = table.scan(**kwargs)
        items.extend(response.get("Items", []))
        last_key = response.get("LastEvaluatedKey")
        if not last_key:
            return items
        kwargs["ExclusiveStartKey"] = last_key


def parse_created_at(value: object) -> datetime | None:
    """Parse an assignment ``created_at`` string, or return ``None`` if malformed."""
    try:
        return datetime.strptime(str(value), TIMESTAMP_FORMAT)
    except ValueError:
        return None


def load_exported_user_ids(export_path: Path) -> set[str]:
    """Return the set of valid unique ``prolific_id`` values in ``export_path``."""
    dataframe = pd.read_csv(export_path, usecols=["prolific_id"])
    return {
        str(user_id).strip()
        for user_id in dataframe["prolific_id"].dropna().unique()
        if is_valid_user_id(user_id)
    }


def build_assignment_frame(items: list[dict[str, Any]], *, cutoff: datetime) -> pd.DataFrame:
    """Filter assignments to the Part 1 iteration and eligibility cutoff.

    Keeps only non-test users with known party and condition who were assigned
    strictly before ``cutoff``.

    Parameters
    ----------
    cutoff : datetime
        Exclusive upper bound on ``created_at`` (export time minus grace).

    Returns
    -------
    pandas.DataFrame
        One row per eligible user: ``user_id``, ``created_at``, ``party_group``,
        ``condition``, ``assignment_id``. Empty if none qualify.
    """
    rows: list[dict[str, Any]] = []

    for item in items:
        if item.get("study_id") != STUDY_ID:
            continue
        if item.get("study_iteration_id") != STUDY_ITERATION_ID:
            continue

        user_id = str(item.get("user_id") or "").strip()
        if not is_valid_user_id(user_id):
            continue

        created_at = parse_created_at(item.get("created_at"))
        if created_at is None or created_at >= cutoff:
            continue

        payload, metadata = parse_payload(item)
        party = str(metadata.get("political_party") or "").strip().lower()
        condition = str(metadata.get("condition") or "").strip().lower()
        if party not in PARTY_ORDER or condition not in CONDITION_DISPLAY_MAP:
            continue

        rows.append(
            {
                "user_id": user_id,
                "created_at": created_at,
                "party_group": party,
                "condition": CONDITION_DISPLAY_MAP[condition],
                "assignment_id": payload.get("assignment_id"),
            }
        )

    return pd.DataFrame(rows)


def format_attrition_table(assignments: pd.DataFrame) -> pd.DataFrame:
    """Summarize attrition rates by party × condition.

    Parameters
    ----------
    assignments : pandas.DataFrame
        Must include ``user_id``, ``party_group``, ``condition``, and boolean
        ``found_in_export``.

    Returns
    -------
    pandas.DataFrame
        Columns ``assigned_eligible``, ``found_in_export``, ``missing_from_export``,
        and ``attrition_rate`` (NA when a cell has zero eligible assignments).
    """
    if assignments.empty:
        index = pd.MultiIndex.from_product([PARTY_ORDER, CONDITION_ORDER])
        return pd.DataFrame(
            0,
            index=index,
            columns=["assigned_eligible", "found_in_export", "missing_from_export"],
        )

    table = (
        assignments.groupby(["party_group", "condition"])
        .agg(
            assigned_eligible=("user_id", "nunique"),
            found_in_export=("found_in_export", "sum"),
        )
        .reindex(pd.MultiIndex.from_product([PARTY_ORDER, CONDITION_ORDER]), fill_value=0)
    )
    table["missing_from_export"] = table["assigned_eligible"] - table["found_in_export"]
    table["attrition_rate"] = (
        (table["missing_from_export"] / table["assigned_eligible"])
        .where(table["assigned_eligible"] > 0)
        .round(4)
    )
    return table


def main() -> None:
    """Print attrition totals and the party × condition attrition table."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--grace-minutes",
        type=int,
        default=DEFAULT_GRACE_MINUTES,
        help=f"Exclude assignments newer than export timestamp minus this many minutes. Default: {DEFAULT_GRACE_MINUTES}.",
    )
    args = parser.parse_args()

    export_path, export_timestamp = resolve_results_csv()
    cutoff = export_timestamp - timedelta(minutes=args.grace_minutes)
    exported_user_ids = load_exported_user_ids(export_path)

    assignment_items = scan_user_assignments()
    assignments = build_assignment_frame(assignment_items, cutoff=cutoff)
    assignments["found_in_export"] = assignments["user_id"].isin(exported_user_ids)

    table = format_attrition_table(assignments)

    print(f"Dataset: {STUDY_PHASE_2_PART_1_RESULTS_FULL}")
    print(f"Results CSV: {export_path}")
    print(f"Export timestamp (file mtime): {export_timestamp.strftime(TIMESTAMP_FORMAT)}")
    print(
        f"Eligibility cutoff: assigned before {cutoff.strftime(TIMESTAMP_FORMAT)} "
        f"({args.grace_minutes} minute grace period)"
    )
    print(f"Exported valid unique prolific_id(s): {len(exported_user_ids)}")
    print(f"Eligible assigned user(s): {assignments['user_id'].nunique() if not assignments.empty else 0}")
    print(f"Eligible assigned user(s) found in export: {int(assignments['found_in_export'].sum()) if not assignments.empty else 0}")
    print(
        f"Eligible assigned user(s) missing from export: "
        f"{int((~assignments['found_in_export']).sum()) if not assignments.empty else 0}"
    )

    print("\nAttrition by political party x condition")
    print(table.to_string())


if __name__ == "__main__":
    main()
