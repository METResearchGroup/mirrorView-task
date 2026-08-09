"""Part-2-owned prompts for free-response feature gen and cluster labeling.

Run from repo root::

    PYTHONPATH=. uv run python -c "
    from experiments.mine_free_response_for_features_2026_08_03.part_2_mine_free_responses.src.prompts import build_feature_generation_messages
    print('prompts OK')
    "
"""

from __future__ import annotations

import json
from typing import Any

from experiments.mine_free_response_for_features_2026_08_03.part_2_mine_free_responses.src.paths import (
    LikertGroup,
)

OPEN_THEMATIC_CATEGORIES_SECTION = """
## Open thematic categories (guidance, not a rigid checklist)

Use category strings such as:
- `pair_comparison_strategy` — how they compared original vs mirror
- `decision_criteria` — rules/thresholds for keep vs remove
- `affect_or_confidence` — certainty, discomfort, indifference
- `content_cues` — topics, toxicity, partisanship, framing they claim to use
- `process_meta` — task understanding, confusion, ignoring the pair
- `other` — salient theme that does not fit above

Do NOT copy post-linguistics checklists from other experiments.
"""

_FEATURE_SYSTEM_LOW = f"""You are analyzing free-response reflections from participants who rated how much
seeing both versions of a post (original + political mirror) influenced their
keep/remove decisions.

This batch contains ONLY participants in the LOW influence group
(Likert rating < 4: seeing the pair influenced them little).

Each item has participant_id, phase1_pair_reflection_text, and their Likert rating.

## QA gate (do this first)
- If the batch is clearly garbage or nonsense (keyboard smash, empty meaning,
  unrelated spam, copy-paste gibberish, or text that cannot be interpreted as a
  reflection about the task), set qa_status=rejected_garbage, put a short reason
  in qa_notes, and return features=[] (empty).
- Borderline but readable reflections should be treated as usable.

## Feature extraction (only if qa_status=usable)
- Extract themes that characterize what participants say influenced (or failed to
  influence) their paired keep/remove judgments.
- Be conservative: include a feature ONLY if highly confident.
- At most 8 features total across the batch; each must include participant_id.
- Use open thematic categories (pair_comparison_strategy, decision_criteria,
  affect_or_confidence, content_cues, process_meta, other).
- Provide evidence_span quoted from the reflection text.
- Do NOT invent keep/remove labels for posts. Do NOT use post-linguistics checklists
  from other experiments.
- Return structured JSON matching the Part-2 schema (qa_status, qa_notes, features).
{OPEN_THEMATIC_CATEGORIES_SECTION}
""".strip()

_FEATURE_SYSTEM_HIGH = f"""You are analyzing free-response reflections from participants who rated how much
seeing both versions of a post (original + political mirror) influenced their
keep/remove decisions.

This batch contains ONLY participants in the HIGH influence group
(Likert rating >= 4: seeing the pair influenced them materially).

Each item has participant_id, phase1_pair_reflection_text, and their Likert rating.

## QA gate (do this first)
- If the batch is clearly garbage or nonsense (keyboard smash, empty meaning,
  unrelated spam, copy-paste gibberish, or text that cannot be interpreted as a
  reflection about the task), set qa_status=rejected_garbage, put a short reason
  in qa_notes, and return features=[] (empty).
- Borderline but readable reflections should be treated as usable.

## Feature extraction (only if qa_status=usable)
- Extract themes that characterize what participants say influenced (or failed to
  influence) their paired keep/remove judgments.
- Be conservative: include a feature ONLY if highly confident.
- At most 8 features total across the batch; each must include participant_id.
- Use open thematic categories (pair_comparison_strategy, decision_criteria,
  affect_or_confidence, content_cues, process_meta, other).
- Provide evidence_span quoted from the reflection text.
- Do NOT invent keep/remove labels for posts. Do NOT use post-linguistics checklists
  from other experiments.
- Return structured JSON matching the Part-2 schema (qa_status, qa_notes, features).
{OPEN_THEMATIC_CATEGORIES_SECTION}
""".strip()

_FEATURE_USER_TEMPLATE = """Analyze this batch of free-response reflections.

batch_id: {batch_id}
likert_group: {likert_group}
participant_ids: {participant_ids}

reflections JSON:
{reflections_json}
"""

_CLUSTER_SYSTEM_LOW = """You are labeling clusters of LLM-extracted themes from participant free responses
about how seeing original+mirror post pairs influenced keep/remove decisions.

This cluster comes from the LOW influence group (Likert < 4).

Given cluster_id and a random sample of member features, propose:
1. cluster_label (≤8 words) naming the shared theme
2. one-sentence definition usable in analysis of low-influence reflections
3. optional salience_notes (or empty string)

Base the label only on provided features. Do not invent themes.
Return structured JSON matching ClusterLabelResult.
""".strip()

_CLUSTER_SYSTEM_HIGH = """You are labeling clusters of LLM-extracted themes from participant free responses
about how seeing original+mirror post pairs influenced keep/remove decisions.

This cluster comes from the HIGH influence group (Likert >= 4).

Given cluster_id and a random sample of member features, propose:
1. cluster_label (≤8 words) naming the shared theme
2. one-sentence definition usable in analysis of high-influence reflections
3. optional salience_notes (or empty string)

Base the label only on provided features. Do not invent themes.
Return structured JSON matching ClusterLabelResult.
""".strip()

_CLUSTER_USER_TEMPLATE = """Label this HDBSCAN feature cluster.

cluster_id: {cluster_id}
likert_group: {likert_group}
n_members: {n_members}

sampled_features JSON:
{sampled_features_json}
"""

_FEATURE_GENERATION_PROMPTS = {
    LikertGroup.LOW.value: _FEATURE_SYSTEM_LOW,
    LikertGroup.HIGH.value: _FEATURE_SYSTEM_HIGH,
}

_CLUSTER_LABEL_PROMPTS = {
    LikertGroup.LOW.value: _CLUSTER_SYSTEM_LOW,
    LikertGroup.HIGH.value: _CLUSTER_SYSTEM_HIGH,
}


def build_feature_generation_messages(
    batch: dict[str, Any],
) -> list[dict[str, str]]:
    """Build chat messages for one free-response feature-generation batch.

    Parameters
    ----------
    batch
        Runner item with likert_group, batch_id, participant_ids, reflections.

    Returns
    -------
    list[dict[str, str]]
        System and user chat messages.
    """
    likert_group = str(batch["likert_group"])
    system = _FEATURE_GENERATION_PROMPTS[likert_group]
    user = _FEATURE_USER_TEMPLATE.format(
        batch_id=batch["batch_id"],
        likert_group=likert_group,
        participant_ids=json.dumps(batch["participant_ids"]),
        reflections_json=json.dumps(batch["reflections"], indent=2),
    )
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]


def build_cluster_label_messages(item: dict[str, Any]) -> list[dict[str, str]]:
    """Build chat messages for one HDBSCAN cluster labeling item.

    Parameters
    ----------
    item
        Runner item with cluster_id, likert_group, n_members, sampled_features.

    Returns
    -------
    list[dict[str, str]]
        System and user chat messages.
    """
    likert_group = str(item["likert_group"])
    system = _CLUSTER_LABEL_PROMPTS[likert_group]
    user = _CLUSTER_USER_TEMPLATE.format(
        cluster_id=item["cluster_id"],
        likert_group=likert_group,
        n_members=item["n_members"],
        sampled_features_json=json.dumps(item["sampled_features"], indent=2),
    )
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]
