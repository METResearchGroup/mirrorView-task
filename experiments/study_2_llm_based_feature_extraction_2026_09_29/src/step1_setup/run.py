"""Step 1 entrypoint: build cohort and mining batches.

Run from the repo root::

    PYTHONPATH=. uv run python experiments/study_2_llm_based_feature_extraction_2026_09_29/src/step1_setup/run.py

Verification (given / when / then):

given STUDY_2_RESULTS_FULL and STUDY_2_STIMULI from S3
when main runs build_cohort and build_batches with SEED=1
then cohort_pairs=15113, modal_keep=11910, modal_remove=3203, batches=320
and two uploaded= lines for cohort.parquet and batches.jsonl
"""

from __future__ import annotations

import json

import pandas as pd
from shared.data.dataloader import load_dataset
from shared.data.registry import STUDY_2_RESULTS_FULL, STUDY_2_STIMULI

from experiments.study_2_llm_based_feature_extraction_2026_09_29.shared.constants import (
    BATCHES_KEY,
    COHORT_KEY,
    EXPECTED_BATCHES,
    EXPECTED_FIVE_LABEL_PAIRS,
    EXPECTED_MODAL_KEEP,
    EXPECTED_MODAL_REMOVE,
    MODAL_LABEL_KEEP,
    MODAL_LABEL_REMOVE,
    SEED,
)
from experiments.study_2_llm_based_feature_extraction_2026_09_29.shared.storage import (
    local_path,
    upload_artifact,
)
from experiments.study_2_llm_based_feature_extraction_2026_09_29.src.step1_setup.build_batches import (
    build_batches,
)
from experiments.study_2_llm_based_feature_extraction_2026_09_29.src.step1_setup.build_cohort import (
    build_cohort,
)


def _validate_cohort_counts(cohort: pd.DataFrame) -> tuple[int, int]:
    """Raise ValueError when pinned cohort counts do not match."""
    pair_count = len(cohort)
    if pair_count != EXPECTED_FIVE_LABEL_PAIRS:
        raise ValueError(
            f"expected {EXPECTED_FIVE_LABEL_PAIRS} cohort pairs, found {pair_count}"
        )
    modal_keep = int(cohort["modal_label"].eq(MODAL_LABEL_KEEP).sum())
    modal_remove = int(cohort["modal_label"].eq(MODAL_LABEL_REMOVE).sum())
    if modal_keep != EXPECTED_MODAL_KEEP:
        raise ValueError(
            f"expected {EXPECTED_MODAL_KEEP} modal keep pairs, found {modal_keep}"
        )
    if modal_remove != EXPECTED_MODAL_REMOVE:
        raise ValueError(
            f"expected {EXPECTED_MODAL_REMOVE} modal remove pairs, found {modal_remove}"
        )
    return modal_keep, modal_remove


def _validate_batch_count(batches: list[dict]) -> None:
    """Raise ValueError when the batch count does not match the pinned value."""
    if len(batches) != EXPECTED_BATCHES:
        raise ValueError(
            f"expected {EXPECTED_BATCHES} batches, found {len(batches)}"
        )


def _write_cohort(cohort: pd.DataFrame) -> None:
    path = local_path(COHORT_KEY)
    path.parent.mkdir(parents=True, exist_ok=True)
    cohort.to_parquet(path, index=False)


def _write_batches(batches: list[dict]) -> None:
    path = local_path(BATCHES_KEY)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for batch in batches:
            handle.write(json.dumps(batch))
            handle.write("\n")


def main() -> None:
    """Load data, build cohort and batches, write outputs, and upload to S3."""
    results = load_dataset(STUDY_2_RESULTS_FULL, low_memory=False)
    stimuli = load_dataset(STUDY_2_STIMULI)
    cohort = build_cohort(results, stimuli)
    modal_keep, modal_remove = _validate_cohort_counts(cohort)
    batches = build_batches(cohort, SEED)
    _validate_batch_count(batches)
    _write_cohort(cohort)
    _write_batches(batches)
    cohort_uri = upload_artifact(COHORT_KEY)
    print(f"uploaded={cohort_uri}")
    batches_uri = upload_artifact(BATCHES_KEY)
    print(f"uploaded={batches_uri}")
    print(
        f"cohort_pairs={len(cohort)} modal_keep={modal_keep} "
        f"modal_remove={modal_remove} batches={len(batches)}"
    )


if __name__ == "__main__":
    main()
