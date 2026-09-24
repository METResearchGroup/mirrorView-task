"""GEPA optimize runner for Jev keep/remove prompt optimization.

Run from the repo root:

    PYTHONPATH=. uv run python experiments/predict_keep_remove_jev_gepa_2026_09_23/jev_gepa/optimize.py --ablation-id B1_gepa_pair --smoke --max-metric-calls 60
"""

from __future__ import annotations

import argparse
import dataclasses
import json
import os
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
import gepa
import numpy as np
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
from experiments.predict_keep_remove_jev_gepa_2026_09_23.shared.rate_limiter import RequestStartLimiter
from experiments.predict_keep_remove_jev_gepa_2026_09_23.shared.secrets import get_openai_api_key
from experiments.predict_keep_remove_jev_gepa_2026_09_23.shared.splits import COHORT_PARQUET
from experiments.predict_keep_remove_jev_gepa_2026_09_23.shared.wandb_tracking import WandbRunSpec, init_run

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


def _subset_valset_for_smoke(valset: list[JevDataInst], seed: int) -> list[JevDataInst]:
    if len(valset) <= SMOKE_VAL_SUBSET_SIZE:
        return list(valset)
    rng = np.random.default_rng(seed)
    chosen_indices = rng.choice(len(valset), size=SMOKE_VAL_SUBSET_SIZE, replace=False)
    return [valset[int(index)] for index in sorted(chosen_indices.tolist())]


def _ensure_openai_api_key() -> None:
    if not os.environ.get("OPENAI_API_KEY", "").strip():
        os.environ["OPENAI_API_KEY"] = get_openai_api_key()


def _to_jsonable(value: object) -> object:
    if dataclasses.is_dataclass(value):
        return {
            field.name: _to_jsonable(getattr(value, field.name))
            for field in dataclasses.fields(value)
        }
    if isinstance(value, dict):
        return {str(key): _to_jsonable(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_to_jsonable(item) for item in value]
    if isinstance(value, tuple):
        return [_to_jsonable(item) for item in value]
    return value


def _write_json(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(_to_jsonable(payload), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _reflection_cost_usd(run: object) -> float:
    summary = getattr(run, "summary", None)
    if summary is None:
        return 0.0
    for key in ("reflection_cost_usd", "reflection/cost_usd", "total_reflection_cost"):
        value = summary.get(key)
        if value is not None:
            return float(value)
    return 0.0


def _persist_run_outputs(
    config: OptimizeConfig,
    result: GEPAResult,
    *,
    selected_idx: int,
    selected_candidate: dict[str, str],
    selected_dev_f1: float,
    reflection_cost_usd: float,
) -> Path:
    config.run_dir.mkdir(parents=True, exist_ok=True)
    _write_json(config.run_dir / GEPA_RESULT_FILENAME, result.to_dict())
    _write_json(config.run_dir / SELECTED_CANDIDATE_FILENAME, selected_candidate)
    dev_selection_path = config.run_dir.parent / DEV_SELECTION_FILENAME
    _write_json(
        dev_selection_path,
        {
            "selected_candidate_idx": selected_idx,
            "selected_dev_f1": selected_dev_f1,
            "gepa_best_idx": result.best_idx,
            "reflection_lm": config.reflection_lm,
            "reflection_cost_usd": reflection_cost_usd,
            "total_metric_calls": result.total_metric_calls,
        },
    )
    return dev_selection_path


def run_optimize(config: OptimizeConfig, *, smoke: bool = False) -> GEPAResult:
    """Run GEPA optimization with Wandb tracking and dev-F1 candidate selection."""
    _ensure_openai_api_key()
    trainset, valset, devset = load_gepa_splits()
    if smoke:
        valset = _subset_valset_for_smoke(valset, config.seed)
    seed_instruction = load_seed_instruction(config.ablation_id)
    seed_candidate = {"instruction": seed_instruction}
    rate_limiter = RequestStartLimiter(config.rate_cap_per_min)
    adapter = JevGepaAdapter(
        view=config.view,
        score_mode=config.score_mode,
        rate_limiter=rate_limiter,
    )
    wandb_run = init_run(
        WandbRunSpec(
            group="jev_gepa",
            name=config.ablation_id,
            job_type="optimize",
            config={
                "ablation_id": config.ablation_id,
                "view": config.view,
                "score_mode": config.score_mode,
                "reflection_lm": config.reflection_lm,
                "max_metric_calls": config.max_metric_calls,
                "smoke": smoke,
                "seed": config.seed,
            },
        )
    )
    try:
        result = gepa.optimize(
            seed_candidate=seed_candidate,
            trainset=trainset,
            valset=valset,
            adapter=adapter,
            reflection_lm=config.reflection_lm,
            max_reflection_cost=config.max_reflection_cost,
            reflection_minibatch_size=10,
            candidate_selection_strategy="pareto",
            use_merge=True,
            max_metric_calls=config.max_metric_calls,
            seed=config.seed,
            use_wandb=True,
            wandb_attach_existing=True,
            run_dir=str(config.run_dir),
        )
        selected_idx, selected_candidate, selected_dev_f1 = select_candidate_on_dev(
            result,
            devset=devset,
            adapter=adapter,
        )
        reflection_cost_usd = _reflection_cost_usd(wandb_run)
        _persist_run_outputs(
            config,
            result,
            selected_idx=selected_idx,
            selected_candidate=selected_candidate,
            selected_dev_f1=selected_dev_f1,
            reflection_cost_usd=reflection_cost_usd,
        )
        print(
            f"ablation_id={config.ablation_id} "
            f"total_metric_calls={result.total_metric_calls} "
            f"selected_dev_f1={selected_dev_f1:.4f}"
        )
        return result
    finally:
        wandb_run.finish()


def main(argv: list[str] | None = None) -> None:
    """CLI entrypoint for GEPA optimization runs."""
    parser = argparse.ArgumentParser(description="Run Jev GEPA prompt optimization")
    parser.add_argument("--ablation-id", required=True, choices=sorted(ABLATION_REGISTRY))
    parser.add_argument("--smoke", action="store_true", help="Run tiny-budget smoke configuration")
    parser.add_argument(
        "--max-metric-calls",
        type=int,
        default=None,
        help="Override max_metric_calls (smoke default 60)",
    )
    args = parser.parse_args(argv)
    config = resolve_ablation_config(args.ablation_id)
    if args.max_metric_calls is not None:
        config = OptimizeConfig(
            ablation_id=config.ablation_id,
            view=config.view,
            score_mode=config.score_mode,
            reflection_lm=config.reflection_lm,
            max_reflection_cost=config.max_reflection_cost,
            max_metric_calls=args.max_metric_calls,
            seed=config.seed,
            run_dir=config.run_dir,
            rate_cap_per_min=config.rate_cap_per_min,
        )
    elif args.smoke:
        config = OptimizeConfig(
            ablation_id=config.ablation_id,
            view=config.view,
            score_mode=config.score_mode,
            reflection_lm=config.reflection_lm,
            max_reflection_cost=config.max_reflection_cost,
            max_metric_calls=60,
            seed=config.seed,
            run_dir=config.run_dir,
            rate_cap_per_min=config.rate_cap_per_min,
        )
    run_optimize(config, smoke=args.smoke)


if __name__ == "__main__":
    main(sys.argv[1:])
