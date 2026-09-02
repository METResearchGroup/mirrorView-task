from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
import yaml

from data_platform.ingestion.sync_twitter import TWEETS_RECORD_TYPE
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


class TestTwitterIngestYamlRecordTypes:
    """Tests that Twitter ingest YAML lists the tweet record type."""

    def test_twitter_ingest_yaml_includes_tweets_record_type(self) -> None:
        twitter_dir = INGEST_CONFIGS_DIR / "twitter"
        missing: list[str] = []
        for path in sorted(twitter_dir.glob("*.yaml")):
            loaded = _load_yaml_mapping(path)
            record_types = loaded.get("record_types")
            if (
                not isinstance(record_types, list)
                or TWEETS_RECORD_TYPE not in record_types
            ):
                missing.append(str(path))
        expected: list[str] = []
        assert missing == expected


class TestBlueskyAuthorFilterYamlKey:
    """Tests that Bluesky ingest YAML uses author_filter, not handle."""

    def test_committed_bluesky_yaml_does_not_use_handle_key(self) -> None:
        found: list[str] = []
        for path in sorted((INGEST_CONFIGS_DIR / "bluesky").glob("*.yaml")):
            loaded = _load_yaml_mapping(path)
            params = loaded.get("ingestion_params")
            if isinstance(params, dict) and "handle" in params:
                found.append(str(path))
        expected: list[str] = []
        assert found == expected

    def test_default_bluesky_yaml_sets_author_filter(self) -> None:
        path = INGEST_CONFIGS_DIR / "bluesky" / "default.yaml"
        loaded = _load_yaml_mapping(path)
        params = loaded["ingestion_params"]
        result = params.get("author_filter")
        expected = "user.bsky.social"
        assert result == expected


class TestTwitterKeywordsYamlKey:
    """Tests that Twitter ingest YAML uses keywords, not keyword."""

    def test_committed_twitter_yaml_does_not_use_keyword_key(self) -> None:
        found: list[str] = []
        for path in sorted((INGEST_CONFIGS_DIR / "twitter").glob("*.yaml")):
            loaded = _load_yaml_mapping(path)
            params = loaded.get("ingestion_params")
            if isinstance(params, dict) and "keyword" in params:
                found.append(str(path))
        expected: list[str] = []
        assert found == expected

    def test_committed_twitter_yaml_sets_keywords_list(self) -> None:
        found: list[str] = []
        for path in sorted((INGEST_CONFIGS_DIR / "twitter").glob("*.yaml")):
            loaded = _load_yaml_mapping(path)
            params = loaded.get("ingestion_params")
            if not isinstance(params, dict):
                found.append(f"{path}: missing ingestion_params")
                continue
            keywords = params.get("keywords")
            if (
                not isinstance(keywords, list)
                or not keywords
                or not all(isinstance(item, str) and item.strip() for item in keywords)
            ):
                found.append(str(path))
        expected: list[str] = []
        assert found == expected

    def test_default_twitter_yaml_sets_keywords_example(self) -> None:
        path = INGEST_CONFIGS_DIR / "twitter" / "default.yaml"
        loaded = _load_yaml_mapping(path)
        params = loaded["ingestion_params"]
        result = params.get("keywords")
        expected = ["example"]
        assert result == expected


OLD_LIMIT_KEYS = frozenset({"limit", "limit_per_keyword", "limit_per_subreddit"})
INGEST_PLATFORMS = ("bluesky", "twitter", "reddit")


class TestLimitPerTaskYamlKey:
    """Tests that ingest YAML uses limit_per_task, not older platform cap keys."""

    def test_committed_ingest_yaml_does_not_use_older_cap_keys(self) -> None:
        found: list[str] = []
        for platform in INGEST_PLATFORMS:
            for path in sorted((INGEST_CONFIGS_DIR / platform).glob("*.yaml")):
                loaded = _load_yaml_mapping(path)
                params = loaded.get("ingestion_params")
                if not isinstance(params, dict):
                    continue
                for key in sorted(OLD_LIMIT_KEYS & params.keys()):
                    found.append(f"{path}: {key}")
        expected: list[str] = []
        assert found == expected

    def test_committed_ingest_yaml_sets_limit_per_task_int(self) -> None:
        missing: list[str] = []
        for platform in INGEST_PLATFORMS:
            for path in sorted((INGEST_CONFIGS_DIR / platform).glob("*.yaml")):
                loaded = _load_yaml_mapping(path)
                params = loaded.get("ingestion_params")
                if not isinstance(params, dict) or not isinstance(
                    params.get("limit_per_task"), int
                ):
                    missing.append(str(path))
        expected: list[str] = []
        assert missing == expected

    @pytest.mark.parametrize(
        "platform,expected",
        [
            ("bluesky", 50),
            ("twitter", 25),
            ("reddit", 5),
        ],
    )
    def test_default_yaml_keeps_platform_cap_values(
        self,
        platform: str,
        expected: int,
    ) -> None:
        path = INGEST_CONFIGS_DIR / platform / "default.yaml"
        loaded = _load_yaml_mapping(path)
        params = loaded["ingestion_params"]
        result = params.get("limit_per_task")
        assert result == expected
