"""Split concatenated source rows into Democrat and Republican party lists.

Run from the repo root:

    PYTHONPATH=. uv run python experiments/upsample_mixed_study_feeds_2026_09_11/run.py
"""

from __future__ import annotations

from experiments.load_study_assignments_2026_09_09.constants import (
    AssignmentRow,
    PARTY_DEMOCRAT,
    PARTY_REPUBLICAN,
)
from experiments.load_study_assignments_2026_09_09.split import (
    rewrite_ids,
    split_by_party,
)


def split_rewritten(
    rows: list[AssignmentRow],
) -> tuple[list[AssignmentRow], list[AssignmentRow]]:
    """Partition rows by original user id and rewrite party assignment ids."""
    democrat, republican = split_by_party(rows)
    return (
        rewrite_ids(democrat, PARTY_DEMOCRAT),
        rewrite_ids(republican, PARTY_REPUBLICAN),
    )


def require_original_party_prefix(
    democrat: list[AssignmentRow],
    republican: list[AssignmentRow],
    original_democrat: list[AssignmentRow],
    original_republican: list[AssignmentRow],
) -> None:
    """Raise when the rewritten original party prefix does not match.

    Compares ``id``, ``assigned_post_ids``, ``political_party``, and
    ``condition`` for each original party row against the start of the
    expanded party list.

    Raises
    ------
    ValueError
        On the first mismatched field.
    """
    raise NotImplementedError
