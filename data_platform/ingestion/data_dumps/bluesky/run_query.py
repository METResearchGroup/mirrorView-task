"""Download Bluesky Jetstream posts for one UTC day via Athena.

Run from the repo root:

    PYTHONPATH=. uv run python data_platform/ingestion/data_dumps/bluesky/run_query.py
"""

from __future__ import annotations

from pathlib import Path
from urllib.parse import urlparse

import boto3

from data_platform.ingestion.data_dumps.bluesky.athena import Athena, DEFAULT_REGION
from data_platform.ingestion.data_dumps.bluesky.queries import (
    ATHENA_WORKGROUP,
    GLUE_DATABASE,
    posts_for_utc_day_sql,
)

RAW_OUTPUT_PATH = Path(__file__).resolve().parent / "data" / "raw" / "posts.csv"
S3_URI_SCHEME = "s3"


def main() -> int:
    """Run the posts SELECT and download the Athena result CSV.

    Returns
    -------
    int
        Process exit code; ``0`` on success.
    """
    query = posts_for_utc_day_sql()
    athena = Athena(region=DEFAULT_REGION)
    execution_id = athena.run_query(
        query,
        database=GLUE_DATABASE,
        workgroup=ATHENA_WORKGROUP,
    )
    output_location = athena.get_output_location(execution_id)
    bucket, key = _parse_s3_uri(output_location)
    _download_s3_object(bucket, key, RAW_OUTPUT_PATH, region=DEFAULT_REGION)
    print(RAW_OUTPUT_PATH)
    return 0


def _parse_s3_uri(s3_uri: str) -> tuple[str, str]:
    parsed = urlparse(s3_uri)
    if parsed.scheme != S3_URI_SCHEME or not parsed.netloc:
        raise ValueError(f"Expected s3 URI, got {s3_uri!r}")
    key = parsed.path.lstrip("/")
    return parsed.netloc, key


def _download_s3_object(
    bucket: str,
    key: str,
    destination: Path,
    region: str,
) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    s3_client = boto3.client("s3", region_name=region)
    s3_client.download_file(bucket, key, str(destination))


if __name__ == "__main__":
    raise SystemExit(main())
