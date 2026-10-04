"""Turn prepared splits into DSPy examples.

Run from the repo root::

    PYTHONPATH=. uv run python experiments/dspy_gepa_balanced_labels_2026_10_02/src/step2_optimize/main.py --help
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass

import dspy
import pandas as pd

from experiments.dspy_gepa_balanced_labels_2026_10_02.shared.artifacts import read_split
from experiments.dspy_gepa_balanced_labels_2026_10_02.shared.config import (
    BALANCED_VALIDATION_KEEP_COUNT,
    BALANCED_VALIDATION_REMOVE_COUNT,
    RANDOM_SEED,
)
from experiments.dspy_gepa_optimization_2026_09_30.shared.config import KEEP_LABEL, REMOVE_LABEL


@dataclass(frozen=True)
class ExampleBatch:
    """Examples and the post texts a proposal guard may not copy."""

    examples: list[dspy.Example]
    post_texts: list[str]
    post_ids: tuple[str, ...]


def load_examples(split_name: str) -> ExampleBatch:
    """Load one stored split as DSPy examples."""
    return _batch(read_split(split_name))


def balanced_validation_examples(validation: ExampleBatch) -> ExampleBatch:
    """Take five ranked keep rows and five ranked remove rows."""
    keep_rows = [row for row in validation.examples if not bool(row.is_remove)]
    remove_rows = [row for row in validation.examples if bool(row.is_remove)]
    chosen = _first(keep_rows, BALANCED_VALIDATION_KEEP_COUNT) + _first(remove_rows, BALANCED_VALIDATION_REMOVE_COUNT)
    if len(chosen) != BALANCED_VALIDATION_KEEP_COUNT + BALANCED_VALIDATION_REMOVE_COUNT:
        raise ValueError("balanced validation sample is incomplete")
    return _batch_from_examples(sorted(chosen, key=lambda row: str(row.post_id)))


def _batch(frame: pd.DataFrame) -> ExampleBatch:
    return _batch_from_examples([_example(row) for row in frame.to_dict(orient="records")])


def _batch_from_examples(examples: list[dspy.Example]) -> ExampleBatch:
    return ExampleBatch(
        examples=examples,
        post_texts=[text for row in examples for text in (row.post_1_text, row.post_2_text)],
        post_ids=tuple(str(row.post_id) for row in examples),
    )


def _example(row: dict[str, object]) -> dspy.Example:
    label = int(row["keep_remove_label"])
    if label not in {KEEP_LABEL, REMOVE_LABEL}:
        raise ValueError(f"unexpected label for {row['post_id']}")
    is_remove = label == REMOVE_LABEL
    example = dspy.Example(
        post_1_text=str(row["original_text"]),
        post_2_text=str(row["mirror_text"]),
        is_remove=is_remove,
        p_remove=1.0 if is_remove else 0.0,
        post_id=str(row["post_id"]),
        keep_remove_label=label,
    )
    return example.with_inputs("post_1_text", "post_2_text")


def _first(examples: list[dspy.Example], count: int) -> list[dspy.Example]:
    ranked = sorted(examples, key=lambda row: _rank(str(row.post_id)))
    if len(ranked) < count:
        raise ValueError(f"needed {count} rows and found {len(ranked)}")
    return ranked[:count]


def _rank(post_id: str) -> tuple[str, str]:
    digest = hashlib.sha256(f"{RANDOM_SEED}:{post_id}".encode()).hexdigest()
    return digest, post_id
