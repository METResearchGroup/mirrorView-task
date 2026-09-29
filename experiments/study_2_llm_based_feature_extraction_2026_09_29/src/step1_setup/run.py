"""Step 1 entrypoint: build cohort and mining batches.

Run from the repo root::

    PYTHONPATH=. uv run python experiments/study_2_llm_based_feature_extraction_2026_09_29/src/step1_setup/run.py
"""

from __future__ import annotations

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


def main() -> None:
    """Load data, build cohort and batches, write outputs, and upload to S3."""
    raise NotImplementedError


if __name__ == "__main__":
    main()
