"""Example conversion and split-scoped evaluation helpers.

Run from the repo root::

    PYTHONPATH=. uv run python experiments/dspy_gepa_optimization_2026_09_30/src/step2_optimize/main.py --validate-contracts
"""

from __future__ import annotations

import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass

import dspy
import pandas as pd

from experiments.dspy_gepa_optimization_2026_09_30.shared.artifacts import read_split
from experiments.dspy_gepa_optimization_2026_09_30.shared.config import (
    BALANCED_VALIDATION_KEEP_COUNT,
    BALANCED_VALIDATION_REMOVE_COUNT,
    DEVELOPMENT_SPLIT,
    GEPA_VALIDATION_SPLIT,
    KEEP_LABEL,
    OPTIMIZATION_SPLIT,
    REMOVE_LABEL,
    TASK_CONCURRENCY,
    TEST_SPLIT,
)
from experiments.dspy_gepa_optimization_2026_09_30.shared.data import post_rank
from experiments.dspy_gepa_optimization_2026_09_30.shared.metric import classification_metrics, score_example

LOADED_SPLITS: list[str] = []


@dataclass(frozen=True)
class ExampleBatch:
    """Examples and the post texts a proposal guard may not copy."""

    examples: list[dspy.Example]
    post_texts: list[str]
    post_ids: tuple[str, ...]


class IndexedExampleLoader:
    """Minimal loader whose ids are positions in an example list."""

    def __init__(self, examples: list[dspy.Example]) -> None:
        self.items = list(examples)

    def all_ids(self) -> list[int]:
        return list(range(len(self.items)))

    def fetch(self, ids: list[int]) -> list[dspy.Example]:
        return [self.items[data_id] for data_id in ids]

    def __len__(self) -> int:
        return len(self.items)


def load_scored_split(split_name: str) -> ExampleBatch:
    """Load one prepared split. Development and test stay out of contract mode."""
    if split_name in {DEVELOPMENT_SPLIT, TEST_SPLIT} and _contract_mode():
        raise RuntimeError(f"contract mode cannot load {split_name}")
    LOADED_SPLITS.append(split_name)
    frame = read_split(split_name)
    return _batch(frame)


def balanced_validation_batch(frame_batch: ExampleBatch) -> ExampleBatch:
    """Keep every remove row and five deterministically ranked keep rows."""
    remove_rows = [row for row in frame_batch.examples if bool(row.is_remove)]
    keep_rows = [row for row in frame_batch.examples if not bool(row.is_remove)]
    if len(remove_rows) != BALANCED_VALIDATION_REMOVE_COUNT:
        raise ValueError(f"expected {BALANCED_VALIDATION_REMOVE_COUNT} remove validation rows")
    ranked_keep = sorted(keep_rows, key=lambda row: post_rank(str(row.post_id)))
    chosen = remove_rows + ranked_keep[:BALANCED_VALIDATION_KEEP_COUNT]
    if len(chosen) != BALANCED_VALIDATION_REMOVE_COUNT + BALANCED_VALIDATION_KEEP_COUNT:
        raise ValueError("balanced validation set is incomplete")
    ordered = sorted(chosen, key=lambda row: str(row.post_id))
    return _batch_from_examples(ordered)


def score_examples(program: dspy.Module, examples: list[dspy.Example], concurrency: int = TASK_CONCURRENCY) -> list[dict[str, object]]:
    """Score examples with bounded concurrency and preserve input order."""
    if concurrency < 1:
        raise ValueError("concurrency must be positive")
    with ThreadPoolExecutor(max_workers=concurrency) as pool:
        return list(pool.map(lambda example: _score_one(program, example), examples))


def metrics_frame(rows: list[dict[str, object]]) -> dict[str, float]:
    """Aggregate remove-positive metrics from scored rows."""
    gold = [bool(row["gold_is_remove"]) for row in rows]
    predicted = [
        bool(row["predicted_is_remove"]) if row["contract_passed"] else not bool(row["gold_is_remove"])
        for row in rows
    ]
    metrics = classification_metrics(gold, predicted)
    metrics["rows"] = float(len(rows))
    metrics["contract_failures"] = float(sum(not row["contract_passed"] for row in rows))
    if len(gold) != len(rows):
        raise ValueError("scored rows are incomplete")
    return metrics


def optimization_batch() -> ExampleBatch:
    """Return the optimization split and mark it as loaded."""
    return load_scored_split(OPTIMIZATION_SPLIT)


def gepa_validation_batch() -> ExampleBatch:
    """Return the GEPA validation split and mark it as loaded."""
    return load_scored_split(GEPA_VALIDATION_SPLIT)


def _batch(frame: pd.DataFrame) -> ExampleBatch:
    examples = [_example(row) for row in frame.to_dict(orient="records")]
    return _batch_from_examples(examples)


def _batch_from_examples(examples: list[dspy.Example]) -> ExampleBatch:
    return ExampleBatch(
        examples=examples,
        post_texts=[text for row in examples for text in (row.post_1_text, row.post_2_text)],
        post_ids=tuple(str(row.post_id) for row in examples),
    )


def _example(row: dict[str, object]) -> dspy.Example:
    is_remove = int(row["keep_remove_label"]) == REMOVE_LABEL
    example = dspy.Example(
        post_1_text=str(row["original_text"]),
        post_2_text=str(row["mirror_text"]),
        is_remove=is_remove,
        p_remove=1.0 if is_remove else 0.0,
        post_id=str(row["post_id"]),
        keep_remove_label=int(row["keep_remove_label"]),
    )
    if int(row["keep_remove_label"]) not in {KEEP_LABEL, REMOVE_LABEL}:
        raise ValueError(f"unexpected label for {row['post_id']}")
    return example.with_inputs("post_1_text", "post_2_text")


def _score_one(program: dspy.Module, example: dspy.Example) -> dict[str, object]:
    started = time.perf_counter()
    try:
        prediction = program(post_1_text=example.post_1_text, post_2_text=example.post_2_text)
        result = score_example(example, prediction)
        reported = getattr(prediction, "p_remove", None)
        returned = getattr(prediction, "is_remove", None)
    except Exception as error:
        result = score_example(example, SimplePrediction(error))
        reported = None
        returned = None
        prediction_error = type(error).__name__
    else:
        prediction_error = ""
    return {
        "post_id": str(example.post_id),
        "gold_is_remove": bool(example.is_remove),
        "is_remove": returned,
        "p_remove": reported,
        "predicted_is_remove": _predicted(result, reported),
        "score": result.score,
        "feedback": result.feedback,
        "contract_passed": result.contract_passed,
        "latency_seconds": time.perf_counter() - started,
        "error": prediction_error,
    }


class SimplePrediction:
    """Stand-in prediction that fails the output contract."""

    def __init__(self, error: Exception) -> None:
        self.is_remove = False
        self.p_remove = error


def _predicted(result: object, reported: object) -> bool:
    if not result.contract_passed:
        return False
    return float(reported) >= 0.5


def _contract_mode() -> bool:
    return CONTRACT_MODE


CONTRACT_MODE = False
