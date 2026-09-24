"""Cache MiniLM embeddings for Part 3 posts. Implemented in Step 3.

Run from repo root::

    PYTHONPATH=. uv run --extra bertopic python -m experiments.bertopic_original_mirror_part3_2026_09_24.src.load_embeddings_minilm --text-role original
"""

from __future__ import annotations

import argparse


def main() -> None:
    """Parse ``--text-role`` and stop until Step 3."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--text-role", choices=["original", "mirror"], required=True)
    parser.parse_args()
    raise NotImplementedError("implemented in Step 3")


if __name__ == "__main__":
    main()
