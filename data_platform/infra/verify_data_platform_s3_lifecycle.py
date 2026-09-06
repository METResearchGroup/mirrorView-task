"""Check that the bucket holds the 30-day expiration rule for tagged intermediate batches.

Run from the repo root:

    export AWS_ACCESS_KEY_ID="$LAB_AWS_ACCESS_KEY_ID"
    export AWS_SECRET_ACCESS_KEY="$LAB_AWS_ACCESS_KEY_SECRET"
    PYTHONPATH=. uv run python data_platform/infra/verify_data_platform_s3_lifecycle.py
"""

from __future__ import annotations

import boto3

from data_platform.infra.apply_data_platform_s3_lifecycle import (
    BUCKET,
    REGION,
    RULE_ID,
    load_rule,
    read_rules,
)


def find_rule(rules: list[dict], rule_id: str) -> dict | None:
    raise NotImplementedError


def rule_problems(installed: dict, expected: dict) -> list[str]:
    raise NotImplementedError


def main() -> None:
    client = boto3.client("s3", region_name=REGION)
    expected = load_rule()
    installed = find_rule(read_rules(client), RULE_ID)
    raise NotImplementedError((BUCKET, expected, installed, rule_problems))


if __name__ == "__main__":
    main()
