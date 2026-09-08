"""Check a Twitter preprocessed S3 inventory against the bucket.

Run from the repo root:

    export AWS_ACCESS_KEY_ID="$LAB_AWS_ACCESS_KEY_ID"
    export AWS_SECRET_ACCESS_KEY="$LAB_AWS_ACCESS_KEY_SECRET"
    PYTHONPATH=. uv run python data_platform/scripts/verify_twitter_preprocessed_s3.py \\
        --dataset-id twitter_5901767a-e609-46fc-9a17-742516b548f2 \\
        --preprocessed-run 2026_09_08-01:48:08
"""

from __future__ import annotations

import json
import sys
from collections.abc import Sequence

from botocore.exceptions import ClientError

from data_platform.scripts.migrate_twitter_preprocessed_to_s3 import (
    BUCKET,
    EXPECTED_OBJECT_COUNT,
    REGION,
    inventory_path_for,
    parse_args,
    sha256_hex,
)
from lib.aws.s3 import S3

VERIFY_DESCRIPTION = "Check a Twitter preprocessed S3 inventory against the bucket."


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
        key = row["s3_key"]
        try:
            remote = s3.get_bytes(key)
        except ClientError as exc:
            problems.append(f"missing {key}: {exc.response['Error']['Code']}")
            continue
        if len(remote) != row["bytes"]:
            problems.append(f"length mismatch {key}: {len(remote)} != {row['bytes']}")
        remote_sha256 = sha256_hex(remote)
        if remote_sha256 != row["sha256"]:
            problems.append(f"sha256 mismatch {key}: {remote_sha256} != {row['sha256']}")
    return problems


def fail_if_inventory_header_invalid(inventory: dict, preprocessed_run: str) -> None:
    """Exit 1 when bucket, region, run, or object count do not match the contract."""
    if inventory["bucket"] != BUCKET or inventory["region"] != REGION:
        print(
            f"FAIL: inventory targets {inventory['bucket']} in {inventory['region']}, "
            f"expected {BUCKET} in {REGION}"
        )
        raise SystemExit(1)
    if inventory.get("preprocessed_run") != preprocessed_run:
        print(
            f"FAIL: inventory preprocessed_run {inventory.get('preprocessed_run')!r}, "
            f"expected {preprocessed_run!r}"
        )
        raise SystemExit(1)
    objects = inventory["objects"]
    if inventory["object_count"] != EXPECTED_OBJECT_COUNT or len(objects) != EXPECTED_OBJECT_COUNT:
        print(
            f"FAIL: inventory lists {inventory['object_count']} objects with "
            f"{len(objects)} rows, expected {EXPECTED_OBJECT_COUNT}"
        )
        raise SystemExit(1)


def main(argv: Sequence[str]) -> None:
    """Load the inventory, confirm bucket and count, and print OK or FAIL."""
    args = parse_args(argv, VERIFY_DESCRIPTION)
    inventory = json.loads(inventory_path_for(args.dataset_id).read_text())
    fail_if_inventory_header_invalid(inventory, args.preprocessed_run)
    objects = inventory["objects"]
    problems = verify_inventory(inventory, S3(BUCKET, region_name=REGION))
    if problems:
        for problem in problems:
            print(problem)
        print(f"FAIL: {len(problems)} of {len(objects)} objects did not match")
        raise SystemExit(1)
    print(f"OK: {len(objects)}/{EXPECTED_OBJECT_COUNT} objects present with matching sha256")


if __name__ == "__main__":
    main(sys.argv[1:])
