"""Flip prompt and FeatureSpec wiring."""

from __future__ import annotations

from data_platform.generate_features.models import FeatureSpec

from shared.flip_generation.models import FlipEngineRow, FlipLlmOutput

FEATURE_NAME = "flip"
TARGET_GROUP_PLACEHOLDER = (
    "[SPECIFIC FIGURE/GROUP — e.g., Republicans/Democrats, Donald Trump/Joe Biden]"
)
USER_TARGET_GROUP_PHRASE = "the target group named in the user message"
TOPIC_ALIGNMENT_INSTRUCTION = (
    "Keep the mirror on the same political topic/issue as the original and flip "
    "only the stance, not the subject — switch to a different issue only when "
    "the original's topic has no natural opposite-stance position."
)
USER_MESSAGE_TEMPLATE = """Target group: {target_group}

Post:
{original_text}"""


def flip_feature_spec() -> FeatureSpec:
    """Return the Bedrock FeatureSpec for flip generation."""
    raise NotImplementedError
