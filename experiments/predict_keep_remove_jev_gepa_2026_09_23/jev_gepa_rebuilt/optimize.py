"""GEPA optimize runner for rebuilt union cohort runs.

Run from the repo root:

    PYTHONPATH=. uv run python experiments/predict_keep_remove_jev_gepa_2026_09_23/jev_gepa_rebuilt/optimize.py --ablation-id R1_gepa_pair --smoke --max-metric-calls 120

``max_metric_calls`` and ``result.total_metric_calls`` count **posts scored** by Jev
(the adapter reports post counts per batch, not HTTP requests).
"""

from __future__ import annotations

import argparse
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

from experiments.predict_keep_remove_jev_gepa_2026_09_23.jev_gepa_rebuilt.adapter import (
    JevGepaRebuiltAdapter,
    ScoreMode,
    ViewName,
    default_seed_candidate,
)
from experiments.predict_keep_remove_jev_gepa_2026_09_23.jev_gepa_rebuilt.constants import (
    DEFAULT_MAX_METRIC_CALLS,
    GEPA_SEED,
    HALF_BUDGET_MAX_METRIC_CALLS,
    OUTPUT_ROOT,
    REFLECTION_MINIBATCH_SIZE,
    VAL_SUBSAMPLE_SIZE,
    WANDB_GROUP,
)
from experiments.predict_keep_remove_jev_gepa_2026_09_23.jev_gepa_rebuilt.policies.error_focused_sampler import (
    ErrorFocusedBatchSampler,
)
from experiments.predict_keep_remove_jev_gepa_2026_09_23.jev_gepa_rebuilt.policies.hard_label_acceptance import (
    HardLabelMarginAcceptance,
)
from experiments.predict_keep_remove_jev_gepa_2026_09_23.jev_gepa_rebuilt.policies.val_subsample_on_accept import (
    ValSubsampleOnAcceptPolicy,
)
from experiments.predict_keep_remove_jev_gepa_2026_09_23.jev_gepa_rebuilt.splits import load_gepa_union_splits
from experiments.predict_keep_remove_jev_gepa_2026_09_23.shared.rate_limiter import RequestStartLimiter
from experiments.predict_keep_remove_jev_gepa_2026_09_23.shared.wandb_tracking import WandbRunSpec, init_run

SMOKE_VAL_SUBSAMPLE_SIZE = 20
SMOKE_DEFAULT_MAX_METRIC_CALLS = 120
DEFAULT_RATE_CAP_PER_MIN = 200
GEPA_RUN_DIRNAME = "gepa_run"

ABLATION_IDS = (
    "R1_gepa_pair",
    "R2_majority_weighted",
    "R3_gepa_pair_terra",
    "R4_gepa_multi_component",
    "R5_gepa_original",
    "R6_gepa_mirror",
    "R7_plain_majority",
)

ABLATION_REGISTRY: dict[str, dict[str, object]] = {
    "R1_gepa_pair": {
        "view": "pair",
        "score_mode": "label_certainty",
        "reflection_lm": "openai/gpt-6-luna",
        "max_reflection_cost": 5.0,
    },
    "R2_majority_weighted": {
        "view": "pair",
        "score_mode": "majority_weighted",
        "reflection_lm": "openai/gpt-6-luna",
        "max_reflection_cost": 5.0,
    },
    "R3_gepa_pair_terra": {
        "view": "pair",
        "score_mode": "label_certainty",
        "reflection_lm": "openai/gpt-5.6-terra",
        "max_reflection_cost": 40.0,
    },
    "R4_gepa_multi_component": {
        "view": "pair",
        "score_mode": "label_certainty",
        "reflection_lm": "openai/gpt-6-luna",
        "max_reflection_cost": 5.0,
    },
    "R5_gepa_original": {
        "view": "original",
        "score_mode": "label_certainty",
        "reflection_lm": "openai/gpt-6-luna",
        "max_reflection_cost": 2.5,
        "max_metric_calls": HALF_BUDGET_MAX_METRIC_CALLS,
    },
    "R6_gepa_mirror": {
        "view": "mirror",
        "score_mode": "label_certainty",
        "reflection_lm": "openai/gpt-6-luna",
        "max_reflection_cost": 2.5,
        "max_metric_calls": HALF_BUDGET_MAX_METRIC_CALLS,
    },
    "R7_plain_majority": {
        "view": "pair",
        "score_mode": "plain_majority",
        "reflection_lm": "openai/gpt-6-luna",
        "max_reflection_cost": 5.0,
    },
}


@dataclass(frozen=True)
class OptimizeConfig:
    """Resolved GEPA optimization run for one rebuilt ablation."""

    ablation_id: str
    view: ViewName
    score_mode: ScoreMode
    reflection_lm: str
    max_reflection_cost: float
    max_metric_calls: int
    seed: int
    run_dir: Path
    val_subsample_size: int
    rate_cap_per_min: int = DEFAULT_RATE_CAP_PER_MIN


def resolve_ablation_config(ablation_id: str, *, smoke: bool = False) -> OptimizeConfig:
    """Build OptimizeConfig from the ablation registry."""
    try:
        entry = ABLATION_REGISTRY[ablation_id]
    except KeyError as exc:
        raise ValueError(f"unknown ablation_id: {ablation_id}") from exc
    run_dir = OUTPUT_ROOT / ablation_id / GEPA_RUN_DIRNAME
    max_metric_calls = int(entry.get("max_metric_calls", DEFAULT_MAX_METRIC_CALLS))
    val_subsample_size = SMOKE_VAL_SUBSAMPLE_SIZE if smoke else VAL_SUBSAMPLE_SIZE
    return OptimizeConfig(
        ablation_id=ablation_id,
        view=str(entry["view"]),  # type: ignore[arg-type]
        score_mode=str(entry["score_mode"]),  # type: ignore[arg-type]
        reflection_lm=str(entry["reflection_lm"]),
        max_reflection_cost=float(entry["max_reflection_cost"]),
        max_metric_calls=max_metric_calls,
        seed=GEPA_SEED,
        run_dir=run_dir,
        val_subsample_size=val_subsample_size,
    )


def run_optimize(config: OptimizeConfig, *, smoke: bool = False) -> GEPAResult:
    """Run GEPA with rebuilt policies and Wandb tracking.

    Parameters
    ----------
    config
        Resolved ablation configuration.
    smoke
        When True, uses smoke val subsample size (20 posts on accept).

    Returns
    -------
    GEPAResult
        GEPA optimization result (post budget in ``total_metric_calls``).
    """
    trainset, valset = load_gepa_union_splits()
    seed_candidate = default_seed_candidate(config.view)
    rate_limiter = RequestStartLimiter(config.rate_cap_per_min)
    adapter = JevGepaRebuiltAdapter(
        view=config.view,
        score_mode=config.score_mode,
        rate_limiter=rate_limiter,
    )
    batch_sampler = ErrorFocusedBatchSampler(
        minibatch_size=REFLECTION_MINIBATCH_SIZE,
        gepa_seed=config.seed,
    )
    val_evaluation_policy = ValSubsampleOnAcceptPolicy(
        subsample_size=config.val_subsample_size,
        gepa_seed=config.seed,
    )
    acceptance_criterion = HardLabelMarginAcceptance()

    wandb_run = init_run(
        WandbRunSpec(
            group=WANDB_GROUP,
            name=config.ablation_id,
            job_type="optimize",
            config={
                "ablation_id": config.ablation_id,
                "view": config.view,
                "score_mode": config.score_mode,
                "reflection_lm": config.reflection_lm,
                "max_metric_calls": config.max_metric_calls,
                "posts_scored": "max_metric_calls and total_metric_calls count Jev posts scored",
                "smoke": smoke,
                "seed": config.seed,
                "val_subsample_size": config.val_subsample_size,
                "reflection_minibatch_size": REFLECTION_MINIBATCH_SIZE,
            },
        )
    )

    optimize_kwargs: dict[str, object] = {
        "seed_candidate": seed_candidate,
        "trainset": trainset,
        "valset": valset,
        "adapter": adapter,
        "reflection_lm": config.reflection_lm,
        "max_metric_calls": config.max_metric_calls,
        "max_reflection_cost": config.max_reflection_cost,
        "reflection_minibatch_size": REFLECTION_MINIBATCH_SIZE,
        "batch_sampler": batch_sampler,
        "val_evaluation_policy": val_evaluation_policy,
        "acceptance_criterion": acceptance_criterion,
        "use_merge": False,
        "candidate_selection_strategy": "pareto",
        "seed": config.seed,
        "run_dir": str(config.run_dir),
        "use_wandb": True,
        "wandb_attach_existing": True,
    }
    # Round-robin module_selector is R4 only (Step 5/6); single-component runs omit it.
    if config.ablation_id == "R4_gepa_multi_component":
        optimize_kwargs["module_selector"] = "round_robin"

    try:
        result = gepa.optimize(**optimize_kwargs)
        print(
            f"ablation_id={config.ablation_id} "
            f"total_metric_calls={result.total_metric_calls} "
            f"smoke={smoke}"
        )
        return result
    finally:
        wandb_run.finish()


def main(argv: list[str] | None = None) -> None:
    """CLI entrypoint for rebuilt GEPA optimization."""
    parser = argparse.ArgumentParser(description="Run rebuilt Jev GEPA prompt optimization")
    parser.add_argument("--ablation-id", required=True, choices=sorted(ABLATION_IDS))
    parser.add_argument("--smoke", action="store_true", help="Run tiny-budget smoke configuration")
    parser.add_argument(
        "--max-metric-calls",
        type=int,
        default=None,
        help="Override max_metric_calls for the run",
    )
    args = parser.parse_args(argv)
    config = resolve_ablation_config(args.ablation_id, smoke=args.smoke)
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
            val_subsample_size=config.val_subsample_size,
            rate_cap_per_min=config.rate_cap_per_min,
        )
    elif args.smoke:
        config = OptimizeConfig(
            ablation_id=config.ablation_id,
            view=config.view,
            score_mode=config.score_mode,
            reflection_lm=config.reflection_lm,
            max_reflection_cost=config.max_reflection_cost,
            max_metric_calls=SMOKE_DEFAULT_MAX_METRIC_CALLS,
            seed=config.seed,
            run_dir=config.run_dir,
            val_subsample_size=config.val_subsample_size,
            rate_cap_per_min=config.rate_cap_per_min,
        )
    run_optimize(config, smoke=args.smoke)


if __name__ == "__main__":
    main(sys.argv[1:])
