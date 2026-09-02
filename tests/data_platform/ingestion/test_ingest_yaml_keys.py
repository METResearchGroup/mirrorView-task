from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

INGEST_CONFIGS_DIR = (
    Path(__file__).resolve().parents[3] / "data_platform" / "ingestion" / "configs"
)
UNREAD_INGEST_YAML_KEYS = frozenset(
    {"query_batch_size", "dedupe_comments_from_prior_raw_runs"}
)
LEGACY_PRIOR_RUN_TOKEN = "prior_runs_all_datasets"


def _ingest_yaml_paths() -> list[Path]:
    return sorted(INGEST_CONFIGS_DIR.rglob("*.yaml"))


def _load_yaml_mapping(path: Path) -> dict[str, Any]:
    loaded = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(loaded, dict):
        raise AssertionError(f"{path} root must be a mapping")
    return loaded


def _collect_keys_and_strings(value: Any) -> tuple[set[str], set[str]]:
    keys: set[str] = set()
    strings: set[str] = set()
    if isinstance(value, dict):
        for key, child in value.items():
            if isinstance(key, str):
                keys.add(key)
            child_keys, child_strings = _collect_keys_and_strings(child)
            keys |= child_keys
            strings |= child_strings
    elif isinstance(value, list):
        for child in value:
            child_keys, child_strings = _collect_keys_and_strings(child)
            keys |= child_keys
            strings |= child_strings
    elif isinstance(value, str):
        strings.add(value)
    return keys, strings


class TestIngestYamlKeys:
    """Tests that ingest YAML does not list keys the sync CLIs never read."""

    def test_unread_keys_are_absent(self) -> None:
        found: list[str] = []
        for path in _ingest_yaml_paths():
            keys, _strings = _collect_keys_and_strings(_load_yaml_mapping(path))
            for key in sorted(keys & UNREAD_INGEST_YAML_KEYS):
                found.append(f"{path}: {key}")
        expected: list[str] = []
        assert found == expected

    def test_prior_run_token_is_canonical(self) -> None:
        found: list[str] = []
        for path in _ingest_yaml_paths():
            _keys, strings = _collect_keys_and_strings(_load_yaml_mapping(path))
            if LEGACY_PRIOR_RUN_TOKEN in strings:
                found.append(str(path))
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
