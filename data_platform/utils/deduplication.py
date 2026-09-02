"""This module keeps a set of record ids in memory so ingest can skip records it
has already stored.

YAML ``dedupe_policy`` lists (and Reddit comment/post policy lists) decide
whether to load ids from earlier local runs. Use ``prior_runs_same_dataset``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from data_platform.utils.storage import StorageManager

PRIOR_RUN_POLICY = "prior_runs_same_dataset"


def policy_includes_prior_runs(policy: object) -> bool:
    """Return True when YAML policy skips ids already stored in earlier local runs.

    Use ``prior_runs_same_dataset`` in the policy list. Local storage only has
    run directories for the current dataset_id, so that name matches the scan.

    Parameters
    ----------
    policy
        A YAML list of strings, or any other value. Non-lists return False.

    Returns
    -------
    bool
        True when the list contains ``prior_runs_same_dataset``.
    """
    if not isinstance(policy, list):
        return False
    return PRIOR_RUN_POLICY in policy


@dataclass(frozen=True)
class DedupeConfig:
    id_column: str
    filename: str | None = None
    include_prior_runs: bool = False


@dataclass
class DedupeSession:
    """In-memory skip set of already-written record ids for one pipeline session.

    Load methods add ids into ``seen_ids`` without replacing ids already present.
    Exclude drops matching rows and leaves ``seen_ids`` unchanged. Extend adds ids
    after those rows have been persisted.
    """

    config: DedupeConfig
    seen_ids: set[str] = field(default_factory=set)

    def warm(self, storage: StorageManager, output_dir: Path) -> None:  # noqa: F821
        """Load this-run ids, then all-run ids when ``include_prior_runs`` is true.

        Compatibility path for existing ingest and preprocess callers.
        """
        self.load_seen_ids(storage, output_dir)
        if self.config.include_prior_runs:
            self.load_seen_ids_from_all_runs(storage)

    def filter_rows(self, rows: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], int]:
        """Return unseen rows and a skipped count. Delegates to ``exclude_seen_ids``."""
        return self.exclude_seen_ids(rows)

    def note_appended(self, rows: list[dict[str, Any]]) -> None:
        """Record persisted row ids. Delegates to ``add_seen_ids``."""
        self.add_seen_ids(rows)

    def load_seen_ids(self, storage: StorageManager, run_dir: Path) -> None:  # noqa: F821
        """Add ids from one run directory to ``seen_ids`` without replacing existing ids.

        Does not read other run directories.

        Parameters
        ----------
        storage
            Disk helper that reads the id column from the run file.
        run_dir
            Timestamped run directory whose output file is scanned.
        """
        self.seen_ids |= storage.load_seen_ids_from_disk(
            run_dir,
            self.config.id_column,
            filename=self.config.filename,
        )

    def load_seen_ids_from_all_runs(self, storage: StorageManager) -> None:  # noqa: F821
        """Add ids from every timestamped run under the storage stage root to ``seen_ids``.

        Does not scan a single run directory by path. Ids already in ``seen_ids`` stay.

        Parameters
        ----------
        storage
            Disk helper whose stage root is walked for timestamped run directories.
        """
        self.seen_ids |= storage.load_seen_ids_from_all_runs(
            self.config.id_column,
            filename=self.config.filename,
        )

    def exclude_seen_ids(
        self, rows: list[dict[str, Any]]
    ) -> tuple[list[dict[str, Any]], int]:
        """Return rows whose id is not in ``seen_ids``, plus how many rows were dropped.

        Does not add ids to ``seen_ids``.

        Returns
        -------
        tuple[list[dict[str, Any]], int]
            Kept rows in original order, then the skipped count.
        """
        new_rows = [row for row in rows if row[self.config.id_column] not in self.seen_ids]
        skipped = len(rows) - len(new_rows)
        return new_rows, skipped

    def add_seen_ids(self, rows: list[dict[str, Any]]) -> None:
        """Add each row's id to ``seen_ids`` after those rows have been persisted."""
        for row in rows:
            self.seen_ids.add(row[self.config.id_column])
