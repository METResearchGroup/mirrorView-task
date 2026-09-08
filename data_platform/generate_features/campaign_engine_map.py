"""Campaign-only engine overrides for mixed OpenAI and Bedrock labeling.

Run from the repo root:

    PYTHONPATH=. uv run python -c \\
        "from data_platform.generate_features.campaign_engine_map import campaign_engine_type; \\
        print(campaign_engine_type('reddit_2026_09_03_233928_llm_features_v1', 'is_political'))"
"""

from __future__ import annotations

OPENAI_ENGINE_TYPE = "openai"
BEDROCK_ENGINE_TYPE = "bedrock"
REDDIT_LLM_FEATURES_CAMPAIGN_ID = "reddit_2026_09_03_233928_llm_features_v1"
BLUESKY_LLM_FEATURES_CAMPAIGN_ID = "bluesky_2026_09_03_235130_llm_features_v1"

REDDIT_CAMPAIGN_ENGINE_BY_FEATURE: dict[str, str] = {
    "is_news_or_opinion": OPENAI_ENGINE_TYPE,
    "is_political": OPENAI_ENGINE_TYPE,
    "political_stance": OPENAI_ENGINE_TYPE,
    "llm_toxicity_tiered": OPENAI_ENGINE_TYPE,
    "is_likely_spam": BEDROCK_ENGINE_TYPE,
    "is_self_contained": BEDROCK_ENGINE_TYPE,
    "is_structurally_complete": BEDROCK_ENGINE_TYPE,
}


def campaign_engine_type(campaign_id: str, feature: str) -> str:
    """Return ``openai`` or ``bedrock`` for one campaign feature.

    Parameters
    ----------
    campaign_id
        Campaign id. Only the pinned Reddit campaign uses a mixed map.
    feature
        Registry feature name.

    Returns
    -------
    str
        ``openai`` or ``bedrock``.

    Raises
    ------
    ValueError
        When the Reddit campaign has no map entry for ``feature``.
    """
    if campaign_id != REDDIT_LLM_FEATURES_CAMPAIGN_ID:
        return OPENAI_ENGINE_TYPE
    engine = REDDIT_CAMPAIGN_ENGINE_BY_FEATURE.get(feature)
    if engine is None:
        raise ValueError(
            f"campaign {campaign_id} has no engine map entry for {feature}"
        )
    return engine
