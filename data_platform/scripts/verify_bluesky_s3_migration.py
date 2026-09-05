"""Check every object in the Bluesky S3 migration inventory against the bucket.

Run from the repo root:

    export AWS_ACCESS_KEY_ID="$LAB_AWS_ACCESS_KEY_ID"
    export AWS_SECRET_ACCESS_KEY="$LAB_AWS_ACCESS_KEY_SECRET"
    PYTHONPATH=. uv run python data_platform/scripts/verify_bluesky_s3_migration.py
"""

from __future__ import annotations

from lib.aws.s3 import S3


def verify_inventory(inventory: dict, s3: S3) -> list[str]:
    raise NotImplementedError


def main() -> None:
    problems = verify_inventory({}, S3(""))
    raise SystemExit(1 if problems else 0)


if __name__ == "__main__":
    main()
