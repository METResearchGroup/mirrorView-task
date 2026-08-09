"""Parse greedy keep/remove generations into decision + label.

Run from root: PYTHONPATH=. uv run python -c "from experiments.finetune_qwen_model_2026_08_08.src.parse_prediction import parse_generation; print(parse_generation('keep'))"
"""

from __future__ import annotations

from dataclasses import dataclass

INVALID_DECISION = "__invalid__"
VALID_DECISIONS = frozenset({"keep", "remove"})
MAX_NEW_TOKENS = 8


@dataclass(frozen=True)
class ParsedPrediction:
    """Parsed keep/remove prediction."""

    predicted_decision: str
    predicted_label: int | None


def parse_generation(raw_generation: str) -> ParsedPrediction:
    """Parse the first whitespace-delimited token as keep/remove.

    Parameters
    ----------
    raw_generation
        Model generation text.

    Returns
    -------
    ParsedPrediction
        ``keep``→label 0, ``remove``→label 1, else ``__invalid__`` / None.
    """
    token = str(raw_generation).strip().split()
    if not token:
        return ParsedPrediction(
            predicted_decision=INVALID_DECISION,
            predicted_label=None,
        )
    first = token[0].strip().lower().strip(".,:;!?\"'`")
    if first == "keep":
        return ParsedPrediction(predicted_decision="keep", predicted_label=0)
    if first == "remove":
        return ParsedPrediction(predicted_decision="remove", predicted_label=1)
    return ParsedPrediction(
        predicted_decision=INVALID_DECISION,
        predicted_label=None,
    )


def gold_label_from_decision(decision: str) -> int:
    """Map gold decision string to keep_remove_label."""
    normalized = str(decision).lower().strip()
    if normalized == "remove":
        return 1
    if normalized == "keep":
        return 0
    raise ValueError(f"Unexpected gold decision: {decision!r}")
