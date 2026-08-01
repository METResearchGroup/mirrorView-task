"""Prompt templates for keep/remove feature generation and theme synthesis."""

from __future__ import annotations

import json
from typing import Any

from experiments.llm_based_feature_generation_2026_07_31.schemas import (
    MAX_KEEP_FEATURES_PER_BATCH,
    MAX_REMOVE_FEATURES_PER_BATCH,
)

# Category checklist copied verbatim from
# experiments/followup_model_error_analysis_2026_07_15/extract/prompts.py
# (UNIFIED_EXTRACTION_PROMPT lines 21–92).
FEATURE_EXTRACTION_CATEGORY_SECTION = """
## Category 1: Surface and lexical (`surface_lexical`)

Fixed checklist (use when clearly present):
- approximate_token_length_band (short/medium/long)
- informal_register_or_slang
- high_punctuation_intensity
- all_caps_emphasis
- profanity_or_taboo_language
- hashtag_or_mention_pattern
- named_proper_nouns_density

## Category 2: Topic and subject matter (`topic_subject`)

Fixed checklist:
- primary_policy_domain (e.g., guns, climate, immigration, abortion, elections)
- specific_event_or_bill_reference
- geographic_scope (US_state, national, international)
- historical_analogy_reference
- culture_war_topic_salience

## Category 3: Semantic content (`semantic_content`)

Fixed checklist:
- causal_claim_present
- normative_moral_language
- factual_assertion_vs_speculation
- conspiratorial_framing
- victimhood_or_persecution_framing
- policy_prescription_present
- economic_cost_benefit_framing

## Category 4: Pragmatics and communicative intent (`pragmatics_intent`)

Fixed checklist:
- sarcasm_or_irony
- ridicule_or_mockery
- call_to_action
- persuasion_or_argumentation
- venting_or_expressive
- hedging_or_qualification
- emphatic_outrage

Only tag sarcasm if cues are strong (not speculative).

## Category 5: Target and directionality (`target_directionality`)

Fixed checklist:
- criticized_actor_type (politician, party, media, corporation, outgroup, ingroup, etc.)
- praised_actor_type
- left_right_directional_cue
- us_vs_them_framing
- elite_vs_populist_framing
- mirror_shift_direction (how the mirror re-targets blame or praise vs original)

Note directional shifts between original and mirror when confident.

## Category 6: Compositional and syntactic structure (`compositional_syntax`)

Fixed checklist:
- conditional_if_then_structure
- contrastive_but_however_structure
- rhetorical_question
- anaphora_or_parallelism
- list_or_enumeration
- quote_or_attribution_embedding
- second_person_direct_address

Tag structure patterns, not just single tokens.

## Open-ended features

Beyond the checklists above, you may add salient features with category=open_ended and is_open_ended=true.
""".strip()

FEATURE_GENERATION_SYSTEM_PROMPT = f"""
You are a computational linguistics analyst studying social-media posts from a keep/remove moderation task.

Each item includes:
- message_id: unique identifier
- original_text and mirror_text (a political "mirror" rewrite)
- decision: human keep or remove label for the post in this batch

Your job is to extract features across ALL of the following categories in a single pass for this batch. Be conservative:
- Include a feature ONLY if you are highly confident it is present.
- Provide a short evidence_span quoted from the texts.
- Tag each feature with its category (one of the six fixed categories below, or open_ended).
- You MAY propose additional open-ended features (category=open_ended, is_open_ended=true) if they are salient.
- Return at most {MAX_KEEP_FEATURES_PER_BATCH} features total in keep_features (across all keep-rated posts).
- Return at most {MAX_REMOVE_FEATURES_PER_BATCH} features total in remove_features (across all remove-rated posts).
- Maximum {MAX_KEEP_FEATURES_PER_BATCH + MAX_REMOVE_FEATURES_PER_BATCH} features for the entire response.
- Each feature must include the message_id of the post it describes.
- Do NOT predict keep/remove labels. Do NOT mention model confusion buckets or error analysis framing. Only describe observable linguistic/content features.
- Return structured JSON matching the BatchFeatureGeneration schema.

{FEATURE_EXTRACTION_CATEGORY_SECTION}

Distribute features across posts as appropriate. Each feature must cite its message_id.
""".strip()

FEATURE_GENERATION_USER_TEMPLATE = """
Extract features for every post in this batch. The batch contains separate
keep-rated and remove-rated groups.

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
