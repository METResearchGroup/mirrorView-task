"""Prompt templates for keep/remove feature generation and theme synthesis."""

from __future__ import annotations

import json
from typing import Any

FEATURE_GENERATION_SYSTEM_PROMPT = """
You are a computational linguistics analyst studying social-media posts from a
human keep/remove moderation study.

Each post includes:
- message_id: unique identifier
- original_text and mirror_text (a political mirror rewrite)
- decision: human keep or remove label for the post

Your job is to extract high-confidence linguistic and content features that
characterize or distinguish keep-rated versus remove-rated posts in the batch.
Be conservative:
- Include a feature ONLY if you are highly confident it is present.
- Set confidence in [0, 1]; prefer features at or above 0.85 confidence.
- Provide a short evidence_span quoted from the texts.
- Tag each feature with a category string (e.g. surface_lexical, topic_subject,
  semantic_content, pragmatics_intent, target_directionality, compositional_syntax,
  or open_ended).
- Do NOT predict keep/remove labels.
- Do NOT mention model confusion buckets or error analysis framing.
- Return structured JSON matching the BatchFeatureGeneration schema.
""".strip()

FEATURE_GENERATION_USER_TEMPLATE = """
Extract features for every post in this batch. The batch contains separate
keep-rated and remove-rated groups.

Batch index: {batch_index}

Keep-rated posts:
{keep_posts_json}

Remove-rated posts:
{remove_posts_json}
""".strip()

THEME_SYNTHESIS_SYSTEM_PROMPT = """
You are synthesizing LLM-extracted linguistic features from social-media posts
grouped by human keep/remove labels.

Input: JSON describing stage-1 feature extractions across multiple batches.

Tasks:
1. Identify 5–12 recurring themes across the feature corpus.
2. For each theme: assign an id, name it, list defining features, give example
   message_ids, report keep_count and remove_count, and write a short
   interpretation.
3. List cross_cutting_themes that span multiple themes or both label groups.

Focus on thematic commonalities in the extracted features. Do not invent features
not present in the input. Prefer interpretable, moderation-relevant themes.

Return structured JSON matching ThemeSynthesisResult.
""".strip()

THEME_SYNTHESIS_USER_TEMPLATE = """
Synthesize recurring themes from this aggregated feature corpus:

{corpus_json}
""".strip()


def build_feature_generation_messages(batch: dict[str, Any]) -> list[dict[str, str]]:
    """Build chat messages for one keep/remove batch."""
    keep_payload = [
        {
            "message_id": post["message_id"],
            "original_text": post["original_text"],
            "mirror_text": post["mirror_text"],
            "decision": "keep",
        }
        for post in batch["keep_posts"]
    ]
    remove_payload = [
        {
            "message_id": post["message_id"],
            "original_text": post["original_text"],
            "mirror_text": post["mirror_text"],
            "decision": "remove",
        }
        for post in batch["remove_posts"]
    ]
    user_content = FEATURE_GENERATION_USER_TEMPLATE.format(
        batch_index=batch["batch_id"],
        keep_posts_json=json.dumps(keep_payload, indent=2),
        remove_posts_json=json.dumps(remove_payload, indent=2),
    )
    return [
        {"role": "system", "content": FEATURE_GENERATION_SYSTEM_PROMPT},
        {"role": "user", "content": user_content},
    ]


def build_theme_synthesis_messages(corpus: dict[str, Any]) -> list[dict[str, str]]:
    """Build chat messages for theme synthesis over aggregated stage-1 features."""
    user_content = THEME_SYNTHESIS_USER_TEMPLATE.format(
        corpus_json=json.dumps(corpus, indent=2),
    )
    return [
        {"role": "system", "content": THEME_SYNTHESIS_SYSTEM_PROMPT},
        {"role": "user", "content": user_content},
    ]


# Exported for prompt-hygiene checks in verification commands.
THEME_SYNTHESIS_PROMPT = THEME_SYNTHESIS_SYSTEM_PROMPT + "\n\n" + THEME_SYNTHESIS_USER_TEMPLATE
