"""GEPA metric, balanced sampling, and proposal guards.

Run from the repo root::

    PYTHONPATH=. uv run python experiments/dspy_gepa_optimization_2026_09_30/src/step2_optimize/main.py --validate-contracts
"""

from __future__ import annotations

from dataclasses import dataclass

import dspy

from experiments.dspy_gepa_optimization_2026_09_30.shared.config import (
    COPIED_SPAN_CHARACTERS,
    INSTRUCTION_LENGTH_LIMIT_RATIO,
    PROBABILITY_THRESHOLD,
    RANDOM_SEED,
)
from experiments.dspy_gepa_optimization_2026_09_30.shared.data import normalized_text, post_rank
from experiments.dspy_gepa_optimization_2026_09_30.shared.program import (
    seed_instruction,
    validate_remove_output,
)

CLOSING_LINE = "Allow Or Remove?"
MISSING_OUTPUT_CONTRACT = "missing_output_contract"
INSTRUCTION_TOO_LONG = "instruction_too_long"
COPIED_OPTIMIZATION_TEXT = "copied_optimization_text"
@dataclass(frozen=True)
class CandidateRecord:
    """One scored candidate used for deterministic selection."""

    index: int
    accuracy: float
    instruction: str


@dataclass(frozen=True)
class MetricResult:
    """Hard score and the feedback GEPA reads."""

    score: float
    feedback: str
    contract_passed: bool


class BalancedReflectionSampler:
    """Draw one keep row and one remove row on each reflection batch."""

    def __init__(self, seed: int = RANDOM_SEED) -> None:
        self._seed = seed
        self._keep_ids: list[int] = []
        self._remove_ids: list[int] = []
        self._keep_cursor = 0
        self._remove_cursor = 0
        self._prepared = False

    def next_minibatch_ids(self, loader: object, state: object) -> list[int]:
        """Return the next keep id and remove id."""
        del state
        if not self._prepared:
            self._prepare(loader)
        keep_id = self._keep_ids[self._keep_cursor % len(self._keep_ids)]
        remove_id = self._remove_ids[self._remove_cursor % len(self._remove_ids)]
        self._keep_cursor += 1
        self._remove_cursor += 1
        self._reshuffle_if_wrapped()
        return [keep_id, remove_id]

    def _prepare(self, loader: object) -> None:
        ids = list(loader.all_ids())
        rows = loader.fetch(ids)
        keep_ids = []
        remove_ids = []
        for data_id, row in zip(ids, rows, strict=True):
            if bool(row.is_remove):
                remove_ids.append(int(data_id))
            else:
                keep_ids.append(int(data_id))
        if not keep_ids or not remove_ids:
            raise ValueError("reflection sampling needs both classes")
        self._keep_ids = _ordered(keep_ids)
        self._remove_ids = _ordered(remove_ids)
        self._prepared = True

    def _reshuffle_if_wrapped(self) -> None:
        if self._keep_cursor % len(self._keep_ids) == 0:
            self._keep_ids = _ordered(self._keep_ids, self._keep_cursor)
        if self._remove_cursor % len(self._remove_ids) == 0:
            self._remove_ids = _ordered(self._remove_ids, self._remove_cursor)


def gepa_metric(gold: dspy.Example, pred: dspy.Prediction, trace: object, pred_name: str | None, pred_trace: object) -> dspy.Prediction:
    """Return GEPA's five-argument metric result."""
    del trace, pred_name, pred_trace
    result = score_example(gold, pred)
    return dspy.Prediction(score=result.score, feedback=result.feedback)


def score_example(gold: dspy.Example, pred: object) -> MetricResult:
    """Score one prediction with remove as the positive class."""
    contract_error = _contract_error(pred)
    probability = _reported_probability(pred)
    predicted_remove = None if contract_error else float(probability) >= PROBABILITY_THRESHOLD
    gold_remove = bool(gold.is_remove)
    correct = predicted_remove is not None and predicted_remove == gold_remove
    return MetricResult(
        score=1.0 if correct else 0.0,
        feedback=_feedback(gold_remove, predicted_remove, probability, contract_error),
        contract_passed=contract_error is None,
    )


def rejection_reasons(instruction: str, optimization_texts: list[str]) -> list[str]:
    """Return every proposal-guard failure, in a stable order."""
    reasons = []
    if CLOSING_LINE not in instruction:
        reasons.append(MISSING_OUTPUT_CONTRACT)
    if len(instruction) > len(seed_instruction()) * INSTRUCTION_LENGTH_LIMIT_RATIO:
        reasons.append(INSTRUCTION_TOO_LONG)
    if _copies_optimization_text(instruction, optimization_texts):
        reasons.append(COPIED_OPTIMIZATION_TEXT)
    return reasons


def select_candidate(records: list[CandidateRecord]) -> CandidateRecord:
    """Choose the highest balanced accuracy, then the shorter earlier prompt."""
    if not records:
        raise ValueError("candidate selection needs at least one record")
    return min(records, key=lambda record: (-record.accuracy, len(record.instruction), record.index))


def classification_metrics(gold: list[bool], predicted: list[bool]) -> dict[str, float]:
    """Return accuracy, precision, recall, and F1 with remove as positive."""
    if len(gold) != len(predicted):
        raise ValueError("gold and predicted lengths differ")
    true_positive = sum(actual and guess for actual, guess in zip(gold, predicted, strict=True))
    false_positive = sum((not actual) and guess for actual, guess in zip(gold, predicted, strict=True))
    false_negative = sum(actual and not guess for actual, guess in zip(gold, predicted, strict=True))
    true_negative = sum((not actual) and not guess for actual, guess in zip(gold, predicted, strict=True))
    precision = _ratio(true_positive, true_positive + false_positive)
    recall = _ratio(true_positive, true_positive + false_negative)
    return {
        "accuracy": _ratio(true_positive + true_negative, len(gold)),
        "precision": precision,
        "recall": recall,
        "f1": _ratio(2 * precision * recall, precision + recall),
    }


def _contract_error(pred: object) -> str | None:
    try:
        validate_remove_output(pred.is_remove, float(pred.p_remove))
    except (AttributeError, TypeError, ValueError) as error:
        return str(error)
    return None


def _reported_probability(pred: object) -> object:
    return getattr(pred, "p_remove", None)


def _feedback(gold_remove: bool, predicted_remove: bool | None, probability: object, contract_error: str | None) -> str:
    predicted = _label(predicted_remove)
    contract = "contract passed" if contract_error is None else f"contract failure: {contract_error}"
    return (
        f"Gold label: {_label(gold_remove)}. Predicted label: {predicted}. "
        f"Reported probability: {probability}. {contract}."
    )


def _label(is_remove: bool | None) -> str:
    if is_remove is None:
        return "invalid"
    return "remove" if is_remove else "keep"


def _copies_optimization_text(instruction: str, texts: list[str]) -> bool:
    normalized_instruction = normalized_text(instruction)
    width = COPIED_SPAN_CHARACTERS
    for text in texts:
        compact = normalized_text(text)
        if len(compact) < width:
            continue
        for start in range(len(compact) - width + 1):
            if compact[start : start + width] in normalized_instruction:
                return True
    return False


def _ordered(ids: list[int], salt: int = 0) -> list[int]:
    return sorted(ids, key=lambda data_id: post_rank(f"{RANDOM_SEED + salt}:{data_id}"))


def _ratio(numerator: float, denominator: float) -> float:
    if denominator == 0:
        return 0.0
    return float(numerator) / float(denominator)

