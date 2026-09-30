"""Mining prompts and LabelTask construction for step 2."""

from __future__ import annotations

import pandas as pd

from data_platform.generate_features.models import LabelTask

from experiments.study_2_llm_based_feature_extraction_2026_09_29.shared.constants import (
    KEEP_PAIRS_PER_BATCH,
    REMOVE_PAIRS_PER_BATCH,
)

SYSTEM_PROMPT = """## Task

You are a computational linguistics analyst studying social-media posts from a keep/remove moderation task.

You will be shown a batch of posts that human annotators kept on the platform and a batch of posts that human annotators removed. Your job is to consider them jointly, and to find features that are distinct to the posts that were kept and distinct to the posts that were removed.

Return as structured output.

## Categories of features

Here are the categories that we want to consider:

### Category 1: Surface and lexical (`lexical`)

This category is about how the post is written, not what claim it makes. It covers length, slang, heavy punctuation, all-caps emphasis, profanity, hashtags and account mentions, and a high density of proper names.

Examples include emphatic typography, profane derogatory insults, colloquial language and insults, and hashtags and account mentions.

### Category 2: Topic and subject matter (`topic_subject`)

This category is about the subject of the post. Examples include a policy area (guns, climate, immigration, abortion, elections), a specific event or bill, a geographic scope, a historical analogy, and culture-war salience.

### Category 3: Semantic content (`semantic_content`)

This category is about the kind of claim the post makes. Examples include causal claims, moral language, a factual claim versus speculation, conspiracy, a claim that a group is being persecuted, a policy prescription, and a cost-benefit argument.

### Category 4: Pragmatics and communicative intent (`pragmatics`)

This category is about what the post is doing to the reader. Examples include sarcasm, mockery, a call to action, persuasion, venting, hedging, and outrage.

### Category 5: Target and directionality (`target`)

This category is about who the post attacks or praises, and which political side it points at. Examples include the type of actor criticized or praised, a left/right cue, us-versus-them framing, and elite-versus-populist framing.

### Category 6: Compositional and syntactic structure (`structure`)

This category is about the shape of the sentences. Examples include if-then conditionals, contrast with "but" or "however," rhetorical questions, parallel repetition, lists, quoted or attributed speech, and direct address in the second person."""

USER_TEMPLATE = """## Stimuli

### Posts that were kept

Each numbered item is one post pair. A pair is an original post and a mirror of that post. The two texts are labeled text 1 and text 2. Those labels do not say which text is the original.

Here are ten post pairs that were kept by human annotators:

{kept_pairs}

### Posts that were removed

Each numbered item is one post pair, labeled the same way as the kept pairs.

Here are ten post pairs that were removed by human annotators:

{removed_pairs}

## Task (repeated)

Consider the kept post pairs and the removed post pairs jointly. For each of the six categories, list the features that are distinct to the kept post pairs and the features that are distinct to the removed post pairs. Write each feature as one short phrase. Return as structured output."""


def render_pair_list(pairs: list[tuple[str, str]]) -> str:
    """Format post pairs as numbered text 1 / text 2 blocks.

    Parameters
    ----------
    pairs
        ``(original_text, mirror_text)`` tuples in display order.

    Returns
    -------
    str
        Multi-line pair list for the user prompt.
    """
    lines: list[str] = []
    for index, (original_text, mirror_text) in enumerate(pairs, start=1):
        lines.append(f"{index}. Text 1: {original_text}")
        lines.append(f"   Text 2: {mirror_text}")
    return "\n".join(lines)


def render_user_prompt(
    kept_pairs: list[tuple[str, str]], removed_pairs: list[tuple[str, str]]
) -> str:
    """Render the user message for one mining batch.

    Parameters
    ----------
    kept_pairs
        Ten kept post pairs.
    removed_pairs
        Ten removed post pairs.

    Returns
    -------
    str
        Filled user prompt text.
    """
    return USER_TEMPLATE.format(
        kept_pairs=render_pair_list(kept_pairs),
        removed_pairs=render_pair_list(removed_pairs),
    )


def _pairs_for_post_ids(
    post_ids: list[str], cohort: pd.DataFrame
) -> list[tuple[str, str]]:
    indexed = cohort.set_index("post_id")
    pairs: list[tuple[str, str]] = []
    for post_id in post_ids:
        row = indexed.loc[post_id]
        pairs.append((str(row["original_text"]), str(row["mirror_text"])))
    return pairs


def build_mining_tasks(batches: list[dict], cohort: pd.DataFrame) -> list[LabelTask]:
    """Build one labeling task per mining batch.

    Parameters
    ----------
    batches
        Batch dicts with ``batch_id``, ``keep_post_ids``, and ``remove_post_ids``.
    cohort
        Cohort with pair text columns.

    Returns
    -------
    list[LabelTask]
        Tasks keyed by ``batch_id``.

    Raises
    ------
    ValueError
        When a batch does not have exactly ten kept and ten removed pairs.
    """
    tasks: list[LabelTask] = []
    for batch in batches:
        keep_ids = batch["keep_post_ids"]
        remove_ids = batch["remove_post_ids"]
        if len(keep_ids) != KEEP_PAIRS_PER_BATCH or len(remove_ids) != REMOVE_PAIRS_PER_BATCH:
            raise ValueError(
                f"batch {batch.get('batch_id')} must have "
                f"{KEEP_PAIRS_PER_BATCH} kept and {REMOVE_PAIRS_PER_BATCH} removed pairs"
            )
        kept_pairs = _pairs_for_post_ids(keep_ids, cohort)
        removed_pairs = _pairs_for_post_ids(remove_ids, cohort)
        text = render_user_prompt(kept_pairs, removed_pairs)
        tasks.append(LabelTask(uri=batch["batch_id"], text=text))
    return tasks
