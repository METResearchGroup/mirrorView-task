"""Collapse per-item runner JSONs into predictions.jsonl, then delete them.

Thin wrapper around
``experiments.llm_prompt_engineering_2026_08_05.consolidate_predictions`` with
v2 output defaults. Does not change classifier generation; run after a
timestamped run folder exists.

Run from repo root::

    PYTHONPATH=. uv run python \\
      experiments/llm_prompt_engineering_v2_2026_08_05/consolidate_predictions.py

    PYTHONPATH=. uv run python \\
      experiments/llm_prompt_engineering_v2_2026_08_05/consolidate_predictions.py \\
      --run-dir experiments/llm_prompt_engineering_v2_2026_08_05/outputs/control/outputs/<TS>
"""

from __future__ import annotations

from pathlib import Path

from experiments.llm_prompt_engineering_2026_08_05.consolidate_predictions import (
    main as _v1_main,
)

EXPERIMENT_ROOT = Path(__file__).resolve().parent
DEFAULT_OUTPUTS_ROOT = EXPERIMENT_ROOT / "outputs"


def main(argv: list[str] | None = None) -> None:
    """CLI entry: consolidate v2 run dirs (discover or ``--run-dir``)."""
    import sys

    args = list(argv) if argv is not None else sys.argv[1:]
    if not any(a == "--outputs-root" or a.startswith("--outputs-root=") for a in args):
        args = ["--outputs-root", str(DEFAULT_OUTPUTS_ROOT), *args]
    _v1_main(args)


if __name__ == "__main__":
    main()
