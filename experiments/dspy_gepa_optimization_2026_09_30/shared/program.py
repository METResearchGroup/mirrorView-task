"""Seed DSPy keep-or-remove program built from the issue 329 prompt.

Run from the repo root::

    PYTHONPATH=. uv run python experiments/dspy_gepa_optimization_2026_09_30/src/step1_setup/main.py --contract-only
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass

import dspy

from experiments.dspy_gepa_optimization_2026_09_30.shared.config import (
    KEEP_EXAMPLE_PROBABILITY,
    PROBABILITY_MAX,
    PROBABILITY_MIN,
    PROBABILITY_THRESHOLD,
    REMOVE_EXAMPLE_PROBABILITY,
    REFLECTION_MODEL_SETTINGS,
    TASK_MODEL_SETTINGS,
    LanguageModelSettings,
)
from experiments.few_shot_llm_inference_2026_09_30.shared.prompts import (
    BASELINE_FEW_SHOT_KEEP_REMOVE_PROMPT,
)

REMOVE_EXAMPLE_HEADER = "Here are examples of pairs of posts that human annotators remove:"
KEEP_EXAMPLE_HEADER = "Here are examples of pairs of posts that human annotators keep:"
POST_SLOT = "Post 1: {post_1_text}"
CLOSING_LINE = "Allow Or Remove?"
EXAMPLE_SPLIT = re.compile(r"(?m)^\d+\.\s+")
POST_2_MARKER = " Post 2: "
FIXED_DEMONSTRATION_COUNT = 10
KEEP_DEMONSTRATION_COUNT = 5
REMOVE_DEMONSTRATION_COUNT = 5


@dataclass(frozen=True)
class PromptDemonstration:
    """One labeled pair parsed from the issue 329 prompt."""

    post_1_text: str
    post_2_text: str
    is_remove: bool
    p_remove: float


class KeepRemoveSignature(dspy.Signature):
    """Classify whether both posts in a political mirror pair should be removed."""

    post_1_text: str = dspy.InputField()
    post_2_text: str = dspy.InputField()
    is_remove: bool = dspy.OutputField(desc="True when both posts should be removed.")
    p_remove: float = dspy.OutputField(desc="Probability that both posts should be removed, from 0 to 1.")


class KeepRemoveProgram(dspy.Module):
    """One predictor whose instruction GEPA may edit.

    Demonstrations, input names, and output names stay fixed.
    """

    def __init__(self, demonstrations: list[dspy.Example], instruction: str) -> None:
        super().__init__()
        signature = KeepRemoveSignature.with_instructions(instruction)
        self.classify = dspy.Predict(signature)
        self.classify.demos = demonstrations

    def forward(self, post_1_text: str, post_2_text: str) -> dspy.Prediction:
        """Return the model's remove decision and probability."""
        return self.classify(post_1_text=post_1_text, post_2_text=post_2_text)


def seed_instruction() -> str:
    """Return the editable instruction, with examples left to demonstrations."""
    prompt = BASELINE_FEW_SHOT_KEEP_REMOVE_PROMPT
    preamble, separator, _rest = prompt.partition(POST_SLOT)
    if not separator or CLOSING_LINE not in prompt:
        raise ValueError("issue 329 prompt is missing the post slot or closing line")
    return f"{preamble.rstrip()}\n\n{CLOSING_LINE}"


def prompt_demonstrations() -> tuple[PromptDemonstration, ...]:
    """Return the ten fixed examples in prompt order, remove examples first."""
    prompt = BASELINE_FEW_SHOT_KEEP_REMOVE_PROMPT
    remove_block, keep_block = _example_blocks(prompt)
    remove_rows = _pairs(remove_block, is_remove=True)
    keep_rows = _pairs(keep_block, is_remove=False)
    _require_demonstration_counts(remove_rows, keep_rows)
    return tuple(remove_rows + keep_rows)


def dspy_demonstrations() -> list[dspy.Example]:
    """Return DSPy examples whose inputs are the two post fields."""
    return [_to_example(row) for row in prompt_demonstrations()]


def build_seed_program() -> KeepRemoveProgram:
    """Return the seed program with the issue 329 instruction and ten demos."""
    return KeepRemoveProgram(dspy_demonstrations(), seed_instruction())


def build_language_model(settings: LanguageModelSettings) -> dspy.LM:
    """Return a DSPy language model using the confirmed Bedrock settings."""
    kwargs: dict[str, object] = {
        "max_tokens": settings.max_tokens,
        "cache": settings.cache,
        "num_retries": settings.num_retries,
    }
    if settings.temperature is not None:
        kwargs["temperature"] = settings.temperature
    language_model = dspy.LM(settings.litellm_model, **kwargs)
    if settings.temperature is None:
        language_model.kwargs.pop("temperature", None)
    return language_model


def build_reflection_model() -> dspy.LM:
    """Return the reflection model. It uses the same Bedrock model ID."""
    return build_language_model(REFLECTION_MODEL_SETTINGS)


def configure_task_model(settings: LanguageModelSettings = TASK_MODEL_SETTINGS) -> dspy.LM:
    """Install the task model as the active DSPy language model."""
    language_model = build_language_model(settings)
    dspy.configure(lm=language_model)
    return language_model


def validate_remove_output(is_remove: bool, p_remove: float) -> None:
    """Require a finite probability and a Boolean that matches the threshold.

    Raises
    ------
    ValueError
        When the probability is outside 0 to 1 or disagrees with the Boolean.
    """
    if isinstance(is_remove, bool) is False or isinstance(p_remove, bool):
        raise ValueError("is_remove must be bool and p_remove must be a number")
    if not math.isfinite(p_remove):
        raise ValueError("p_remove must be finite")
    if p_remove < PROBABILITY_MIN or p_remove > PROBABILITY_MAX:
        raise ValueError("p_remove must be between 0 and 1")
    if is_remove != (p_remove >= PROBABILITY_THRESHOLD):
        raise ValueError("is_remove disagrees with p_remove at 0.5")


def reflection_text(language_model: dspy.LM, instruction: str) -> str:
    """Ask the reflection model for one revised instruction."""
    response = language_model(
        "Propose one revised moderation instruction. "
        "Keep the task, inputs, and remove-or-keep decision unchanged.\n\n"
        f"{instruction}"
    )
    return _first_text(response)


def _example_blocks(prompt: str) -> tuple[str, str]:
    if REMOVE_EXAMPLE_HEADER not in prompt or KEEP_EXAMPLE_HEADER not in prompt:
        raise ValueError("issue 329 prompt is missing example headers")
    remove_and_rest = prompt.split(REMOVE_EXAMPLE_HEADER, 1)[1]
    remove_block, keep_and_rest = remove_and_rest.split(KEEP_EXAMPLE_HEADER, 1)
    keep_block = keep_and_rest.split(CLOSING_LINE, 1)[0]
    return remove_block, keep_block


def _pairs(block: str, is_remove: bool) -> list[PromptDemonstration]:
    rows = []
    for chunk in EXAMPLE_SPLIT.split(block):
        text = chunk.strip()
        if not text:
            continue
        rows.append(_demonstration(text, is_remove))
    return rows


def _demonstration(text: str, is_remove: bool) -> PromptDemonstration:
    if not text.startswith("Post 1:"):
        raise ValueError("example does not start with Post 1")
    body = text[len("Post 1:") :].strip()
    post_1_text, separator, post_2_text = body.partition(POST_2_MARKER)
    if not separator or not post_1_text.strip() or not post_2_text.strip():
        raise ValueError("example is missing Post 1 or Post 2 text")
    probability = REMOVE_EXAMPLE_PROBABILITY if is_remove else KEEP_EXAMPLE_PROBABILITY
    return PromptDemonstration(post_1_text.strip(), post_2_text.strip(), is_remove, probability)


def _require_demonstration_counts(
    remove_rows: list[PromptDemonstration],
    keep_rows: list[PromptDemonstration],
) -> None:
    if len(remove_rows) != REMOVE_DEMONSTRATION_COUNT:
        raise ValueError(f"expected {REMOVE_DEMONSTRATION_COUNT} remove examples")
    if len(keep_rows) != KEEP_DEMONSTRATION_COUNT:
        raise ValueError(f"expected {KEEP_DEMONSTRATION_COUNT} keep examples")
    if len(remove_rows) + len(keep_rows) != FIXED_DEMONSTRATION_COUNT:
        raise ValueError(f"expected {FIXED_DEMONSTRATION_COUNT} demonstrations")


def _to_example(row: PromptDemonstration) -> dspy.Example:
    example = dspy.Example(
        post_1_text=row.post_1_text,
        post_2_text=row.post_2_text,
        is_remove=row.is_remove,
        p_remove=row.p_remove,
    )
    return example.with_inputs("post_1_text", "post_2_text")


def _first_text(response: object) -> str:
    if isinstance(response, list) and response:
        return str(response[0])
    return str(response)

