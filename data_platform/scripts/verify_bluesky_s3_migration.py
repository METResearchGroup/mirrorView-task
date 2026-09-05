"""Check every object in the Bluesky S3 migration inventory against the bucket.

Run from the repo root:

    export AWS_ACCESS_KEY_ID="$LAB_AWS_ACCESS_KEY_ID"
    export AWS_SECRET_ACCESS_KEY="$LAB_AWS_ACCESS_KEY_SECRET"
    PYTHONPATH=. uv run python data_platform/scripts/verify_bluesky_s3_migration.py
"""

from __future__ import annotations

import json

from data_platform.scripts.migrate_bluesky_lfs_to_s3 import (
    BUCKET,
    EXPECTED_OBJECT_COUNT,
    INVENTORY_PATH,
    REGION,
    sha256_hex,
)
from lib.aws.s3 import S3


def verify_inventory(inventory: dict, s3: S3) -> list[str]:
    """Re-download every inventory object and report length or SHA-256 mismatches.

    Returns
    -------
    list[str]
        One message per missing or mismatched object. Empty when every object
        matches.
    """
    raise NotImplementedError


def main() -> None:
    inventory = json.loads(INVENTORY_PATH.read_text())
    problems = verify_inventory(inventory, S3(BUCKET, region_name=REGION))
    raise SystemExit(1 if problems else 0)


if __name__ == "__main__":
    main()
