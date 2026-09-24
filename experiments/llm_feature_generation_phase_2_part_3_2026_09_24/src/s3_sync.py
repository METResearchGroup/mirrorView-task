"""Upload experiment artifacts to S3.

Run from the repo root::

    PYTHONPATH=. uv run python -m experiments.llm_feature_generation_phase_2_part_3_2026_09_24.src.s3_sync \\
      --paths data/post_split outputs/original_only/cohort
"""

from __future__ import annotations

from pathlib import Path


def s3_key_for_local(local_path: Path) -> str:
    """Map a local experiment path to an S3 object key."""
    raise NotImplementedError


def main() -> None:
    """Parse CLI args and upload the requested paths."""
    raise NotImplementedError


if __name__ == "__main__":
    main()
