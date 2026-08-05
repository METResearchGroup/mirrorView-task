"""Prompt templates for single-class feature generation and HDBSCAN cluster labeling."""

from __future__ import annotations

import json
from typing import Any

from experiments.create_llm_features_2026_08_05.src.paths import LabelClass

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
- rhetorical_question
- conditional_if_then_structure
- contrastive_but_however_structure
- anaphora_or_parallelism
- list_or_enumeration
- quote_or_attribution_embedding
- second_person_direct_address

Tag structure patterns, not just single tokens.

## Open-ended features

Beyond the checklists above, you may add salient features with category=open_ended and is_open_ended=true.
""".strip()

FEATURE_GENERATION_KEEP_SYSTEM_PROMPT = f"""
You are a computational linguistics analyst studying social-media posts from a keep/remove moderation task.

This batch contains ONLY posts with human decision=keep (modal linked-fate label).

Each item includes:
- message_id: unique identifier
- original_text and mirror_text (a political "mirror" rewrite)
- decision: always "keep" for every post in this batch

Your job is to extract features that characterize these keep-rated posts across ALL of the following categories in a single pass for this batch. Be conservative:
- Include a feature ONLY if you are highly confident it is present.
- Provide a short evidence_span quoted from the texts.
- Tag each feature with its category (one of the six fixed categories below, or open_ended).
- You MAY propose additional open-ended features (category=open_ended, is_open_ended=true) if they are salient.
- Return at most 8 features total across all posts in the batch.
- Each feature must include the message_id of the post it describes.
- Do NOT predict keep/remove labels. Do NOT mention model confusion buckets or error analysis framing. Only describe observable linguistic/content features.
- Focus on cues that help explain why a post might be kept under linked-fate moderation, without inventing moderator intent.
- Return structured JSON matching the SingleClassBatchFeatureGeneration schema (field: features).

{FEATURE_EXTRACTION_CATEGORY_SECTION}
""".strip()

FEATURE_GENERATION_KEEP_USER_TEMPLATE = """
Extract features for every post in this keep-only batch.

Keep-rated posts:
{posts_json}
""".strip()

FEATURE_GENERATION_REMOVE_SYSTEM_PROMPT = f"""
You are a computational linguistics analyst studying social-media posts from a keep/remove moderation task.

This batch contains ONLY posts with human decision=remove (modal linked-fate label).

Each item includes:
- message_id: unique identifier
- original_text and mirror_text (a political "mirror" rewrite)
- decision: always "remove" for every post in this batch

Your job is to extract features that characterize these remove-rated posts across ALL of the following categories in a single pass for this batch. Be conservative:
- Include a feature ONLY if you are highly confident it is present.
- Provide a short evidence_span quoted from the texts.
- Tag each feature with its category (one of the six fixed categories below, or open_ended).
- You MAY propose additional open-ended features (category=open_ended, is_open_ended=true) if they are salient.
- Return at most 8 features total across all posts in the batch.
- Each feature must include the message_id of the post it describes.
- Do NOT predict keep/remove labels. Do NOT mention model confusion buckets or error analysis framing. Only describe observable linguistic/content features.
- Focus on cues that help explain why a post might be removed under linked-fate moderation, without inventing moderator intent.
- Return structured JSON matching the SingleClassBatchFeatureGeneration schema (field: features).

{FEATURE_EXTRACTION_CATEGORY_SECTION}
""".strip()

FEATURE_GENERATION_REMOVE_USER_TEMPLATE = """
Extract features for every post in this remove-only batch.

Remove-rated posts:
{posts_json}
""".strip()

CLUSTER_LABEL_KEEP_SYSTEM_PROMPT = """
You are labeling clusters of LLM-extracted linguistic features from social-media posts
that humans rated KEEP in a linked-fate keep/remove moderation task.

You will receive:
- cluster_id
- label_class: keep
- a random sample of member features from this cluster (feature_name, feature_value,
  category, rationale, optional evidence_span)

Task:
1. Propose a short cluster_label (≤8 words) that names the shared linguistic/rhetorical
   pattern in the sample.
2. Write a one-sentence definition usable as a moderation criterion for KEEP-rated posts.
3. Optionally add salience_notes (or empty string).

Rules:
- Base the label only on the provided features. Do not invent features not present.
- Prefer form/rhetoric/pragmatics over raw topic names when both are present
  (e.g. prefer "hedged policy prescription" over "guns").
- Do NOT predict keep/remove for new posts. Do NOT mention classifier error buckets.
- Return structured JSON matching ClusterLabelResult.
""".strip()

CLUSTER_LABEL_KEEP_USER_TEMPLATE = """
Label this KEEP-feature cluster.

cluster_id: {cluster_id}
n_members: {n_members}
sampled_features:
{sampled_features_json}
""".strip()

CLUSTER_LABEL_REMOVE_SYSTEM_PROMPT = """
You are labeling clusters of LLM-extracted linguistic features from social-media posts
that humans rated REMOVE in a linked-fate keep/remove moderation task.

You will receive:
- cluster_id
- label_class: remove
- a random sample of member features from this cluster (feature_name, feature_value,
  category, rationale, optional evidence_span)

Task:
1. Propose a short cluster_label (≤8 words) that names the shared linguistic/rhetorical
   pattern in the sample.
2. Write a one-sentence definition usable as a moderation criterion for REMOVE-rated posts.
3. Optionally add salience_notes (or empty string).

Rules:
- Base the label only on the provided features. Do not invent features not present.
- Prefer form/rhetoric/pragmatics over raw topic names when both are present
  (e.g. prefer "emphatic outgroup ridicule" over "immigration").
- Do NOT predict keep/remove for new posts. Do NOT mention classifier error buckets.
- Return structured JSON matching ClusterLabelResult.
""".strip()

CLUSTER_LABEL_REMOVE_USER_TEMPLATE = """
Label this REMOVE-feature cluster.

cluster_id: {cluster_id}
n_members: {n_members}
sampled_features:
{sampled_features_json}
""".strip()

_FEATURE_GENERATION_PROMPTS = {
    LabelClass.KEEP: (
        FEATURE_GENERATION_KEEP_SYSTEM_PROMPT,
        FEATURE_GENERATION_KEEP_USER_TEMPLATE,
    ),
    LabelClass.REMOVE: (
        FEATURE_GENERATION_REMOVE_SYSTEM_PROMPT,
        FEATURE_GENERATION_REMOVE_USER_TEMPLATE,
    ),
}

_CLUSTER_LABEL_PROMPTS = {
    LabelClass.KEEP: (
        CLUSTER_LABEL_KEEP_SYSTEM_PROMPT,
        CLUSTER_LABEL_KEEP_USER_TEMPLATE,
    ),
    LabelClass.REMOVE: (
        CLUSTER_LABEL_REMOVE_SYSTEM_PROMPT,
        CLUSTER_LABEL_REMOVE_USER_TEMPLATE,
    ),
}


def build_feature_generation_messages(batch: dict[str, Any]) -> list[dict[str, str]]:
    """Build system/user chat messages for one single-class feature batch.

    Parameters
    ----------
    batch
        Runner item with ``label_class`` and ``posts``.

    Returns
    -------
    list[dict[str, str]]
        Chat messages for the research_tools runner.
    """
    label_class = LabelClass(batch["label_class"])
    system_prompt, user_template = _FEATURE_GENERATION_PROMPTS[label_class]
    posts_json = json.dumps(batch["posts"], indent=2)
    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_template.format(posts_json=posts_json)},
    ]


def build_cluster_label_messages(item: dict[str, Any]) -> list[dict[str, str]]:
    """Build system/user chat messages for one HDBSCAN cluster labeling item.

    Parameters
    ----------
    item
        Runner item with ``label_class``, ``cluster_id``, ``n_members``,
        and ``sampled_features``.

    Returns
    -------
    list[dict[str, str]]
        Chat messages for the research_tools runner.
    """
    label_class = LabelClass(item["label_class"])
    system_prompt, user_template = _CLUSTER_LABEL_PROMPTS[label_class]
    sampled_features_json = json.dumps(item["sampled_features"], indent=2)
    return [
        {"role": "system", "content": system_prompt},
        {
            "role": "user",
            "content": user_template.format(
                cluster_id=item["cluster_id"],
                n_members=item["n_members"],
                sampled_features_json=sampled_features_json,
            ),
        },
    ]
