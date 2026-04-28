"""Estimate assignment-to-export attrition by political party x condition.

This script compares users in the DynamoDB ``user_assignments`` table against
the latest ``scripts/mirrorview_pilot_data_*.csv`` export. A user is considered
eligible for attrition accounting only if they were assigned before the export
timestamp minus a grace period, so recently assigned users still have time to
finish and upload data.

To run:

    PYTHONPATH=. uv run python experiments/basic_summary_stats_2026_04_27/total_attrition.py
"""

from __future__ import annotations

import argparse
from datetime import datetime, timedelta
import json
from pathlib import Path
import re
from typing import Any

import boto3
import pandas as pd


AWS_REGION = "us-east-2"
USER_ASSIGNMENTS_TABLE = "user_assignments"
STUDY_ID = "mirrorview"
STUDY_ITERATION_ID = "pilot-phase2-v3"
DEFAULT_GRACE_MINUTES = 20

EXPORT_FILENAME_PATTERN = re.compile(
    r"^mirrorview_pilot_data_(\d{4}_\d{2}_\d{2}-\d{2}:\d{2}:\d{2})\.csv$"
)
TIMESTAMP_FORMAT = "%Y_%m_%d-%H:%M:%S"

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent
SCRIPTS_DIR = PROJECT_ROOT / "scripts"

CONDITION_DISPLAY_MAP = {
    "control": "control",
    "training": "training",
    "training_assisted": "training-assisted",
}
CONDITION_ORDER = ["control", "training", "training-assisted"]
PARTY_ORDER = ["democrat", "republican"]


def find_latest_export_csv() -> tuple[Path, datetime]:
    """Return the newest export CSV and its timestamp parsed from the filename."""
    candidates: list[tuple[datetime, Path]] = []
    for path in SCRIPTS_DIR.glob("mirrorview_pilot_data_*.csv"):
        match = EXPORT_FILENAME_PATTERN.match(path.name)
        if not match:
            continue
        candidates.append((datetime.strptime(match.group(1), TIMESTAMP_FORMAT), path))

    if not candidates:
        raise FileNotFoundError(f"No timestamped mirrorview_pilot_data_*.csv under {SCRIPTS_DIR}")

    export_timestamp, latest_path = max(candidates, key=lambda item: item[0])
    return latest_path, export_timestamp


def is_valid_user_id(user_id: object) -> bool:
    """Exclude manual/test placeholder Prolific IDs from attrition accounting."""
    text = str(user_id or "").strip().lower()
    return bool(text) and "pid" not in text and not text.startswith("manual-test-")


def parse_payload(item: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    """Parse the assignment payload and nested metadata JSON fields."""
    raw_payload = item.get("payload") or "{}"
    payload = json.loads(raw_payload) if isinstance(raw_payload, str) else raw_payload

    raw_metadata = payload.get("metadata") or "{}"
    metadata = json.loads(raw_metadata) if isinstance(raw_metadata, str) else raw_metadata
    return payload, metadata


def scan_user_assignments() -> list[dict[str, Any]]:
    """Return every item from the user assignment table."""
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
    """Parse assignment ``created_at`` timestamps, returning None for malformed rows."""
    try:
        return datetime.strptime(str(value), TIMESTAMP_FORMAT)
    except ValueError:
        return None


def load_exported_user_ids(export_path: Path) -> set[str]:
    """Return valid unique Prolific IDs present in the export CSV."""
    dataframe = pd.read_csv(export_path, usecols=["prolific_id"])
    return {
        str(user_id).strip()
        for user_id in dataframe["prolific_id"].dropna().unique()
        if is_valid_user_id(user_id)
    }


def build_assignment_frame(items: list[dict[str, Any]], *, cutoff: datetime) -> pd.DataFrame:
    """Build one row per eligible assigned user with party and condition labels."""
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
    """Create attrition counts and rates by party x condition."""
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
        table["missing_from_export"] / table["assigned_eligible"].replace(0, pd.NA)
    ).round(4)
    return table


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--grace-minutes",
        type=int,
        default=DEFAULT_GRACE_MINUTES,
        help=f"Exclude assignments newer than export timestamp minus this many minutes. Default: {DEFAULT_GRACE_MINUTES}.",
    )
    args = parser.parse_args()

    export_path, export_timestamp = find_latest_export_csv()
    cutoff = export_timestamp - timedelta(minutes=args.grace_minutes)
    exported_user_ids = load_exported_user_ids(export_path)

    assignment_items = scan_user_assignments()
    assignments = build_assignment_frame(assignment_items, cutoff=cutoff)
    assignments["found_in_export"] = assignments["user_id"].isin(exported_user_ids)

    table = format_attrition_table(assignments)

    print(f"Latest export: {export_path}")
    print(f"Export timestamp: {export_timestamp.strftime(TIMESTAMP_FORMAT)}")
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
