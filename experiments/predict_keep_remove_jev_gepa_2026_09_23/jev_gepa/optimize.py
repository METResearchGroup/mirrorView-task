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
import pandas as pd

from experiments.predict_keep_remove_jev_gepa_2026_09_23.jev_gepa.adapter import (
    DEFAULT_THRESHOLD,
    JevDataInst,
    JevGepaAdapter,
    ScoreMode,
    ViewName,
)
from experiments.predict_keep_remove_jev_gepa_2026_09_23.shared.metrics import probability_metrics
from experiments.predict_keep_remove_jev_gepa_2026_09_23.shared.prompt import POSTS_STATE_KEY, build_noul_instruction
from experiments.predict_keep_remove_jev_gepa_2026_09_23.shared.splits import COHORT_PARQUET

EXPERIMENT_ROOT = _REPO_ROOT / "experiments/predict_keep_remove_jev_gepa_2026_09_23"
JEV_GEPA_ROOT = EXPERIMENT_ROOT / "jev_gepa"
JEV_BASELINE_OUTPUT_ROOT = EXPERIMENT_ROOT / "jev_baseline/outputs"
OUTPUT_ROOT = JEV_GEPA_ROOT / "outputs"
GEPA_SEED = 20260924
DEFAULT_MAX_METRIC_CALLS = 9000
DEFAULT_RATE_CAP_PER_MIN = 200
SMOKE_VAL_SUBSET_SIZE = 20
DEV_SELECTION_FILENAME = "dev_selection.json"
GEPA_RESULT_FILENAME = "gepa_result.json"
SELECTED_CANDIDATE_FILENAME = "selected_candidate.json"

ABLATION_REGISTRY: dict[str, dict[str, object]] = {
    "B1_gepa_pair": {
        "view": "pair",
        "score_mode": "probability",
        "reflection_lm": "openai/gpt-6-luna",
        "max_reflection_cost": 5.0,
        "stage_a_seed": "A1_pair_study_prompt",
    },
    "B1T_gepa_pair_terra": {
        "view": "pair",
        "score_mode": "probability",
        "reflection_lm": "openai/gpt-5.6-terra",
        "max_reflection_cost": 20.0,
        "stage_a_seed": "A1_pair_study_prompt",
    },
    "B2_gepa_original": {
        "view": "original",
        "score_mode": "probability",
        "reflection_lm": "openai/gpt-6-luna",
        "max_reflection_cost": 5.0,
        "stage_a_seed": "A2_original_only",
    },
    "B3_gepa_mirror": {
        "view": "mirror",
        "score_mode": "probability",
        "reflection_lm": "openai/gpt-6-luna",
        "max_reflection_cost": 5.0,
        "stage_a_seed": "A3_mirror_only",
    },
    "B4_gepa_asymmetric_reward": {
        "view": "pair",
        "score_mode": "asymmetric",
        "reflection_lm": "openai/gpt-6-luna",
        "max_reflection_cost": 5.0,
        "stage_a_seed": "A1_pair_study_prompt",
    },
}


def resolve_ablation_config(ablation_id: str) -> OptimizeConfig:
    """Build OptimizeConfig from the ablation registry."""
    try:
        entry = ABLATION_REGISTRY[ablation_id]
    except KeyError as exc:
        raise ValueError(f"unknown ablation_id: {ablation_id}") from exc
    run_dir = OUTPUT_ROOT / ablation_id / "gepa_run"
    return OptimizeConfig(
        ablation_id=ablation_id,
        view=str(entry["view"]),  # type: ignore[arg-type]
        score_mode=str(entry["score_mode"]),  # type: ignore[arg-type]
        reflection_lm=str(entry["reflection_lm"]),
        max_reflection_cost=float(entry["max_reflection_cost"]),
        max_metric_calls=DEFAULT_MAX_METRIC_CALLS,
        seed=GEPA_SEED,
        run_dir=run_dir,
    )


def _row_to_jev_data_inst(row: object) -> JevDataInst:
    return JevDataInst(
        post_id=str(row.post_id),
        original_text=str(row.original_text),
        mirror_text=str(row.mirror_text),
        post_1_role=str(row.post_1_role),
        post_2_role=str(row.post_2_role),
        label=int(row.label),
        n_keep=int(row.n_keep),
        n_remove=int(row.n_remove),
        n_raters=int(row.n_raters),
        sampled_stance=str(row.sampled_stance),
        sample_toxicity_type=str(row.sample_toxicity_type),
    )


def load_gepa_splits() -> tuple[list[JevDataInst], list[JevDataInst], list[JevDataInst]]:
    """Load GEPA train, val, and dev splits from the cohort parquet."""
    parquet_path = _REPO_ROOT / COHORT_PARQUET
    if not parquet_path.is_file():
        raise FileNotFoundError(f"cohort parquet missing at {parquet_path}")
    frame = pd.read_parquet(parquet_path)
    trainset = [
        _row_to_jev_data_inst(row)
        for row in frame.loc[frame["gepa_subset"].eq("train")].itertuples()
    ]
    valset = [
        _row_to_jev_data_inst(row)
        for row in frame.loc[frame["gepa_subset"].eq("val")].itertuples()
    ]
    devset = [
        _row_to_jev_data_inst(row)
        for row in frame.loc[frame["split"].eq("dev")].itertuples()
    ]
    return trainset, valset, devset


def _strip_consider_prefix(instruction: str) -> str:
    prefix = f"Consider `{POSTS_STATE_KEY}[0]`. "
    if instruction.startswith(prefix):
        return instruction[len(prefix) :]
    return instruction


def load_seed_instruction(ablation_id: str) -> str:
    """Return the seed task instruction for GEPA (without the Consider prefix)."""
    entry = ABLATION_REGISTRY[ablation_id]
    view = str(entry["view"])
    stage_a_seed = str(entry["stage_a_seed"])
    stage_a_results = JEV_BASELINE_OUTPUT_ROOT / stage_a_seed / "results.json"
    if stage_a_results.is_file():
        return _strip_consider_prefix(build_noul_instruction(0, view))
    return _strip_consider_prefix(build_noul_instruction(0, view))


def select_candidate_on_dev(
    result: GEPAResult,
    *,
    devset: list[JevDataInst],
    adapter: JevGepaAdapter,
) -> tuple[int, dict[str, str], float]:
    """Pick the accepted candidate with highest dev F1 at threshold 0.5."""
    best_idx = 0
    best_candidate = result.candidates[0]
    best_f1 = -1.0
    labels = [example.label for example in devset]
    for candidate_idx, candidate in enumerate(result.candidates):
        eval_batch = adapter.evaluate(devset, candidate, capture_traces=False)
        probabilities = [output.p_remove for output in eval_batch.outputs]
        dev_f1 = probability_metrics(
            labels,
            probabilities,
            threshold=DEFAULT_THRESHOLD,
        ).f1
        if dev_f1 > best_f1:
            best_f1 = dev_f1
            best_idx = candidate_idx
            best_candidate = candidate
    return best_idx, best_candidate, best_f1


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


def run_optimize(config: OptimizeConfig, *, smoke: bool = False) -> GEPAResult:
    raise NotImplementedError


def main(argv: list[str] | None = None) -> None:
    raise NotImplementedError


if __name__ == "__main__":
    main(sys.argv[1:])
