"""Check the Twitter preprocessed S3 inventory against the bucket.

Run from the repo root:

    export AWS_ACCESS_KEY_ID="$LAB_AWS_ACCESS_KEY_ID"
    export AWS_SECRET_ACCESS_KEY="$LAB_AWS_ACCESS_KEY_SECRET"
    PYTHONPATH=. uv run python data_platform/scripts/verify_twitter_preprocessed_s3.py
"""

from __future__ import annotations

from lib.aws.s3 import S3

from data_platform.scripts.migrate_twitter_preprocessed_to_s3 import (
    BUCKET,
    EXPECTED_OBJECT_COUNT,
    INVENTORY_PATH,
    REGION,
)


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
    """Load the inventory, confirm bucket and count, and print OK or FAIL."""
    raise NotImplementedError


if __name__ == "__main__":
    main()
