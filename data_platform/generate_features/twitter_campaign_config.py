"""Load the Twitter LLM campaign YAML for one locked campaign id."""

from __future__ import annotations

from typing import Any

from data_platform.utils.config_paths import load_yaml_config
from lib.constants import REPO_ROOT

ACCEPTED_CAMPAIGN_ID = "twitter_2026_09_06_192847_llm_features_v1"
CAMPAIGN_YAML_PATH = (
    REPO_ROOT
    / "data_platform/generate_features/configs/twitter/mirrorview_2026-09-05_llm_features_v1.yaml"
)


def load_twitter_campaign_config(campaign_id: str) -> dict[str, Any]:
    """Return the campaign YAML for the locked Twitter campaign id.

    Raises
    ------
    ValueError
        If ``campaign_id`` is not the accepted Twitter campaign id. The
        message names the rejected id.
    """
    if campaign_id != ACCEPTED_CAMPAIGN_ID:
        raise ValueError(f"unsupported twitter campaign id: {campaign_id}")
    return load_yaml_config(CAMPAIGN_YAML_PATH)
