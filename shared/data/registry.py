"""Named catalog of study datasets under ``shared/data/``."""

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
STUDY_PHASE_2_PART_2_KEEP_REMOVE_LABELS_UNANIMOUS_MIN3 = (
    "STUDY_PHASE_2_PART_2_KEEP_REMOVE_LABELS_UNANIMOUS_MIN3"
)
STUDY_PHASE_2_PART_2_USER_REFLECTION_FEEDBACK = (
    "STUDY_PHASE_2_PART_2_USER_REFLECTION_FEEDBACK"
)
STUDY_PHASE_2_PART_3_RESULTS_FULL = "STUDY_PHASE_2_PART_3_RESULTS_FULL"
STUDY_PHASE_2_PART_3_STIMULI = "STUDY_PHASE_2_PART_3_STIMULI"
STUDY_PHASE_2_PART_2_AND_3_RESULTS_FULL = "STUDY_PHASE_2_PART_2_AND_3_RESULTS_FULL"
STUDY_PHASE_2_PART_2_AND_3_STIMULI = "STUDY_PHASE_2_PART_2_AND_3_STIMULI"


@dataclass(frozen=True)
class DatasetEntry:
    """Immutable catalog record for one registered study table.

    File-backed entries set ``relative_path``. Union entries set
    ``source_names`` instead; ``load_dataset`` stacks those sources.

    ``kind`` is ``results`` or ``stimuli`` for study tables, or
    ``transformed`` for derived artifacts under ``shared/data/transformed/``.
    """

    name: str
    relative_path: Path | None
    kind: DatasetKind
    study_phase: str
    source_names: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        has_path = self.relative_path is not None
        has_sources = bool(self.source_names)
        if has_path == has_sources:
            raise ValueError(
                f"{self.name}: set exactly one of relative_path or source_names"
            )

    @property
    def is_union(self) -> bool:
        """True when this entry is a stacked view of other datasets."""
        return bool(self.source_names)


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
    STUDY_PHASE_2_PART_2_KEEP_REMOVE_LABELS_UNANIMOUS_MIN3: DatasetEntry(
        name=STUDY_PHASE_2_PART_2_KEEP_REMOVE_LABELS_UNANIMOUS_MIN3,
        relative_path=Path(
            "shared/data/transformed/study_phase_2_part_2/"
            "keep_remove_labels_unanimous_min3.csv"
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
    STUDY_PHASE_2_PART_3_RESULTS_FULL: DatasetEntry(
        name=STUDY_PHASE_2_PART_3_RESULTS_FULL,
        relative_path=Path("shared/data/raw/study_phase_2_part_3/results/full.csv"),
        kind="results",
        study_phase="study_phase_2_part_3",
    ),
    STUDY_PHASE_2_PART_3_STIMULI: DatasetEntry(
        name=STUDY_PHASE_2_PART_3_STIMULI,
        relative_path=Path("shared/data/raw/study_phase_2_part_3/stimuli/flips.csv"),
        kind="stimuli",
        study_phase="study_phase_2_part_3",
    ),
    STUDY_PHASE_2_PART_2_AND_3_RESULTS_FULL: DatasetEntry(
        name=STUDY_PHASE_2_PART_2_AND_3_RESULTS_FULL,
        relative_path=None,
        kind="results",
        study_phase="study_phase_2_part_2_and_3",
        source_names=(
            STUDY_PHASE_2_PART_2_RESULTS_FULL,
            STUDY_PHASE_2_PART_3_RESULTS_FULL,
        ),
    ),
    STUDY_PHASE_2_PART_2_AND_3_STIMULI: DatasetEntry(
        name=STUDY_PHASE_2_PART_2_AND_3_STIMULI,
        relative_path=None,
        kind="stimuli",
        study_phase="study_phase_2_part_2_and_3",
        source_names=(
            STUDY_PHASE_2_PART_2_STIMULI,
            STUDY_PHASE_2_PART_3_STIMULI,
        ),
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
    """Absolute path for a file-backed ``name``. Does not check that the file exists.

    Raises:
        KeyError: If ``name`` is not in the catalog.
        ValueError: If ``name`` is a union dataset with no single file.
    """
    entry = get_dataset(name)
    if entry.relative_path is None:
        sources = ", ".join(entry.source_names)
        raise ValueError(
            f"Dataset {name!r} is a union of {sources} and has no single file. "
            "Load it with shared.data.dataloader.load_dataset."
        )
    return REPO_ROOT / entry.relative_path
