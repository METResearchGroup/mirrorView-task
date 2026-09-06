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
    """Return the single lifecycle rule committed in ``data_platform_s3_lifecycle.json``.

    Raises
    ------
    ValueError
        If the file does not hold exactly one rule whose ``ID`` is ``RULE_ID``.
    """
    raise NotImplementedError


def read_rules(client: Any) -> list[dict]:
    """Return the bucket's current lifecycle rules, or ``[]`` when it has no configuration.

    Only ``NoSuchLifecycleConfiguration`` is treated as "no rules"; any other
    ``ClientError`` propagates.
    """
    raise NotImplementedError


def merge_rule(existing: list[dict], rule: dict) -> list[dict]:
    """Return ``existing`` with ``rule`` replacing the rule that shares its ``ID``.

    Rules with other ids are kept unchanged and in order. When no rule shares
    the id, ``rule`` is appended. ``existing`` is not modified, so rerunning
    the apply never adds a duplicate.
    """
    raise NotImplementedError


def main() -> None:
    client = boto3.client("s3", region_name=REGION)
    rule = load_rule()
    existing = read_rules(client)
    merged = merge_rule(existing, rule)
    raise NotImplementedError(merged)


if __name__ == "__main__":
    main()
