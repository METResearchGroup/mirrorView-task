from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from data_platform.utils.deduplication import PRIOR_RUN_POLICY

INGEST_CONFIGS_DIR = (
    Path(__file__).resolve().parents[3] / "data_platform" / "ingestion" / "configs"
)
UNREAD_INGEST_YAML_KEYS = frozenset(
    {"query_batch_size", "dedupe_comments_from_prior_raw_runs"}
)
ALLOWED_DEDUPE_POLICY_TOKENS = frozenset({"current_run", PRIOR_RUN_POLICY})
DEDUPE_POLICY_KEYS = frozenset(
    {"dedupe_policy", "comments_dedupe_policy", "posts_dedupe_policy"}
)


def _ingest_yaml_paths() -> list[Path]:
    return sorted(INGEST_CONFIGS_DIR.rglob("*.yaml"))


def _load_yaml_mapping(path: Path) -> dict[str, Any]:
    loaded = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(loaded, dict):
        raise AssertionError(f"{path} root must be a mapping")
    return loaded


def _collect_keys(value: Any) -> set[str]:
    keys: set[str] = set()
    if isinstance(value, dict):
        for key, child in value.items():
            if isinstance(key, str):
                keys.add(key)
            keys |= _collect_keys(child)
    elif isinstance(value, list):
        for child in value:
            keys |= _collect_keys(child)
    return keys


class TestIngestYamlKeys:
    """Tests that ingest YAML does not list keys the sync CLIs never read."""

    def test_unread_keys_are_absent(self) -> None:
        found: list[str] = []
        for path in _ingest_yaml_paths():
            keys = _collect_keys(_load_yaml_mapping(path))
            for key in sorted(keys & UNREAD_INGEST_YAML_KEYS):
                found.append(f"{path}: {key}")
        expected: list[str] = []
        assert found == expected

    def test_dedupe_policy_tokens_are_known(self) -> None:
        found: list[str] = []
        for path in _ingest_yaml_paths():
            loaded = _load_yaml_mapping(path)
            params = loaded.get("ingestion_params")
            if not isinstance(params, dict):
                continue
            for key in DEDUPE_POLICY_KEYS:
                raw_policy = params.get(key)
                if raw_policy is None:
                    continue
                if not isinstance(raw_policy, list):
                    found.append(f"{path}: {key} is not a list")
                    continue
                unknown = [
                    token
                    for token in raw_policy
                    if token not in ALLOWED_DEDUPE_POLICY_TOKENS
                ]
                if unknown:
                    found.append(f"{path}: {key}={unknown}")
        expected: list[str] = []
        assert found == expected

    def test_params_live_under_ingestion_params(self) -> None:
        found: list[str] = []
        for path in _ingest_yaml_paths():
            loaded = _load_yaml_mapping(path)
            if "fetch" in loaded:
                found.append(str(path))
        expected: list[str] = []
        assert found == expected
