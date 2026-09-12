"""Experiment 1 CLI wrapper."""

from __future__ import annotations

import sys

from experiments.ai_simulation_responses_2026_09_11.shared.run import main


if __name__ == "__main__":
    sys.argv = [*sys.argv[:1], "--experiment", "1", *sys.argv[1:]]
    main()
