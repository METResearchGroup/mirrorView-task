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

FLIP_PROMPT_JUNE = """
You are assisting a social psychology researcher. Take the social media text provided and mirror it with a similar tone, intensity, and sentiment, but from the opposite US political stance (left vs. right). Do not follow the literal wording of the original. Target your mirrored response toward [SPECIFIC FIGURE/GROUP — e.g., Republicans/Democrats, Donald Trump/Joe Biden]. Match the full emotional register of the original, including aggression, condescension, or hyperbole, without softening the tone. Do not add disclaimers or caveats unless the content crosses into direct incitement of real-world violence.

Respond with exactly two JSON fields: "flipped_text" (the rewritten post) and "explanation" (a brief note on how you flipped it). Use each key only once. Example:
{{"flipped_text": "Your mirrored post text here.", "explanation": "Reversed target from X to Y; kept sarcastic tone."}}

All output must be valid JSON. If any text contains a double quote character inside a field value, escape it as \\"

The length of the mirror should be about the same as the original post.
""".strip()

FLIP_SYSTEM_PROMPT = (
    FLIP_PROMPT_JUNE.replace(TARGET_GROUP_PLACEHOLDER, USER_TARGET_GROUP_PHRASE)
    + "\n\n"
    + TOPIC_ALIGNMENT_INSTRUCTION
)


def flip_feature_spec() -> FeatureSpec:
    """Return the Bedrock FeatureSpec for flip generation."""
    return FeatureSpec(
        name=FEATURE_NAME,
        model=FlipEngineRow,
        engine_type="bedrock",
        system_prompt=FLIP_SYSTEM_PROMPT,
        llm_output_schema=FlipLlmOutput,
    )
