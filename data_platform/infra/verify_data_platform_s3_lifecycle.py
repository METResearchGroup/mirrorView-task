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
    """Return the rule whose ``ID`` is ``rule_id``, or ``None`` when absent."""
    return next((rule for rule in rules if rule.get("ID") == rule_id), None)


def rule_problems(installed: dict, expected: dict) -> list[str]:
    """Compare status, AND prefix, AND tags, and expiration days of two lifecycle rules.

    Returns
    -------
    list[str]
        One message per field that differs. Empty when ``installed`` matches
        ``expected`` on every compared field.
    """
    installed_and = installed.get("Filter", {}).get("And", {})
    expected_and = expected["Filter"]["And"]
    compared = [
        ("status", installed.get("Status"), expected["Status"]),
        ("prefix", installed_and.get("Prefix"), expected_and["Prefix"]),
        ("tags", _tag_pairs(installed_and.get("Tags", [])), _tag_pairs(expected_and["Tags"])),
        ("expiration_days", installed.get("Expiration", {}).get("Days"), expected["Expiration"]["Days"]),
    ]
    return [f"{name} is {found!r}, expected {wanted!r}" for name, found, wanted in compared if found != wanted]


def _tag_pairs(tags: list[dict]) -> list[tuple[str, str]]:
    return sorted((tag["Key"], tag["Value"]) for tag in tags)


def main() -> None:
    client = boto3.client("s3", region_name=REGION)
    expected = load_rule()
    installed = find_rule(read_rules(client), RULE_ID)
    raise NotImplementedError((BUCKET, expected, installed, rule_problems))


if __name__ == "__main__":
    main()
