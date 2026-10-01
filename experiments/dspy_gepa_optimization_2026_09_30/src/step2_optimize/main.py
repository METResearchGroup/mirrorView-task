"""Validate the DSPy program and GEPA metric without a paid call.

Run from the repo root::

    PYTHONPATH=. uv run python experiments/dspy_gepa_optimization_2026_09_30/src/step2_optimize/main.py --validate-contracts
"""

from __future__ import annotations

import argparse
from types import SimpleNamespace

from experiments.dspy_gepa_optimization_2026_09_30.shared import evaluation
from experiments.dspy_gepa_optimization_2026_09_30.shared.config import (
    DEVELOPMENT_SPLIT,
    TEST_SPLIT,
)
from experiments.dspy_gepa_optimization_2026_09_30.shared.metric import (
    BalancedReflectionSampler,
    COPIED_OPTIMIZATION_TEXT,
    CandidateRecord,
    INSTRUCTION_TOO_LONG,
    MISSING_OUTPUT_CONTRACT,
    classification_metrics,
    gepa_metric,
    rejection_reasons,
    score_example,
    select_candidate,
)
from experiments.dspy_gepa_optimization_2026_09_30.shared.program import (
    dspy_demonstrations,
    seed_instruction,
)

PAID_CALLS = 0


def main() -> None:
    """Run local contract checks. Smoke and pilot modes are separate commands."""
    args = _parse_args()
    if args.validate_contracts:
        run_contract_checks()
        return
    raise SystemExit("pass --validate-contracts, or wait for the smoke command")


def run_contract_checks() -> None:
    """Exercise output, metric, sampling, rejection, and tie-break contracts."""
    evaluation.CONTRACT_MODE = True
    evaluation.LOADED_SPLITS.clear()
    optimization = evaluation.optimization_batch()
    validation = evaluation.balanced_validation_batch(evaluation.gepa_validation_batch())
    _check_counts(optimization, validation)
    _check_metric()
    _check_sampler(optimization.examples)
    _check_rejections(optimization.post_texts)
    _check_tie_break()
    _check_metrics_math()
    if DEVELOPMENT_SPLIT in evaluation.LOADED_SPLITS or TEST_SPLIT in evaluation.LOADED_SPLITS:
        raise RuntimeError("contract mode loaded a held-out split")
    print("fixed_demonstrations", len(dspy_demonstrations()))
    print("balanced_validation_rows", len(validation.examples))
    print("balanced_validation_ids", ",".join(validation.post_ids))
    print("loaded_splits", ",".join(evaluation.LOADED_SPLITS))
    print("paid_calls", PAID_CALLS)
    print("contract_checks", "passed")


def _check_counts(optimization: evaluation.ExampleBatch, validation: evaluation.ExampleBatch) -> None:
    demonstrations = dspy_demonstrations()
    if len(demonstrations) != 10:
        raise RuntimeError("expected 10 fixed demonstrations")
    if sum(bool(row.is_remove) for row in demonstrations) != 5:
        raise RuntimeError("expected five remove demonstrations")
    if len(validation.examples) != 10:
        raise RuntimeError("expected 10 balanced validation rows")
    if len(optimization.examples) != 222:
        raise RuntimeError("expected 222 optimization rows")


def _check_metric() -> None:
    gold_remove = SimpleNamespace(is_remove=True)
    gold_keep = SimpleNamespace(is_remove=False)
    valid = score_example(gold_remove, SimpleNamespace(is_remove=True, p_remove=0.5))
    boundary = score_example(gold_keep, SimpleNamespace(is_remove=False, p_remove=0.49))
    disagree = score_example(gold_remove, SimpleNamespace(is_remove=False, p_remove=0.5))
    invalid = score_example(gold_remove, SimpleNamespace(is_remove=True, p_remove=1.2))
    if valid.score != 1.0 or not valid.contract_passed:
        raise RuntimeError("valid remove prediction was rejected")
    if boundary.score != 1.0:
        raise RuntimeError("keep prediction below 0.5 was rejected")
    if disagree.score != 0.0 or disagree.contract_passed:
        raise RuntimeError("threshold disagreement received credit")
    if invalid.score != 0.0 or "contract failure" not in invalid.feedback:
        raise RuntimeError("invalid probability received credit")
    metric = gepa_metric(gold_remove, SimpleNamespace(is_remove=True, p_remove=1.0), None, None, None)
    if metric.score != 1.0 or "Gold label: remove" not in metric.feedback:
        raise RuntimeError("GEPA metric feedback is incomplete")


def _check_sampler(examples: list[object]) -> None:
    first = _batch_labels(examples)
    second = _batch_labels(examples)
    if first != second:
        raise RuntimeError("reflection batches are not deterministic")
    for labels in first:
        if labels != ["keep", "remove"]:
            raise RuntimeError(f"reflection batch was {labels}")


def _batch_labels(examples: list[object]) -> list[list[str]]:
    sampler = BalancedReflectionSampler()
    loader = evaluation.IndexedExampleLoader(examples)
    labels = []
    for _ in range(3):
        ids = sampler.next_minibatch_ids(loader, state=None)
        labels.append(["remove" if examples[data_id].is_remove else "keep" for data_id in ids])
    return labels


def _check_rejections(post_texts: list[str]) -> None:
    seed = seed_instruction()
    missing = rejection_reasons(seed.replace("Allow Or Remove?", ""), post_texts)
    oversized = rejection_reasons(seed + (" more" * 400), post_texts)
    copied = rejection_reasons(f"{seed}\n{post_texts[0]}", post_texts)
    if MISSING_OUTPUT_CONTRACT not in missing:
        raise RuntimeError("missing contract was not rejected")
    if INSTRUCTION_TOO_LONG not in oversized:
        raise RuntimeError("oversized instruction was not rejected")
    if COPIED_OPTIMIZATION_TEXT not in copied:
        raise RuntimeError("copied optimization text was not rejected")


def _check_tie_break() -> None:
    selected = select_candidate(
        [
            CandidateRecord(1, 0.5, "short"),
            CandidateRecord(0, 0.5, "short"),
            CandidateRecord(2, 0.6, "much longer instruction"),
        ]
    )
    if selected.index != 2:
        raise RuntimeError("higher accuracy did not win")
    tied = select_candidate(
        [
            CandidateRecord(1, 0.5, "bbbb"),
            CandidateRecord(0, 0.5, "aa"),
        ]
    )
    if tied.index != 0:
        raise RuntimeError("shorter instruction did not win the tie")


def _check_metrics_math() -> None:
    metrics = classification_metrics([True, False], [False, False])
    empty = classification_metrics([], [])
    if metrics["recall"] != 0.0 or metrics["precision"] != 0.0:
        raise RuntimeError("zero-denominator metrics were not zero")
    if empty["f1"] != 0.0 or empty["accuracy"] != 0.0:
        raise RuntimeError("empty metrics were not zero")


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Optimize the keep-or-remove instruction.")
    parser.add_argument("--validate-contracts", action="store_true")
    return parser.parse_args()


if __name__ == "__main__":
    main()
