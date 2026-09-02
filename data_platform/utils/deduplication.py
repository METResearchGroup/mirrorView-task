"""In-memory skip-set session for ingest identity dedupe.

YAML policy tokens choose whether to load ids from earlier local runs.
The canonical prior-run token is ``prior_runs_same_dataset``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any
import warnings

if TYPE_CHECKING:
    from data_platform.utils.storage import StorageManager

PRIOR_RUN_POLICY = "prior_runs_same_dataset"
PRIOR_RUN_POLICY_ALIASES = frozenset({"prior_runs_all_datasets"})
PRIOR_RUN_POLICIES = frozenset({PRIOR_RUN_POLICY}) | PRIOR_RUN_POLICY_ALIASES
_DEPRECATION_STACKLEVEL = 3


def _deprecated_prior_run_tokens(policy: list[Any]) -> frozenset[str]:
    return frozenset(item for item in policy if item in PRIOR_RUN_POLICY_ALIASES)


def _warn_deprecated_prior_run_tokens(tokens: frozenset[str]) -> None:
    if not tokens:
        return
    alias_list = ", ".join(sorted(tokens))
    warnings.warn(
        f"{alias_list} is a deprecated alias of {PRIOR_RUN_POLICY}",
        DeprecationWarning,
        stacklevel=_DEPRECATION_STACKLEVEL,
    )


def policy_includes_prior_runs(policy: Any) -> bool:
    """True when YAML policy asks to skip ids already stored in earlier local runs.

    The canonical token is ``prior_runs_same_dataset``. Local storage only sees
    run directories for the current dataset_id, so that name matches the scan.

    ``prior_runs_all_datasets`` is a leftover Athena name. Callers may still
    pass it; it enables the same scan and should warn so configs can migrate.

    Parameters
    ----------
    policy
        YAML list of policy tokens, or any other value. Non-lists are treated
        as "do not skip prior runs."

    Returns
    -------
    bool
        True when the list includes the canonical token or its documented alias.
    """
    if not isinstance(policy, list):
        return False
    _warn_deprecated_prior_run_tokens(_deprecated_prior_run_tokens(policy))
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
