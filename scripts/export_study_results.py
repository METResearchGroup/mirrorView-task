"""Export mirror view pilot data from S3 into a single filtered CSV."""

from __future__ import annotations

from pathlib import Path
import re

import boto3
import pandas as pd


BUCKET_NAME = "jspsych-mirror-view-3"
S3_PREFIX = "data/prolific/"
EXPECTED_FILE_COUNT = 190
MANUAL_TEST_PATTERN = re.compile(r"^manual-test-.*$")

SCRIPT_DIR = Path(__file__).resolve().parent
TEMP_DIR = SCRIPT_DIR / "temp"
OUTPUT_CSV = SCRIPT_DIR / "mirrorview_pilot_data_2026-04-15.csv"


def list_csv_keys(s3_client: boto3.client) -> list[str]:
    """Return all CSV object keys under the configured prefix."""
    paginator = s3_client.get_paginator("list_objects_v2")
    csv_keys: list[str] = []

    for page in paginator.paginate(Bucket=BUCKET_NAME, Prefix=S3_PREFIX):
        for item in page.get("Contents", []):
            key = item["Key"]
            if key.endswith(".csv"):
                csv_keys.append(key)

    csv_keys.sort()
    return csv_keys


def download_csvs(s3_client: boto3.client, csv_keys: list[str]) -> list[Path]:
    """Download CSV files into scripts/temp and return their local paths."""
    TEMP_DIR.mkdir(parents=True, exist_ok=True)
    local_paths: list[Path] = []
    seen_names: set[str] = set()

    for key in csv_keys:
        file_name = Path(key).name
        if file_name in seen_names:
            raise RuntimeError(f"Duplicate CSV filename encountered in S3: {file_name}")
        seen_names.add(file_name)

        local_path = TEMP_DIR / file_name
        print(f"Downloading s3://{BUCKET_NAME}/{key} -> {local_path}")
        s3_client.download_file(BUCKET_NAME, key, str(local_path))
        local_paths.append(local_path)

    return local_paths


def list_local_csvs() -> list[Path]:
    """Return the CSV files currently present in scripts/temp."""
    local_paths = sorted(path for path in TEMP_DIR.iterdir() if path.suffix == ".csv")
    # if len(local_paths) != EXPECTED_FILE_COUNT:
    #     raise RuntimeError(
    #         f"Expected {EXPECTED_FILE_COUNT} CSV files in {TEMP_DIR}, found {len(local_paths)}"
    #     )
    return local_paths


def load_downloaded_csvs(local_paths: list[Path]) -> pd.DataFrame:
    """Read all downloaded CSV files and concatenate them into one dataframe."""
    frames = [pd.read_csv(path) for path in local_paths]
    return pd.concat(frames, ignore_index=True)


def filter_manual_test_rows(dataframe: pd.DataFrame) -> pd.DataFrame:
    """Drop rows whose prolific_id looks like a manual test record."""
    if "prolific_id" not in dataframe.columns:
        raise KeyError("Expected 'prolific_id' column in combined CSV data")

    prolific_ids = dataframe["prolific_id"].fillna("").astype(str)
    return dataframe.loc[~prolific_ids.str.match(MANUAL_TEST_PATTERN)].copy()


def main() -> None:
    s3_client = boto3.client("s3")

    csv_keys = list_csv_keys(s3_client)
    print(f"Found {len(csv_keys)} CSV files in s3://{BUCKET_NAME}/{S3_PREFIX}")
    # if len(csv_keys) != EXPECTED_FILE_COUNT:
    #     raise RuntimeError(
    #         f"Expected {EXPECTED_FILE_COUNT} CSV files, found {len(csv_keys)}"
    #     )

    download_csvs(s3_client, csv_keys)
    local_paths = list_local_csvs()
    print(f"Downloaded {len(local_paths)} CSV files to {TEMP_DIR}")

    all_csvs = load_downloaded_csvs(local_paths)
    print(f"Combined dataframe has {len(all_csvs)} rows before filtering")

    filtered = filter_manual_test_rows(all_csvs)
    removed_rows = len(all_csvs) - len(filtered)
    print(f"Removed {removed_rows} manual test rows. Total remaining rows: {len(filtered)}")

    filtered.to_csv(OUTPUT_CSV, index=False)
    print(f"Wrote filtered export to {OUTPUT_CSV}")


if __name__ == "__main__":
    main()
