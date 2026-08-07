"""Local-disk durability helpers for platform sync runs.

Bluesky S3 upload is opt-in via ``DATA_PLATFORM_BLUESKY_S3_UPLOAD``. Twitter and
Reddit treat successful local completion as durable for the preprocess gate.
"""

from __future__ import annotations

from lib.load_env_vars import EnvVarsContainer

_TRUTHY_UPLOAD_FLAGS = frozenset({"1", "true"})


def is_bluesky_s3_upload_enabled() -> bool:
    """Return whether Bluesky should upload raw runs to the shared lab S3 bucket.

    Returns
    -------
    bool
        True only when ``DATA_PLATFORM_BLUESKY_S3_UPLOAD`` is ``1`` or ``true``
        (case-insensitive). Missing, empty, ``0``, and ``false`` disable upload.
    """
    raw = EnvVarsContainer.get_env_var("DATA_PLATFORM_BLUESKY_S3_UPLOAD", required=False)
    return raw.strip().lower() in _TRUTHY_UPLOAD_FLAGS
