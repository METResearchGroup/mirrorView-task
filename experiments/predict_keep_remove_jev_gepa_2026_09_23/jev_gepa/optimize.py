"""GEPA optimize runner for Jev keep/remove prompt optimization.

Run from the repo root:

    PYTHONPATH=. uv run python experiments/predict_keep_remove_jev_gepa_2026_09_23/jev_gepa/optimize.py --ablation-id B1_gepa_pair --smoke --max-metric-calls 60
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[3]
_SCRIPT_DIR = str(Path(__file__).resolve().parent)
if sys.path and sys.path[0] == _SCRIPT_DIR:
    sys.path.pop(0)
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from gepa.core.result import GEPAResult

from experiments.predict_keep_remove_jev_gepa_2026_09_23.jev_gepa.adapter import (
    JevDataInst,
    JevGepaAdapter,
    ScoreMode,
    ViewName,
)

EXPERIMENT_ROOT = _REPO_ROOT / "experiments/predict_keep_remove_jev_gepa_2026_09_23"
JEV_GEPA_ROOT = EXPERIMENT_ROOT / "jev_gepa"
OUTPUT_ROOT = JEV_GEPA_ROOT / "outputs"
GEPA_SEED = 20260924
DEFAULT_MAX_METRIC_CALLS = 9000
DEFAULT_RATE_CAP_PER_MIN = 200
SMOKE_VAL_SUBSET_SIZE = 20


@dataclass(frozen=True)
class OptimizeConfig:
    ablation_id: str
    view: ViewName
    score_mode: ScoreMode
    reflection_lm: str
    max_reflection_cost: float
    max_metric_calls: int
    seed: int
    run_dir: Path
    rate_cap_per_min: int = DEFAULT_RATE_CAP_PER_MIN


def load_gepa_splits() -> tuple[list[JevDataInst], list[JevDataInst], list[JevDataInst]]:
    raise NotImplementedError


def load_seed_instruction(ablation_id: str) -> str:
    raise NotImplementedError


def select_candidate_on_dev(
    result: GEPAResult,
    *,
    devset: list[JevDataInst],
    adapter: JevGepaAdapter,
) -> tuple[int, dict[str, str], float]:
    raise NotImplementedError


def run_optimize(config: OptimizeConfig, *, smoke: bool = False) -> GEPAResult:
    raise NotImplementedError


def main(argv: list[str] | None = None) -> None:
    raise NotImplementedError


if __name__ == "__main__":
    main(sys.argv[1:])
