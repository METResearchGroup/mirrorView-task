"""Prompt templates for discovery, cluster labeling, and post labeling.

Run from the repo root::

    PYTHONPATH=. uv run python -c "
    from experiments.llm_feature_generation_phase_2_part_3_2026_09_24.src.prompts import (
        FEATURE_GENERATION_SYSTEM_PROMPT,
    )
    print(len(FEATURE_GENERATION_SYSTEM_PROMPT))
    "
"""

from __future__ import annotations

import json
from typing import Any

from experiments.llm_feature_generation_phase_2_part_3_2026_09_24.src.constants import (
    DECISION_KEEP,
    DECISION_REMOVE,
    MAX_KEEP_FEATURES_PER_BATCH,
    MAX_REMOVE_FEATURES_PER_BATCH,
)

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
- original_text and/or mirror_text depending on the text arm
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

SINGLE_CLASS_KEEP_SYSTEM_PROMPT = f"""
You are a computational linguistics analyst studying social-media posts from a keep/remove moderation task.

This batch contains ONLY posts with human decision=keep (modal linked-fate label).

Each item includes message_id, text fields for the active arm, and decision=keep.

Return at most {MAX_KEEP_FEATURES_PER_BATCH} features total across all posts in the batch.
Return structured JSON matching the SingleClassBatchFeatureGeneration schema (field: features).

{FEATURE_EXTRACTION_CATEGORY_SECTION}
""".strip()

SINGLE_CLASS_REMOVE_SYSTEM_PROMPT = f"""
You are a computational linguistics analyst studying social-media posts from a keep/remove moderation task.

This batch contains ONLY posts with human decision=remove (modal linked-fate label).

Each item includes message_id, text fields for the active arm, and decision=remove.

Return at most {MAX_REMOVE_FEATURES_PER_BATCH} features total across all posts in the batch.
Return structured JSON matching the SingleClassBatchFeatureGeneration schema (field: features).

{FEATURE_EXTRACTION_CATEGORY_SECTION}
""".strip()

SINGLE_CLASS_USER_TEMPLATE = """
Extract features for every post in this {label_class}-only batch.

Posts:
{posts_json}
""".strip()

CLUSTER_LABEL_KEEP_SYSTEM_PROMPT = """
You are labeling clusters of LLM-extracted linguistic features from social-media posts
that humans rated KEEP in a linked-fate keep/remove moderation task.

Task:
1. Propose a short cluster_label (8 words or fewer).
2. Write a one-sentence definition usable as a moderation criterion for KEEP-rated posts.
3. Optionally add salience_notes (or empty string).

Return structured JSON matching ClusterLabelResult.
""".strip()

CLUSTER_LABEL_REMOVE_SYSTEM_PROMPT = """
You are labeling clusters of LLM-extracted linguistic features from social-media posts
that humans rated REMOVE in a linked-fate keep/remove moderation task.

Task:
1. Propose a short cluster_label (8 words or fewer).
2. Write a one-sentence definition usable as a moderation criterion for REMOVE-rated posts.
3. Optionally add salience_notes (or empty string).

Return structured JSON matching ClusterLabelResult.
""".strip()

CLUSTER_LABEL_USER_TEMPLATE = """
Label this {label_class}-feature cluster.

cluster_id: {cluster_id}
n_members: {n_members}
sampled_features:
{sampled_features_json}
""".strip()

POST_LABEL_SYSTEM_PREFIX = """
You are labeling one social-media post against an approved moderation codebook.

For each codebook feature, return present=true when the feature clearly applies to the
post text, otherwise present=false. Use only the provided codebook definitions.

Codebook:
{codebook_json}
""".strip()

POST_LABEL_USER_TEMPLATE = """
Label this post.

text_surface: {text_surface}
post_text:
{text}
""".strip()

CODEBOOK_REWRITE_SYSTEM_PROMPT = """
You rewrite moderation codebook features for a later labeling step.

The labeler will only judge whether each feature is PRESENT in post text.
Do NOT mention keep/remove decisions, human ratings, clusters, or moderation outcomes.

For each input feature:
1. name: 2 to 6 words, lowercase, complete phrase (never truncate mid-thought).
2. definition: exactly one sentence starting with "The post" describing observable text/content.
3. is_topic_only: true when the feature is only policy topic, party/ideological target, or issue
   stance without rhetorical form (insults, sarcasm, calls to action, syntax, etc.).
4. topic_only_reason: short reason when is_topic_only is true, else "".

Return structured JSON matching CodebookRewriteBatch.
""".strip()

CODEBOOK_REWRITE_USER_TEMPLATE = """
Rewrite these codebook features (neutral, outcome-free definitions).

features_json:
{features_json}
""".strip()

_ARM_PAYLOAD_BUILDERS = {
    "original_only": lambda post: {
        "message_id": post["message_id"],
        "original_text": post["original_text"],
    },
    "mirror_only": lambda post: {
        "message_id": post["message_id"],
        "mirror_text": post["mirror_text"],
    },
    "paired": lambda post: {
        "message_id": post["message_id"],
        "original_text": post["original_text"],
        "mirror_text": post["mirror_text"],
    },
}


def build_feature_generation_messages(
    batch: dict[str, Any],
    arm: str,
) -> list[dict[str, str]]:
    """Build chat messages for one discovery batch and text arm."""
    if "keep_posts" in batch:
        return _build_mixed_messages(batch, arm)
    return _build_single_class_messages(batch, arm)


def build_cluster_label_messages(item: dict[str, Any]) -> list[dict[str, str]]:
    """Build chat messages for one HDBSCAN cluster labeling item."""
    label_class = str(item["label_class"])
    system_prompt = (
        CLUSTER_LABEL_KEEP_SYSTEM_PROMPT
        if label_class == DECISION_KEEP
        else CLUSTER_LABEL_REMOVE_SYSTEM_PROMPT
    )
    user_content = CLUSTER_LABEL_USER_TEMPLATE.format(
        label_class=label_class,
        cluster_id=item["cluster_id"],
        n_members=item["n_members"],
        sampled_features_json=json.dumps(item["sampled_features"], indent=2),
    )
    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_content},
    ]


def build_codebook_rewrite_messages(features: list[dict[str, Any]]) -> list[dict[str, str]]:
    """Build chat messages for one batch of codebook feature rewrites."""
    user_content = CODEBOOK_REWRITE_USER_TEMPLATE.format(
        features_json=json.dumps(features, indent=2),
    )
    return [
        {"role": "system", "content": CODEBOOK_REWRITE_SYSTEM_PROMPT},
        {"role": "user", "content": user_content},
    ]


def build_labeling_prompt(
    codebook: list[dict[str, Any]],
    text: str,
    text_surface: str,
) -> list[dict[str, str]]:
    """Build chat messages with a fixed codebook prefix and one post text."""
    system_content = POST_LABEL_SYSTEM_PREFIX.format(
        codebook_json=json.dumps(codebook, indent=2),
    )
    user_content = POST_LABEL_USER_TEMPLATE.format(text_surface=text_surface, text=text)
    return [
        {"role": "system", "content": system_content},
        {"role": "user", "content": user_content},
    ]


def _build_mixed_messages(batch: dict[str, Any], arm: str) -> list[dict[str, str]]:
    builder = _ARM_PAYLOAD_BUILDERS[arm]
    keep_payload = [{**builder(post), "decision": DECISION_KEEP} for post in batch["keep_posts"]]
    remove_payload = [
        {**builder(post), "decision": DECISION_REMOVE} for post in batch["remove_posts"]
    ]
    user_content = FEATURE_GENERATION_USER_TEMPLATE.format(
        keep_posts_json=json.dumps(keep_payload, indent=2),
        remove_posts_json=json.dumps(remove_payload, indent=2),
    )
    return [
        {"role": "system", "content": FEATURE_GENERATION_SYSTEM_PROMPT},
        {"role": "user", "content": user_content},
    ]


def _build_single_class_messages(batch: dict[str, Any], arm: str) -> list[dict[str, str]]:
    label_class = str(batch["label_class"])
    builder = _ARM_PAYLOAD_BUILDERS[arm]
    posts_payload = [
        {**builder(post), "decision": label_class} for post in batch["posts"]
    ]
    system_prompt = (
        SINGLE_CLASS_KEEP_SYSTEM_PROMPT
        if label_class == DECISION_KEEP
        else SINGLE_CLASS_REMOVE_SYSTEM_PROMPT
    )
    user_content = SINGLE_CLASS_USER_TEMPLATE.format(
        label_class=label_class,
        posts_json=json.dumps(posts_payload, indent=2),
    )
    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_content},
    ]
