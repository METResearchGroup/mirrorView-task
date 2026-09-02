from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from data_platform.utils.storage import StorageManager

PRIOR_RUN_POLICIES = frozenset({"prior_runs_same_dataset", "prior_runs_all_datasets"})


def policy_includes_prior_runs(policy: Any) -> bool:
    """True when YAML policy asks to skip ids already stored in earlier local runs.

    `prior_runs_all_datasets` used to mean Athena across datasets. Local-only
    storage can only see run dirs for the current dataset_id, so both names
    enable the same same-dataset scan.
    """
    if not isinstance(policy, list):
        return False
    return any(item in PRIOR_RUN_POLICIES for item in policy)


@dataclass(frozen=True)
class DedupeConfig:
    id_column: str
    filename: str | None = None
    include_prior_runs: bool = False


@dataclass
class DedupeSession:
    config: DedupeConfig
    seen_ids: set[str] = field(default_factory=set)

    def warm(self, storage: StorageManager, output_dir: Path) -> None:  # noqa: F821
        seen: set[str] = set()
        seen.update(
            storage.load_seen_ids_from_disk(
                output_dir,
                self.config.id_column,
                filename=self.config.filename,
            )
        )
        if self.config.include_prior_runs:
            seen.update(
                storage.load_seen_ids_from_all_runs(
                    self.config.id_column,
                    filename=self.config.filename,
                )
            )
        self.seen_ids |= seen

    def filter_rows(self, rows: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], int]:
        new_rows = [row for row in rows if row[self.config.id_column] not in self.seen_ids]
        skipped = len(rows) - len(new_rows)
        return new_rows, skipped

    def note_appended(self, rows: list[dict[str, Any]]) -> None:
        for row in rows:
            self.seen_ids.add(row[self.config.id_column])

    def load_seen_ids(self, storage: StorageManager, run_dir: Path) -> None:  # noqa: F821
        self.seen_ids |= storage.load_seen_ids_from_disk(
            run_dir,
            self.config.id_column,
            filename=self.config.filename,
        )

    def load_seen_ids_from_all_runs(self, storage: StorageManager) -> None:  # noqa: F821
        self.seen_ids |= storage.load_seen_ids_from_all_runs(
            self.config.id_column,
            filename=self.config.filename,
        )

    def exclude_seen_ids(
        self, rows: list[dict[str, Any]]
    ) -> tuple[list[dict[str, Any]], int]:
        new_rows = [row for row in rows if row[self.config.id_column] not in self.seen_ids]
        skipped = len(rows) - len(new_rows)
        return new_rows, skipped

    def add_seen_ids(self, rows: list[dict[str, Any]]) -> None:
        raise NotImplementedError
