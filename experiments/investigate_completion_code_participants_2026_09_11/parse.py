"""Parse DynamoDB assignment payloads and precomputed assignment id lists."""

from __future__ import annotations

import json
from typing import Any


def parse_assignment_payload(payload: str) -> dict[str, str | None]:
    """Return assignment_id, s3_key, political_party, and condition from a payload string.

    Parameters
    ----------
    payload
        JSON object stored on the DynamoDB ``payload`` attribute. ``metadata``
        may itself be a JSON string.

    Raises
    ------
    ValueError
        When ``payload`` is not a JSON object.
    """
    parsed = json.loads(payload)
    if not isinstance(parsed, dict):
        raise ValueError("payload must be a JSON object")
    metadata = _parse_metadata(parsed.get("metadata"))
    assignment_id = parsed.get("assignment_id")
    s3_key = parsed.get("s3_key")
    return {
        "assignment_id": _optional_str(assignment_id),
        "s3_key": _optional_str(s3_key),
        "political_party": _optional_str(metadata.get("political_party")),
        "condition": _optional_str(metadata.get("condition")),
    }


def parse_post_ids(assigned_post_ids: str) -> list[str]:
    """Parse a JSON list of post ids.

    Raises
    ------
    ValueError
        When the value is not a JSON list of strings.
    """
    parsed = json.loads(assigned_post_ids)
    if not isinstance(parsed, list):
        raise ValueError("assigned_post_ids must be a JSON list")
    return [str(post_id) for post_id in parsed]


def posts_match_assignment(
    scored_post_ids: tuple[str, ...] | list[str],
    assigned_post_ids: tuple[str, ...] | list[str],
) -> bool:
    """Return True when scored ids equal the assigned list in order."""
    return list(scored_post_ids) == list(assigned_post_ids)


def _parse_metadata(metadata: Any) -> dict[str, Any]:
    if metadata is None:
        return {}
    if isinstance(metadata, dict):
        return metadata
    if isinstance(metadata, str):
        parsed = json.loads(metadata)
        if not isinstance(parsed, dict):
            raise ValueError("payload metadata must be a JSON object")
        return parsed
    raise ValueError("payload metadata must be a JSON object or JSON string")


def _optional_str(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None
