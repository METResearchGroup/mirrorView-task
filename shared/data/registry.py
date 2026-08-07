"""Named catalog of canonical study datasets under ``shared/data/``."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

DatasetKind = Literal["results", "stimuli", "transformed"]

REPO_ROOT = Path(__file__).resolve().parents[2]

STUDY_PHASE_2_PART_1_RESULTS_PILOT = "STUDY_PHASE_2_PART_1_RESULTS_PILOT"
STUDY_PHASE_2_PART_1_RESULTS_FULL = "STUDY_PHASE_2_PART_1_RESULTS_FULL"
STUDY_PHASE_2_PART_1_STIMULI = "STUDY_PHASE_2_PART_1_STIMULI"
STUDY_PHASE_2_PART_2_RESULTS_FULL = "STUDY_PHASE_2_PART_2_RESULTS_FULL"
STUDY_PHASE_2_PART_2_STIMULI = "STUDY_PHASE_2_PART_2_STIMULI"
STUDY_PHASE_2_PART_2_KEEP_REMOVE_LABELS = "STUDY_PHASE_2_PART_2_KEEP_REMOVE_LABELS"
STUDY_PHASE_2_PART_2_USER_REFLECTION_FEEDBACK = (
    "STUDY_PHASE_2_PART_2_USER_REFLECTION_FEEDBACK"
)


@dataclass(frozen=True)
class DatasetEntry:
    """Immutable catalog record for one registered study CSV.

    ``kind`` is ``results`` or ``stimuli`` for raw inputs, or
    ``transformed`` for derived artifacts under ``shared/data/transformed/``.
    """

    name: str
    relative_path: Path
    kind: DatasetKind
    study_phase: str


DATASETS: dict[str, DatasetEntry] = {
    STUDY_PHASE_2_PART_1_RESULTS_PILOT: DatasetEntry(
        name=STUDY_PHASE_2_PART_1_RESULTS_PILOT,
        relative_path=Path("shared/data/raw/study_phase_2_part_1/results/pilot.csv"),
        kind="results",
        study_phase="study_phase_2_part_1",
    ),
    STUDY_PHASE_2_PART_1_RESULTS_FULL: DatasetEntry(
        name=STUDY_PHASE_2_PART_1_RESULTS_FULL,
        relative_path=Path("shared/data/raw/study_phase_2_part_1/results/full.csv"),
        kind="results",
        study_phase="study_phase_2_part_1",
    ),
    STUDY_PHASE_2_PART_1_STIMULI: DatasetEntry(
        name=STUDY_PHASE_2_PART_1_STIMULI,
        relative_path=Path(
            "shared/data/raw/study_phase_2_part_1/stimuli/claude_generated_mirrors.csv"
        ),
        kind="stimuli",
        study_phase="study_phase_2_part_1",
    ),
    STUDY_PHASE_2_PART_2_RESULTS_FULL: DatasetEntry(
        name=STUDY_PHASE_2_PART_2_RESULTS_FULL,
        relative_path=Path("shared/data/raw/study_phase_2_part_2/results/full.csv"),
        kind="results",
        study_phase="study_phase_2_part_2",
    ),
    STUDY_PHASE_2_PART_2_STIMULI: DatasetEntry(
        name=STUDY_PHASE_2_PART_2_STIMULI,
        relative_path=Path("shared/data/raw/study_phase_2_part_2/stimuli/flips.csv"),
        kind="stimuli",
        study_phase="study_phase_2_part_2",
    ),
    STUDY_PHASE_2_PART_2_KEEP_REMOVE_LABELS: DatasetEntry(
        name=STUDY_PHASE_2_PART_2_KEEP_REMOVE_LABELS,
        relative_path=Path(
            "shared/data/transformed/study_phase_2_part_2/keep_remove_labels.csv"
        ),
        kind="transformed",
        study_phase="study_phase_2_part_2",
    ),
    STUDY_PHASE_2_PART_2_USER_REFLECTION_FEEDBACK: DatasetEntry(
        name=STUDY_PHASE_2_PART_2_USER_REFLECTION_FEEDBACK,
        relative_path=Path(
            "shared/data/transformed/study_phase_2_part_2/user_reflection_feedback.csv"
        ),
        kind="transformed",
        study_phase="study_phase_2_part_2",
    ),
}


def get_dataset(name: str) -> DatasetEntry:
    """Return the registry entry for ``name``.

    Raises:
        KeyError: If ``name`` is not in the catalog.
    """
    try:
        return DATASETS[name]
    except KeyError as exc:
        known = ", ".join(sorted(DATASETS))
        raise KeyError(
            f"Unknown dataset {name!r}. Valid names are in shared.data.registry: {known}"
        ) from exc


def resolve_path(name: str) -> Path:
    """Absolute path for ``name``. Does not check that the file exists."""
    entry = get_dataset(name)
    return REPO_ROOT / entry.relative_path
