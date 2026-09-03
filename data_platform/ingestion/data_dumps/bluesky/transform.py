"""Map Bluesky warehouse dump rows onto the Bluesky ingest record shape.

Run from the repo root:

    PYTHONPATH=. uv run python -c \\
        "from data_platform.ingestion.data_dumps.bluesky.transform import dump_post_to_sync_row"
"""

from __future__ import annotations

from collections.abc import Mapping


def dump_post_to_sync_row(
    row: Mapping[str, object],
    sync_timestamp: str,
) -> dict[str, object]:
    """Return a Bluesky ingest row for one warehouse dump post.

    Parameters
    ----------
    row
        Dump columns ``uri``, ``did``, ``created_at``, and ``text``.
    sync_timestamp
        Raw run directory name written onto ``sync_timestamp``.

    Returns
    -------
    dict[str, object]
        A dict that validates as ``SyncBlueskyPostModel``.

    Raises
    ------
    KeyError
        When a required dump key is missing.
    ValueError
        When ``uri`` or ``did`` is blank, or ``uri`` has no ``/``.
    """
    raise NotImplementedError
