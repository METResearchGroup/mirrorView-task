"""Package-level path root and record file-name constants.

Run from the repo root:

    PYTHONPATH=. uv run pytest tests/data_platform/utils/test_paths.py -q
"""

from __future__ import annotations

from pathlib import Path

PACKAGE_ROOT: Path = Path(__file__).resolve().parent
POSTS_FILENAME: str = "posts.csv"
COMMENTS_FILENAME: str = "comments.csv"
METADATA_FILENAME: str = "metadata.json"
