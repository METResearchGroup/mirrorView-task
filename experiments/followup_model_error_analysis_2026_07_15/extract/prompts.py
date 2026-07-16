"""Unified multi-category extraction prompt templates."""

from __future__ import annotations

UNIFIED_EXTRACTION_PROMPT = """
You are a computational linguistics analyst studying social-media posts from a keep/remove moderation task.

Each item includes:
- original_text and mirrored_text (a political "mirror" rewrite)
- human_is_remove: ground-truth human label (0=keep, 1=remove)
- qwen_is_remove: Bedrock Qwen3 Next 80B prediction (0=keep, 1=remove)
- confusion_bucket: tp | tn | fp | fn

Your job is to extract features across ALL of the following categories in a single pass for each post. Be conservative:
- Include a feature ONLY if you are highly confident it is present.
- Set confidence in [0,1]; features below 0.85 will be discarded downstream.
- Provide a short evidence_span quoted from the texts.
- Tag each feature with its category (one of the six fixed categories below, or open_ended).
- You MAY propose additional open-ended features (category=open_ended, is_open_ended=true) if they are salient and high-confidence.
- Do NOT predict keep/remove labels. Do NOT explain Qwen's reasoning. Only describe observable linguistic/content features.
- Return structured JSON matching the BatchFeatureExtraction schema.

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

For each post in this chunk, return all high-confidence features across all categories.

Bucket: {bucket}
Chunk: {chunk_idx}
Posts:
{posts_json}
""".strip()


CLUSTERING_PROMPT = """
You are synthesizing LLM-extracted linguistic features from social-media posts grouped by Qwen3 keep/remove confusion buckets.

Input: JSONL of posts with their high-confidence extracted features (multiple categories).

Tasks:
1. Identify 5–12 clusters of posts/features that recur together.
2. For each cluster: name it, list defining features, give up to 10 example post_ids, report bucket_mix (tp/tn/fp/fn).
3. List cross-cutting themes across clusters.
4. Explicitly call out themes that are **over-represented among FP (false positive remove)** vs TN.

Do not invent features not present in the input. Prefer interpretable, moderation-relevant themes.

Return structured JSON matching ClusteringResult.

Feature corpus shard:
{corpus_jsonl}
""".strip()


CLUSTER_MERGE_PROMPT = """
You are merging multiple partial clustering results from shards of the same feature-extraction experiment.

Input: list of ClusteringResult objects from shards.

Tasks:
1. Merge semantically duplicate clusters.
2. Produce a final consolidated list of 6–15 clusters.
3. Highlight FP-enriched themes with supporting cluster_ids.

Return structured JSON matching ClusteringResult with shard_id="merged".

Shard results:
{shard_results_json}
""".strip()
