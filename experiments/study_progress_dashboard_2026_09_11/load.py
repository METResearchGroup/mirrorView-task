"""Load the September 2026 study export and DynamoDB assignment rows."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

import boto3
import pandas as pd

from experiments.study_progress_dashboard_2026_09_11.constants import (
    AWS_REGION,
    INVALID_PROLIFIC_SUBSTRINGS,
    PARTY_ORDER,
    STUDY_ID,
    STUDY_ITERATION_ID,
    TIMESTAMP_FORMAT,
    USER_ASSIGNMENTS_TABLE,
)
from lib.timestamp_utils import get_current_timestamp
from scripts.export_study_results import (
    BUCKET_NAME,
    download_csvs,
    filter_manual_test_rows,
    list_csv_keys,
    load_downloaded_csvs,
    utc_midnight_ms,
)


def is_valid_user_id(user_id: object) -> bool:
    """Return False for placeholder, manual-test, and dev Prolific ids."""
    text = str(user_id or "").strip().lower()
    if not text:
        return False
    return not any(sub in text for sub in INVALID_PROLIFIC_SUBSTRINGS)


def export_study_csv(output_dir: Path, *, since_date, force_download: bool) -> Path:
    """Download prolific CSVs from the study bucket and write one combined CSV."""
    output_dir.mkdir(parents=True, exist_ok=True)
    min_file_epoch_ms = utc_midnight_ms(since_date)
    s3_client = boto3.client("s3", region_name=AWS_REGION)
    csv_keys = list_csv_keys(s3_client, min_file_epoch_ms=min_file_epoch_ms)
    local_paths = download_csvs(s3_client, csv_keys, force_redownload=force_download)
    combined = filter_manual_test_rows(load_downloaded_csvs(local_paths))
    output_path = output_dir / f"export_{BUCKET_NAME}_{get_current_timestamp()}.csv"
    combined.to_csv(output_path, index=False)
    return output_path


def load_export_csv(path: Path) -> pd.DataFrame:
    """Read a combined jsPsych export CSV."""
    return pd.read_csv(path)


def count_export_files(export_df: pd.DataFrame) -> int:
    """Count saved sessions as rows where ``trial_index`` is 0."""
    if export_df.empty or "trial_index" not in export_df.columns:
        return 0
    return int(pd.to_numeric(export_df["trial_index"], errors="coerce").eq(0).sum())


def scan_assignments() -> pd.DataFrame:
    """Return valid assignment rows for this study iteration.

    Columns are ``user_id``, ``party``, and ``created_at`` as datetimes.
    """
    table = boto3.resource("dynamodb", region_name=AWS_REGION).Table(
        USER_ASSIGNMENTS_TABLE
    )
    items: list[dict[str, Any]] = []
    kwargs: dict[str, Any] = {}
    while True:
        response = table.scan(**kwargs)
        items.extend(response.get("Items", []))
        last_key = response.get("LastEvaluatedKey")
        if not last_key:
            break
        kwargs["ExclusiveStartKey"] = last_key

    rows: list[dict[str, Any]] = []
    for item in items:
        if item.get("study_id") != STUDY_ID:
            continue
        if item.get("study_iteration_id") != STUDY_ITERATION_ID:
            continue
        user_id = str(item.get("user_id") or "").strip()
        if not is_valid_user_id(user_id):
            continue
        payload_raw = item.get("payload") or "{}"
        payload = json.loads(payload_raw) if isinstance(payload_raw, str) else payload_raw
        metadata_raw = payload.get("metadata") or "{}"
        metadata = (
            json.loads(metadata_raw) if isinstance(metadata_raw, str) else metadata_raw
        )
        party = str(metadata.get("political_party") or "").strip().lower()
        if party not in PARTY_ORDER:
            continue
        created_at = _parse_created_at(item.get("created_at"))
        if created_at is None:
            continue
        rows.append(
            {
                "user_id": user_id,
                "party": party,
                "created_at": created_at,
            }
        )
    return pd.DataFrame(rows, columns=["user_id", "party", "created_at"])


def _parse_created_at(value: object) -> datetime | None:
    try:
        return datetime.strptime(str(value), TIMESTAMP_FORMAT)
    except ValueError:
        return None
