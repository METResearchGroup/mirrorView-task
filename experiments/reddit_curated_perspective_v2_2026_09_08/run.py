"""Run the Reddit curated Perspective v2 experiment.

Run from the repo root:

    PYTHONPATH=. uv run python experiments/reddit_curated_perspective_v2_2026_09_08/run.py --load-only
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from experiments.reddit_curated_perspective_v2_2026_09_08.load_curated import (
    PINNED_CURATED_SHA256,
    load_pinned_curated,
    medium_rows,
)

EXPERIMENT_DIR = Path(__file__).resolve().parent


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--load-only", action="store_true")
    args = parser.parse_args(argv)
    if args.load_only:
        curated = load_pinned_curated()
        medium = medium_rows(curated)
        print(f"curated_rows={len(curated)}")
        print(f"medium_rows={len(medium)}")
        print(f"source_sha256={PINNED_CURATED_SHA256}")
        return 0
    raise SystemExit("pass --load-only")


if __name__ == "__main__":
    sys.exit(main())
