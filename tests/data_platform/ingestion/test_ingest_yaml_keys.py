from __future__ import annotations

from pathlib import Path

import yaml

INGEST_CONFIGS_DIR = Path("data_platform/ingestion/configs")
UNREAD_INGEST_YAML_KEYS = frozenset(
    {"query_batch_size", "dedupe_comments_from_prior_raw_runs"}
)
LEGACY_PRIOR_RUN_TOKEN = "prior_runs_all_datasets"


def _ingest_yaml_paths() -> list[Path]:
    return sorted(INGEST_CONFIGS_DIR.rglob("*.yaml"))


def _load_yaml_mapping(path: Path) -> dict:
    loaded = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(loaded, dict):
        raise AssertionError(f"{path} root must be a mapping")
    return loaded


class TestIngestYamlKeys:
    """Tests that ingest YAML only advertises keys the sync CLIs read."""

    def test_unread_keys_are_absent(self) -> None:
        found: list[str] = []
        for path in _ingest_yaml_paths():
            text = path.read_text(encoding="utf-8")
            for key in UNREAD_INGEST_YAML_KEYS:
                if key in text:
                    found.append(f"{path}: {key}")
        expected: list[str] = []
        assert found == expected

    def test_prior_run_token_is_canonical(self) -> None:
        found: list[str] = []
        for path in _ingest_yaml_paths():
            if LEGACY_PRIOR_RUN_TOKEN in path.read_text(encoding="utf-8"):
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
