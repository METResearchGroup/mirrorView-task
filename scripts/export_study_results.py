"""Export mirror view pilot data from S3 into a single filtered CSV.

Only objects named ``data_<epoch_ms>.csv`` or ``data_<epoch_ms>_<uuid>.csv`` (lambda upload time) at or after
``--since-date`` (UTC midnight) are listed and merged. To run:

    - PYTHONPATH=. uv run python scripts/export_study_results.py           # skip existing files
    - PYTHONPATH=. uv run python scripts/export_study_results.py --force-download  # full re-fetch
"""

from __future__ import annotations

import argparse
from datetime import UTC, date, datetime
from pathlib import Path
import re

import boto3
import pandas as pd

from lib.timestamp_utils import get_current_timestamp


BUCKET_NAME = "jspsych-mirror-view-4"
S3_PREFIX = "data/prolific/"
EXPECTED_FILE_COUNT = 190
DATA_CSV_FILENAME_PATTERN = re.compile(
    r"^data_(\d+)(?:_[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12})?\.csv$"
)
MANUAL_TEST_PATTERN = re.compile(r"^manual-test-.*$")
INVALID_PROLIFIC_SUBSTRINGS = ("pid", "manual-test", "dev")
DEFAULT_SINCE_DATE = date(2026, 4, 20)

SCRIPT_DIR = Path(__file__).resolve().parent
TEMP_DIR = SCRIPT_DIR / "temp"
OUTPUT_CSV = SCRIPT_DIR / f"mirrorview_pilot_data_{get_current_timestamp()}.csv"


def utc_midnight_ms(d: date) -> int:
    """Return epoch milliseconds at UTC midnight on ``d``."""
    dt = datetime(d.year, d.month, d.day, tzinfo=UTC)
    return int(dt.timestamp() * 1000)


def list_csv_keys(s3_client: boto3.client, *, min_file_epoch_ms: int) -> list[str]:
    """Return CSV object keys under the prefix that match ``data_<ms>.csv`` or ``data_<ms>_<uuid>.csv`` with ``ms >= min_file_epoch_ms``."""
    paginator = s3_client.get_paginator("list_objects_v2")
    csv_keys: list[str] = []
    skipped_non_matching = 0
    skipped_before_cutoff = 0

    for page in paginator.paginate(Bucket=BUCKET_NAME, Prefix=S3_PREFIX):
        for item in page.get("Contents", []):
            key = item["Key"]
            if not key.endswith(".csv"):
                continue
            basename = Path(key).name
            match = DATA_CSV_FILENAME_PATTERN.match(basename)
            if not match:
                skipped_non_matching += 1
                continue
            file_ms = int(match.group(1))
            if file_ms < min_file_epoch_ms:
                skipped_before_cutoff += 1
                continue
            csv_keys.append(key)

    csv_keys.sort()
    print(
        f"S3 key filter: kept {len(csv_keys)} key(s); skipped {skipped_before_cutoff} before cutoff "
        f"and {skipped_non_matching} non-matching basename(s) under {S3_PREFIX!r}"
    )
    return csv_keys


def download_csvs(
    s3_client: boto3.client, csv_keys: list[str], *, force_redownload: bool = False
) -> list[Path]:
    """Download CSV files into scripts/temp and return one local path per S3 key (same order).

    By default, skips download when the target file already exists under ``temp/``.
    Pass ``force_redownload=True`` (CLI: ``--force-download``) to always fetch from S3.
    """
    TEMP_DIR.mkdir(parents=True, exist_ok=True)
    local_paths: list[Path] = []
    seen_names: set[str] = set()
    downloaded = 0
    skipped = 0

    for key in csv_keys:
        file_name = Path(key).name
        if file_name in seen_names:
            raise RuntimeError(f"Duplicate CSV filename encountered in S3: {file_name}")
        seen_names.add(file_name)

        local_path = TEMP_DIR / file_name
        if not force_redownload and local_path.is_file():
            print(f"Skipping (already present): {local_path}")
            skipped += 1
        else:
            print(f"Downloading s3://{BUCKET_NAME}/{key} -> {local_path}")
            s3_client.download_file(BUCKET_NAME, key, str(local_path))
            downloaded += 1
        local_paths.append(local_path)

    print(
        f"S3 CSV sync: {downloaded} downloaded, {skipped} skipped (already in {TEMP_DIR})"
    )
    return local_paths


def validate_loaded_csv(frame: pd.DataFrame) -> bool:
    """Return True if this user's CSV should be included in the export.

    Rows with ``prolific_id`` containing any of these substrings (case-insensitive)
    are invalid: ``pid`` (placeholder IDs), ``manual-test``, ``dev``. If any row
    in a file matches, the whole file is excluded.
    """
    if "prolific_id" not in frame.columns:
        raise KeyError("Expected 'prolific_id' column in CSV data")
    prolific_ids = frame["prolific_id"].fillna("").astype(str).str.lower()
    for sub in INVALID_PROLIFIC_SUBSTRINGS:
        if prolific_ids.str.contains(sub.lower(), regex=False).any():
            return False
    return True


def load_downloaded_csvs(local_paths: list[Path]) -> pd.DataFrame:
    """Read downloaded CSVs, drop users with invalid prolific_id values, and concat."""
    filtered_frames: list[pd.DataFrame] = []
    excluded_user_files = 0
    excluded_rows = 0

    for path in local_paths:
        frame = pd.read_csv(path)
        if validate_loaded_csv(frame):
            filtered_frames.append(frame)
        else:
            excluded_user_files += 1
            excluded_rows += len(frame)

    total_files = len(local_paths)
    included_files = len(filtered_frames)
    bad = ", ".join(repr(s) for s in INVALID_PROLIFIC_SUBSTRINGS)
    print(
        f"Excluded {excluded_user_files} user CSV file(s) ({excluded_rows} rows) whose "
        f"prolific_id contained any of [{bad}] ({included_files}/{total_files} files kept)"
    )

    if not filtered_frames:
        # Keep the output shape stable so downstream filtering can run even when
        # no CSVs survive the "valid prolific_id" filter.
        return pd.DataFrame(columns=["prolific_id"])
    return pd.concat(filtered_frames, ignore_index=True)


def filter_manual_test_rows(dataframe: pd.DataFrame) -> pd.DataFrame:
    """Drop rows whose prolific_id looks like a manual test record."""
    if "prolific_id" not in dataframe.columns:
        raise KeyError("Expected 'prolific_id' column in combined CSV data")

    prolific_ids = dataframe["prolific_id"].fillna("").astype(str)
    return dataframe.loc[~prolific_ids.str.match(MANUAL_TEST_PATTERN)].copy()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--force-download",
        action="store_true",
        help="Re-download every CSV from S3 even when the file already exists in temp.",
    )
    parser.add_argument(
        "--since-date",
        type=date.fromisoformat,
        default=DEFAULT_SINCE_DATE,
        metavar="YYYY-MM-DD",
        help=(
            "Only include objects named data_<ms>.csv or data_<ms>_<uuid>.csv where ms is at or after UTC midnight on "
            f"this date (ISO). Default: {DEFAULT_SINCE_DATE.isoformat()}."
        ),
    )
    args = parser.parse_args()

    min_file_epoch_ms = utc_midnight_ms(args.since_date)
    s3_client = boto3.client("s3")

    csv_keys = list_csv_keys(s3_client, min_file_epoch_ms=min_file_epoch_ms)
    print(
        f"Found {len(csv_keys)} CSV file(s) to export (>= {args.since_date.isoformat()} UTC by filename) "
        f"in s3://{BUCKET_NAME}/{S3_PREFIX}"
    )
    # if len(csv_keys) != EXPECTED_FILE_COUNT:
    #     raise RuntimeError(
    #         f"Expected {EXPECTED_FILE_COUNT} CSV files, found {len(csv_keys)}"
    #     )

    local_paths = download_csvs(
        s3_client, csv_keys, force_redownload=args.force_download
    )
    print(f"Using {len(local_paths)} CSV file path(s) from S3 listing under {TEMP_DIR}")

    all_csvs = load_downloaded_csvs(local_paths)
    print(f"Combined dataframe has {len(all_csvs)} rows before filtering")

    filtered = filter_manual_test_rows(all_csvs)
    removed_rows = len(all_csvs) - len(filtered)
    print(f"Removed {removed_rows} manual test rows. Total remaining rows: {len(filtered)}")

    filtered.to_csv(OUTPUT_CSV, index=False)
    print(f"Wrote filtered export to {OUTPUT_CSV}")


if __name__ == "__main__":
    main()
