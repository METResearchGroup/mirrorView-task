"""Keep or remove request and result mapping on top of the shared Jev scorer.

Run from repo root::

    PYTHONPATH=. uv run python -c "from experiments.zero_shot_jev_inference_2026_10_01.shared.jev import build_remove_request"
"""

from __future__ import annotations

from langchain_typesafe import ClassifierRequest, Noul, NoulCriteria

from experiments.zero_shot_jev_inference_2026_10_01.shared.constants import (
    JEV_MODEL,
    REMOVE_QUESTION_ID,
    REMOVE_THRESHOLD,
    STATE_POST_1_KEY,
    STATE_POST_2_KEY,
)
from experiments.zero_shot_llm_inference_2026_09_30.shared.prompts import (
    BASELINE_ZERO_SHOT_KEEP_REMOVE_PROMPT,
)
from experiments.zero_shot_llm_inference_2026_09_30.shared.schemas import (
    PREDICTION_SCHEMA_VERSION,
    PredictionRecord,
    RemovePrediction,
    Study2InputRecord,
    TokenUsage,
)
from shared.models.jev import JevResult

PAIR_BLOCK = "Post 1: {post_1_text}\n\nPost 2: {post_2_text}\n\nAllow Or Remove?"
REMOVE_QUESTION = (
    f"Post 1 is in `{STATE_POST_1_KEY}` and Post 2 is in `{STATE_POST_2_KEY}`.\n\n"
    "Should both posts in the pair be removed from the platform?"
)
REMOVE_CRITERIA = NoulCriteria(
    true="Remove: both posts in the pair should be removed from the platform.",
    false="Allow: both posts in the pair should be allowed on the platform.",
)


def build_remove_instructions(prompt: str) -> str:
    """Swap the baseline prompt's pair block for a yes or no remove question.

    Parameters
    ----------
    prompt
        Issue 326 baseline prompt text.

    Returns
    -------
    str
        Prompt text through the judgment line, then the remove question.

    Raises
    ------
    ValueError
        When the prompt does not end with exactly one pair block.
    """
    preamble, separator, tail = prompt.partition(PAIR_BLOCK)
    if not separator or tail:
        raise ValueError("baseline prompt must end with the Post 1/Post 2 pair block")
    return preamble + REMOVE_QUESTION


REMOVE_INSTRUCTIONS = build_remove_instructions(BASELINE_ZERO_SHOT_KEEP_REMOVE_PROMPT)


def build_remove_request(record: Study2InputRecord) -> ClassifierRequest:
    """Build the classifier input for one prepared pair, posts in input order.

    Parameters
    ----------
    record
        Prepared Study 2 pair.

    Returns
    -------
    ClassifierRequest
        State for the two posts and one remove Noul.
    """
    return {
        "state": {
            STATE_POST_1_KEY: record.post_1_text,
            STATE_POST_2_KEY: record.post_2_text,
        },
        "questions": {
            REMOVE_QUESTION_ID: Noul(
                instructions=REMOVE_INSTRUCTIONS,
                criteria=REMOVE_CRITERIA,
            ),
        },
    }


def to_prediction_record(
    run_id: str,
    record: Study2InputRecord,
    result: JevResult,
) -> PredictionRecord:
    """Map one Jev result onto the issue 326 prediction row.

    ``is_remove`` is derived from ``p_remove`` at 0.5. ``schema_version`` is
    issue 326's prediction schema version, which the proposal omitted because
    that field was added after the proposal text.

    Parameters
    ----------
    run_id
        Safe run identifier.
    record
        Prepared pair that was scored.
    result
        Validated Jev result for that pair.

    Returns
    -------
    PredictionRecord
        Prediction row with the stored Boolean label and token counts.
    """
    p_remove = result.noul(REMOVE_QUESTION_ID)
    prediction = RemovePrediction(is_remove=p_remove >= REMOVE_THRESHOLD, p_remove=p_remove)
    usage = TokenUsage(
        input_tokens=result.input_tokens,
        output_tokens=result.output_tokens,
        total_tokens=result.total_tokens,
    )
    return PredictionRecord(
        schema_version=PREDICTION_SCHEMA_VERSION,
        run_id=run_id,
        model_folder=JEV_MODEL.folder_name,
        model_id=JEV_MODEL.model_id,
        post_id=record.post_id,
        is_remove=prediction.is_remove,
        p_remove=prediction.p_remove,
        usage=usage,
    )
