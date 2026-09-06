"""Install the 30-day expiration rule for tagged data platform intermediate batches.

Run from the repo root:

    export AWS_ACCESS_KEY_ID="$LAB_AWS_ACCESS_KEY_ID"
    export AWS_SECRET_ACCESS_KEY="$LAB_AWS_ACCESS_KEY_SECRET"
    PYTHONPATH=. uv run python data_platform/infra/apply_data_platform_s3_lifecycle.py
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import boto3

BUCKET = "mirrorview-experimental-artifacts"
REGION = "us-east-2"
RULE_ID = "expire-data-platform-intermediate-artifacts"
LIFECYCLE_PATH = Path(__file__).with_name("data_platform_s3_lifecycle.json")


def load_rule() -> dict:
    raise NotImplementedError


def read_rules(client: Any) -> list[dict]:
    raise NotImplementedError


def merge_rule(existing: list[dict], rule: dict) -> list[dict]:
    raise NotImplementedError


def main() -> None:
    client = boto3.client("s3", region_name=REGION)
    rule = load_rule()
    existing = read_rules(client)
    merged = merge_rule(existing, rule)
    raise NotImplementedError(merged)


if __name__ == "__main__":
    main()
