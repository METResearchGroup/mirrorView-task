"""Check the Reddit preprocessed S3 inventory against the bucket.

Run from the repo root:

    export AWS_ACCESS_KEY_ID="$LAB_AWS_ACCESS_KEY_ID"
    export AWS_SECRET_ACCESS_KEY="$LAB_AWS_ACCESS_KEY_SECRET"
    PYTHONPATH=. uv run python data_platform/scripts/verify_reddit_preprocessed_s3.py
"""

from __future__ import annotations

from data_platform.scripts.migrate_reddit_preprocessed_to_s3 import (
    BUCKET,
    EXPECTED_OBJECT_COUNT,
    INVENTORY_PATH,
    PREPROCESSED_RUN,
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
    inventory = {"bucket": BUCKET, "region": REGION, "objects": []}
    if inventory["bucket"] != BUCKET or inventory["region"] != REGION:
        raise SystemExit(1)
    if inventory.get("preprocessed_run") not in {None, PREPROCESSED_RUN}:
        raise SystemExit(1)
    problems = verify_inventory(inventory, S3(BUCKET, region_name=REGION))
    print(problems)
    print(INVENTORY_PATH)
    print(EXPECTED_OBJECT_COUNT)
    print(sha256_hex)


if __name__ == "__main__":
    main()
