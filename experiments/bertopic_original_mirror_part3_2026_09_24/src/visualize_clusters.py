"""Plot BERTopic clusters. Implemented in Step 4.

Run from repo root::

    PYTHONPATH=. uv run --extra bertopic python -m experiments.bertopic_original_mirror_part3_2026_09_24.src.visualize_clusters --text-role original
"""

from __future__ import annotations

import argparse


def main() -> None:
    """Parse ``--text-role`` and stop until Step 4."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--text-role", choices=["original", "mirror", "joint"], required=True)
    parser.parse_args()
    raise NotImplementedError("implemented in Step 4")


if __name__ == "__main__":
    main()
