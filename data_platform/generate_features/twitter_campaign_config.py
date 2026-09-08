"""Load a Twitter LLM campaign YAML by scanning the twitter configs directory."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from data_platform.utils.config_paths import load_yaml_config
from lib.constants import REPO_ROOT

TWITTER_CAMPAIGN_CONFIG_DIR = (
    REPO_ROOT / "data_platform/generate_features/configs/twitter"
)
CAMPAIGN_YAML_GLOB = "*.yaml"
UNSUPPORTED_CAMPAIGN_ID_PREFIX = "unsupported twitter campaign id: "


def load_twitter_campaign_config(campaign_id: str) -> dict[str, Any]:
    """Return the campaign YAML mapping whose campaign_id matches.

    Parameters
    ----------
    campaign_id
        Campaign id stored on a Twitter campaign YAML file.

    Returns
    -------
    dict[str, Any]
        The YAML mapping for that campaign.

    Raises
    ------
    ValueError
        If no YAML matches, or if two files share the same campaign id.
        A missing match uses the prefix ``unsupported twitter campaign id:``.
    """
    matches = _matching_campaign_configs(campaign_id)
    if len(matches) > 1:
        raise ValueError(f"duplicate twitter campaign id: {campaign_id}")
    if not matches:
        raise ValueError(f"{UNSUPPORTED_CAMPAIGN_ID_PREFIX}{campaign_id}")
    return matches[0]


def _matching_campaign_configs(campaign_id: str) -> list[dict[str, Any]]:
    """Return YAML mappings under the Twitter config dir with this campaign id."""
    matches: list[dict[str, Any]] = []
    for yaml_path in _twitter_campaign_yaml_paths():
        mapping = load_yaml_config(yaml_path)
        if mapping.get("campaign_id") == campaign_id:
            matches.append(mapping)
    return matches


def _twitter_campaign_yaml_paths() -> list[Path]:
    """Return Twitter campaign YAML files in sorted path order."""
    return sorted(TWITTER_CAMPAIGN_CONFIG_DIR.glob(CAMPAIGN_YAML_GLOB))
