"""Prompts for feature generation and theme synthesis (keep/remove framing)."""

from __future__ import annotations

import json
from typing import Any

FEATURE_GENERATION_PROMPT = """
You are a computational linguistics analyst studying social-media posts from a keep/remove moderation task.

Each batch includes two groups of posts with human modal labels:
- keep: posts raters decided to keep
- remove: posts raters decided to remove

Each post includes:
- message_id: unique identifier
- original_text and mirror_text (a political "mirror" rewrite)
- decision: keep or remove

Your job is to extract high-confidence linguistic/content features for each post in the batch.
Be conservative:
- Include a feature ONLY if you are highly confident it is present.
- Set confidence in [0,1]; prefer features at or above 0.85.
- Provide a short evidence_span quoted from the texts.
- Tag each feature with a category (surface_lexical, topic_subject, semantic_content,
  pragmatics_intent, target_directionality, compositional_syntax, or open_ended).
- You MAY propose open-ended features when salient and high-confidence.
- Do NOT predict keep/remove labels. Only describe observable linguistic/content features.
- When features seem characteristic of the keep group or the remove group in this batch,
  note that in the feature_value or rationale, but still ground claims in evidence spans.
- Return structured JSON matching the BatchFeatureGeneration schema.

## Category guidance (non-exhaustive)

surface_lexical: length band, slang, punctuation intensity, caps, profanity, hashtags/mentions, proper nouns
topic_subject: policy domain, events/bills, geographic scope, historical analogy, culture-war salience
semantic_content: causal claims, moral language, speculation, conspiratorial framing, victimhood, policy prescription
pragmatics_intent: sarcasm, ridicule, call to action, persuasion, venting, hedging, outrage
target_directionality: criticized/praised actor types, left/right cues, us-vs-them, elite-vs-populist, mirror retargeting
compositional_syntax: conditionals, contrastive structure, rhetorical questions, parallelism, lists, quotes, second-person address

Batch id: {batch_id}

Keep posts:
{keep_posts_json}

Remove posts:
{remove_posts_json}
""".strip()


THEME_SYNTHESIS_PROMPT = """
You are synthesizing LLM-extracted linguistic features from social-media posts that have human keep/remove moderation labels.

Input: JSON of batches, each with keep_posts and remove_posts and their high-confidence extracted features.

Tasks:
1. Identify 5–12 themes of features that recur together across the corpus.
2. For each theme: name it, list defining features, give up to 10 example message_ids,
   report label_mix (counts of keep vs remove among the examples), and write a short interpretation.
3. List cross-cutting themes that appear across multiple theme groups.

Do not invent features not present in the input. Prefer interpretable, moderation-relevant themes.
Do not frame results in terms of classifier mistakes or confusion-matrix buckets.
Focus on linguistic/content commonalities among keep-labeled and remove-labeled posts.

Return structured JSON matching ThemeSynthesisResult.

Feature corpus:
{corpus_json}
""".strip()


def build_feature_generation_messages(batch: dict[str, Any]) -> list[dict[str, str]]:
    """Build chat messages for one mixed keep/remove batch."""
    keep_posts = [
        {
            "message_id": row["message_id"],
            "original_text": row["original_text"],
            "mirror_text": row["mirror_text"],
            "decision": row["decision"],
        }
        for row in batch["keep_posts"]
    ]
    remove_posts = [
        {
            "message_id": row["message_id"],
            "original_text": row["original_text"],
            "mirror_text": row["mirror_text"],
            "decision": row["decision"],
        }
        for row in batch["remove_posts"]
    ]
    content = FEATURE_GENERATION_PROMPT.format(
        batch_id=batch["batch_id"],
        keep_posts_json=json.dumps(keep_posts, ensure_ascii=False, indent=2),
        remove_posts_json=json.dumps(remove_posts, ensure_ascii=False, indent=2),
    )
    return [{"role": "user", "content": content}]


def build_theme_synthesis_messages(item: dict[str, Any]) -> list[dict[str, str]]:
    """Build chat messages for theme synthesis over aggregated stage-1 features."""
    content = THEME_SYNTHESIS_PROMPT.format(
        corpus_json=json.dumps(item["corpus"], ensure_ascii=False, indent=2),
    )
    return [{"role": "user", "content": content}]
