"""Check the Reddit preprocessed S3 inventory against the bucket.

Run from the repo root:

    export AWS_ACCESS_KEY_ID="$LAB_AWS_ACCESS_KEY_ID"
    export AWS_SECRET_ACCESS_KEY="$LAB_AWS_ACCESS_KEY_SECRET"
    PYTHONPATH=. uv run python data_platform/scripts/verify_reddit_preprocessed_s3.py
"""

from __future__ import annotations

import json

from botocore.exceptions import ClientError

from data_platform.scripts.migrate_reddit_preprocessed_to_s3 import (
    BUCKET,
    EXPECTED_OBJECT_COUNT,
    INVENTORY_PATH,
    PREPROCESSED_RUN,
    REGION,
    sha256_hex,
)
from lib.aws.s3 import S3


def _check_inventory_row(row: dict, s3: S3) -> list[str]:
    """Re-download one inventory row and report length or SHA-256 mismatches."""
    key = row["s3_key"]
    try:
        remote = s3.get_bytes(key)
    except ClientError as exc:
        return [f"missing {key}: {exc.response['Error']['Code']}"]
    problems: list[str] = []
    if len(remote) != row["bytes"]:
        problems.append(f"length mismatch {key}: {len(remote)} != {row['bytes']}")
    remote_sha256 = sha256_hex(remote)
    if remote_sha256 != row["sha256"]:
        problems.append(f"sha256 mismatch {key}: {remote_sha256} != {row['sha256']}")
    return problems


def verify_inventory(inventory: dict, s3: S3) -> list[str]:
    """Re-download every inventory object and report length or SHA-256 mismatches.

    Returns
    -------
    list[str]
        One message per missing or mismatched object. Empty when every object
        matches.
    """
    problems: list[str] = []
    for row in inventory["objects"]:
        problems.extend(_check_inventory_row(row, s3))
    return problems


def _fail_if_wrong_bucket(inventory: dict) -> None:
    """Exit when the inventory bucket or region does not match the locked values."""
    if inventory["bucket"] != BUCKET or inventory["region"] != REGION:
        print(
            f"FAIL: inventory targets {inventory['bucket']} in {inventory['region']}, "
            f"expected {BUCKET} in {REGION}"
        )
        raise SystemExit(1)


def _fail_if_wrong_run_or_count(inventory: dict) -> None:
    """Exit when preprocessed_run or object_count does not match the locked values."""
    if inventory.get("preprocessed_run") != PREPROCESSED_RUN:
        print(
            f"FAIL: inventory preprocessed_run is {inventory.get('preprocessed_run')!r}, "
            f"expected {PREPROCESSED_RUN!r}"
        )
        raise SystemExit(1)
    objects = inventory["objects"]
    if inventory["object_count"] != EXPECTED_OBJECT_COUNT or len(objects) != EXPECTED_OBJECT_COUNT:
        print(
            f"FAIL: inventory lists {inventory['object_count']} objects with "
            f"{len(objects)} rows, expected {EXPECTED_OBJECT_COUNT}"
        )
        raise SystemExit(1)


def main() -> None:
    inventory = json.loads(INVENTORY_PATH.read_text())
    _fail_if_wrong_bucket(inventory)
    _fail_if_wrong_run_or_count(inventory)
    objects = inventory["objects"]
    problems = verify_inventory(inventory, S3(BUCKET, region_name=REGION))
    if problems:
        for problem in problems:
            print(problem)
        print(f"FAIL: {len(problems)} of {len(objects)} objects did not match")
        raise SystemExit(1)
    print(f"OK: {len(objects)}/{EXPECTED_OBJECT_COUNT} objects present with matching sha256")


if __name__ == "__main__":
    main()
