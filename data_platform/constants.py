"""Package-level path root and record file-name constants.

Run from the repo root:

    PYTHONPATH=. uv run pytest tests/data_platform/utils/test_paths.py -q
"""

from __future__ import annotations

from pathlib import Path

PACKAGE_ROOT: Path = Path()
POSTS_FILENAME: str = ""
COMMENTS_FILENAME: str = ""
METADATA_FILENAME: str = ""
