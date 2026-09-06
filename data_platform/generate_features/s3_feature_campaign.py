"""S3 layout and small mutable files of one feature in an LLM labeling campaign.

Owns the per-feature prefix, the boto3 calls the campaign needs (conditional
put, conditional replace, get with ETag, delete, list, tags), and the read,
append, and conditional replace pattern behind ``manifest.json``,
``progress.jsonl``, ``errors.jsonl``, and ``active_openai_batch.json``.
"""

from __future__ import annotations


def run_id_for_feature():
    raise NotImplementedError


def feature_prefix():
    raise NotImplementedError


class FeaturePaths:
    """Bucket and per-feature prefix of one campaign feature."""


class CampaignObjectStore:
    """The few S3 operations a campaign feature writer needs."""


def new_manifest():
    raise NotImplementedError


def load_manifest():
    raise NotImplementedError


def save_manifest():
    raise NotImplementedError


def load_active_state():
    raise NotImplementedError


def save_active_state():
    raise NotImplementedError


def delete_active_state():
    raise NotImplementedError


def append_progress():
    raise NotImplementedError


def append_errors():
    raise NotImplementedError


class ActiveStateMirror:
    """Keeps the engine's local ``active_openai_batch.json`` and its S3 copy in step."""
