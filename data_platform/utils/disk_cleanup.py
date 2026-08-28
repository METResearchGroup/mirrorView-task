from __future__ import annotations

import shutil

from data_platform.utils.dataset import dataset_root

ALLOWED_PLATFORMS = frozenset({"bluesky", "reddit", "twitter"})


def delete_dataset_local_files(platform: str, dataset_id: str) -> None:
    """Delete every local file for a dataset under data_platform/data/.

    This is destructive and irreversible. Callers must ensure local artifacts are
    no longer needed before invoking.
    """
    if platform not in ALLOWED_PLATFORMS:
        raise ValueError(f"Unsupported platform for local delete: {platform!r}")
    root = dataset_root(platform, dataset_id)
    if not root.exists():
        raise FileNotFoundError(root)
    shutil.rmtree(root)
    print(f"delete_dataset_local_files: deleted {root}")
