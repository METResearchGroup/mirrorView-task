"""Example conversion and split-scoped evaluation helpers.

Run from the repo root::

    PYTHONPATH=. uv run python experiments/dspy_gepa_optimization_2026_09_30/src/step2_optimize/main.py --validate-contracts
"""

from __future__ import annotations

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
    TEST_SPLIT,
)
from experiments.dspy_gepa_optimization_2026_09_30.shared.data import post_rank

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


def _contract_mode() -> bool:
    return CONTRACT_MODE


CONTRACT_MODE = False
