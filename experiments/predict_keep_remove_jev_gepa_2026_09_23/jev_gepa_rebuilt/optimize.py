"""GEPA optimize runner for rebuilt union cohort runs.

Run from the repo root:

    PYTHONPATH=. uv run python experiments/predict_keep_remove_jev_gepa_2026_09_23/jev_gepa_rebuilt/optimize.py --ablation-id R1_gepa_pair --smoke --max-metric-calls 120

``max_metric_calls`` and ``result.total_metric_calls`` count **posts scored** by Jev
(the adapter reports post counts per batch, not HTTP requests).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parents[3]
_SCRIPT_DIR = str(Path(__file__).resolve().parent)
if sys.path and sys.path[0] == _SCRIPT_DIR:
    sys.path.pop(0)
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from gepa.core.result import GEPAResult
from gepa.core.state import GEPAState
from gepa.proposer.base import CandidateProposal
import gepa

from experiments.predict_keep_remove_jev_gepa_2026_09_23.jev_gepa_rebuilt.adapter import (
    JevGepaRebuiltAdapter,
    ScoreMode,
    ViewName,
    default_seed_candidate,
)
from experiments.predict_keep_remove_jev_gepa_2026_09_23.jev_gepa_rebuilt.artifacts import upload_rebuilt
from experiments.predict_keep_remove_jev_gepa_2026_09_23.jev_gepa_rebuilt.constants import (
    ACCEPTANCE_LOG_FILENAME,
    CANDIDATE_DEV_SCORES_FILENAME,
    COMPONENT_UPDATE_LOG_FILENAME,
    DEFAULT_MAX_METRIC_CALLS,
    DEV_SELECTION_FILENAME,
    GEPA_RESULT_FILENAME,
    GEPA_SEED,
    HALF_BUDGET_MAX_METRIC_CALLS,
    OUTPUT_ROOT,
    R4_ROUND_ROBIN_COMPONENT_KEYS,
    R4_SEED_KEEP_CRITERIA,
    R4_SEED_MIRROR_NOTE,
    R4_SEED_REMOVE_CRITERIA,
    REFLECTION_MINIBATCH_SIZE,
    REFLECTION_USAGE_JSONL,
    SMOKE_METRIC_CALLS,
    SMOKE_OUTPUT_DIR,
    SMOKE_VAL_SUBSAMPLE_SIZE,
    STOP_REASON_FILENAME,
    TOP_ACCEPTED_CANDIDATES,
    VAL_SUBSAMPLE_SIZE,
    WANDB_GROUP,
)
from experiments.predict_keep_remove_jev_gepa_2026_09_23.jev_gepa_rebuilt.smoke_checks import (
    assert_r1_smoke_pass,
    write_r1_smoke_report,
    write_r4_smoke_passed,
)
from experiments.predict_keep_remove_jev_gepa_2026_09_23.jev_gepa_rebuilt.dev_ab import build_or_load_dev_ab_split
from experiments.predict_keep_remove_jev_gepa_2026_09_23.jev_gepa_rebuilt.guards import check_candidate_guards
from experiments.predict_keep_remove_jev_gepa_2026_09_23.jev_gepa_rebuilt.policies.val_subsample_on_accept import (
    PROPOSAL_REJECTED_KEY,
)
from experiments.predict_keep_remove_jev_gepa_2026_09_23.jev_gepa_rebuilt.reflection_logging import (
    make_reflection_lm_with_usage_log,
)
from experiments.predict_keep_remove_jev_gepa_2026_09_23.jev_gepa_rebuilt.selection import (
    filter_top10_val_dev_gap,
    list_accepted_candidate_indices,
    preselect_top_by_val_score,
    select_on_dev_ab,
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
from experiments.predict_keep_remove_jev_gepa_2026_09_23.jev_gepa_rebuilt.splits import (
    load_dev_instances,
    load_gepa_union_splits,
    load_train_post_texts,
)
from experiments.predict_keep_remove_jev_gepa_2026_09_23.shared.rate_limiter import RequestStartLimiter
from experiments.predict_keep_remove_jev_gepa_2026_09_23.shared.wandb_tracking import WandbRunSpec, init_run

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


def seed_candidate_for_ablation(ablation_id: str, view: ViewName) -> dict[str, str]:
    """Return GEPA seed candidate; R4 uses four round-robin component keys."""
    if ablation_id == "R4_gepa_multi_component":
        return {
            R4_ROUND_ROBIN_COMPONENT_KEYS[0]: default_seed_candidate(view)[
                R4_ROUND_ROBIN_COMPONENT_KEYS[0]
            ],
            "remove_criteria": R4_SEED_REMOVE_CRITERIA,
            "keep_criteria": R4_SEED_KEEP_CRITERIA,
            "mirror_note": R4_SEED_MIRROR_NOTE,
        }
    return default_seed_candidate(view)


class R4ComponentUpdateLogCallback:
    """Append round-robin module selection and key snapshot hashes for R4 smoke."""

    def __init__(self, log_path: Path) -> None:
        self._log_path = log_path
        self._log_path.parent.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _snapshot_hash(candidate: dict[str, str], module_selected: str) -> str:
        text = candidate.get(module_selected, "")
        return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]

    def on_proposal_start(self, event: dict[str, object]) -> None:
        iteration = int(event["iteration"])
        components = event.get("components") or []
        if not components:
            return
        module_selected = str(components[0])
        parent_candidate = event.get("parent_candidate") or {}
        if not isinstance(parent_candidate, dict):
            return
        record = {
            "iteration": iteration,
            "module_selected": module_selected,
            "keys_snapshot_hash": self._snapshot_hash(parent_candidate, module_selected),
        }
        with self._log_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record) + "\n")


def _finalize_smoke_artifacts(config: OptimizeConfig, result: GEPAResult) -> None:
    """Write Step 5 smoke reports under outputs/_smoke after a smoke run."""
    ablation_dir = config.run_dir.parent
    if config.ablation_id == "R1_gepa_pair":
        report = assert_r1_smoke_pass(ablation_dir)
        report["num_iterations"] = getattr(result, "num_iterations", None)
        write_r1_smoke_report(ablation_dir, SMOKE_OUTPUT_DIR, report)
    if config.ablation_id == "R4_gepa_multi_component":
        write_r4_smoke_passed(ablation_dir, SMOKE_OUTPUT_DIR)


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


class GuardedHardLabelAcceptance:
    """Hard-label margin acceptance with train-text guards and JSONL logging."""

    def __init__(
        self,
        inner: HardLabelMarginAcceptance,
        *,
        train_post_texts: list[str],
        acceptance_log_path: Path,
        wandb_run: Any | None,
    ) -> None:
        self._inner = inner
        self._train_post_texts = train_post_texts
        self._acceptance_log_path = acceptance_log_path
        self._wandb_run = wandb_run
        self._acceptance_log_path.parent.mkdir(parents=True, exist_ok=True)

    def _append_log(self, candidate_idx: int, accepted: bool, reason: str | None) -> None:
        row = {"candidate_idx": candidate_idx, "accepted": accepted, "reason": reason}
        with self._acceptance_log_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(row) + "\n")
        if self._wandb_run is not None:
            self._wandb_run.log(
                {
                    "acceptance/accepted": int(accepted),
                    "acceptance/candidate_idx": candidate_idx,
                }
            )

    def should_accept(self, proposal: CandidateProposal, state: GEPAState) -> bool:
        state.adapter_state[PROPOSAL_REJECTED_KEY] = False
        candidate_idx = len(state.program_candidates)
        if not self._inner.should_accept(proposal, state):
            state.adapter_state[PROPOSAL_REJECTED_KEY] = True
            reason = self._inner.reject_reason(proposal, state)
            self._append_log(candidate_idx, False, reason)
            return False
        guard = check_candidate_guards(
            proposal.candidate,
            train_post_texts=self._train_post_texts,
        )
        if not guard.ok:
            state.adapter_state[PROPOSAL_REJECTED_KEY] = True
            self._append_log(candidate_idx, False, guard.reason)
            return False
        self._append_log(candidate_idx, True, None)
        return True

    def reject_reason(self, proposal: CandidateProposal, state: GEPAState) -> str:
        return self._inner.reject_reason(proposal, state)


def _write_json(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _read_acceptance_log(path: Path) -> list[dict]:
    if not path.is_file():
        return []
    rows: list[dict] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def _val_subsample_ids_by_idx(result: GEPAResult) -> dict[int, list[str]]:
    mapping: dict[int, list[str]] = {}
    for idx, subscores in enumerate(result.val_subscores):
        mapping[idx] = [str(key) for key in subscores.keys()]
    return mapping


def _detect_stop_reason(
    config: OptimizeConfig,
    result: GEPAResult,
    reflection_lm: Any,
) -> str:
    reasons: list[str] = []
    if result.total_metric_calls is not None and result.total_metric_calls >= config.max_metric_calls:
        reasons.append("max_metric_calls")
    reflection_cost = float(getattr(reflection_lm, "total_cost", 0.0) or 0.0)
    if reflection_cost >= config.max_reflection_cost:
        reasons.append("max_reflection_cost")
    if (config.run_dir / "gepa.stop").is_file():
        reasons.append("gepa.stop")
    if not reasons:
        return "unknown"
    if len(reasons) > 1:
        return "composite"
    return reasons[0]


def _persist_post_run_artifacts(
    config: OptimizeConfig,
    result: GEPAResult,
    reflection_lm: Any,
    *,
    selected_idx: int,
    threshold: float,
    dev_a_f1: float,
    dev_b_f1: float,
    top10_indices: list[int],
    candidate_rows: list[dict],
) -> None:
    config.run_dir.mkdir(parents=True, exist_ok=True)
    _write_json(config.run_dir / GEPA_RESULT_FILENAME, result.to_dict())
    stop_reason = _detect_stop_reason(config, result, reflection_lm)
    reflection_cost = float(getattr(reflection_lm, "total_cost", 0.0) or 0.0)
    _write_json(
        config.run_dir / STOP_REASON_FILENAME,
        {
            "stop_reason": stop_reason,
            "total_metric_calls": result.total_metric_calls,
            "reflection_cost_usd": reflection_cost,
            "max_reflection_cost_usd": config.max_reflection_cost,
        },
    )
    output_dir = config.run_dir.parent
    _write_json(
        output_dir / DEV_SELECTION_FILENAME,
        {
            "selected_candidate_idx": selected_idx,
            "threshold": threshold,
            "dev_a_f1": dev_a_f1,
            "dev_b_f1": dev_b_f1,
            "top10_candidate_indices": top10_indices,
            "reflection_total_usd": reflection_cost,
            "reflection_total_tokens_in": getattr(reflection_lm, "total_tokens_in", 0),
            "reflection_total_tokens_out": getattr(reflection_lm, "total_tokens_out", 0),
            "total_metric_calls": result.total_metric_calls,
        },
    )
    scores_path = output_dir / CANDIDATE_DEV_SCORES_FILENAME
    with scores_path.open("w", encoding="utf-8") as handle:
        for row in candidate_rows:
            handle.write(json.dumps(row) + "\n")
    upload_rebuilt(output_dir)
    upload_rebuilt(config.run_dir)


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
    build_or_load_dev_ab_split(seed=config.seed, write=True)
    trainset, valset = load_gepa_union_splits()
    val_inst_by_post_id = {instance.post_id: instance for instance in valset}
    dev_a = load_dev_instances(split="dev_a")
    dev_b = load_dev_instances(split="dev_b")
    train_post_texts = load_train_post_texts()
    seed_candidate = seed_candidate_for_ablation(config.ablation_id, config.view)
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
    acceptance_log_path = config.run_dir / ACCEPTANCE_LOG_FILENAME
    acceptance_criterion = GuardedHardLabelAcceptance(
        HardLabelMarginAcceptance(),
        train_post_texts=train_post_texts,
        acceptance_log_path=acceptance_log_path,
        wandb_run=None,
    )

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
    acceptance_criterion._wandb_run = wandb_run

    usage_jsonl_path = config.run_dir / REFLECTION_USAGE_JSONL
    reflection_lm = make_reflection_lm_with_usage_log(
        config.reflection_lm,
        usage_jsonl_path=usage_jsonl_path,
        wandb_run=wandb_run,
    )

    optimize_kwargs: dict[str, object] = {
        "seed_candidate": seed_candidate,
        "trainset": trainset,
        "valset": valset,
        "adapter": adapter,
        "reflection_lm": reflection_lm,
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
    callbacks: list[Any] = []
    if config.ablation_id == "R4_gepa_multi_component":
        optimize_kwargs["module_selector"] = "round_robin"
        log_path = config.run_dir / COMPONENT_UPDATE_LOG_FILENAME
        if log_path.is_file():
            log_path.unlink()
        callbacks.append(R4ComponentUpdateLogCallback(log_path))
    if callbacks:
        optimize_kwargs["callbacks"] = callbacks

    try:
        result = gepa.optimize(**optimize_kwargs)
        acceptance_log = _read_acceptance_log(acceptance_log_path)
        accepted_indices = list_accepted_candidate_indices(result, acceptance_log)
        top10 = preselect_top_by_val_score(result, accepted_indices, k=TOP_ACCEPTED_CANDIDATES)
        val_subsample_ids = _val_subsample_ids_by_idx(result)
        filtered = filter_top10_val_dev_gap(
            adapter,
            top10,
            result.candidates,
            dev_a,
            val_subsample_ids_by_idx=val_subsample_ids,
            val_inst_by_post_id=val_inst_by_post_id,
        )
        selection_pool = filtered if filtered else top10
        if not selection_pool:
            selection_pool = [0]
        selected_idx, threshold, dev_a_f1, dev_b_f1, candidate_rows = select_on_dev_ab(
            adapter,
            result.candidates,
            selection_pool,
            dev_a,
            dev_b,
        )
        for row in candidate_rows:
            idx = int(row["candidate_idx"])
            row["val_score"] = float(result.val_aggregate_scores[idx])
        _persist_post_run_artifacts(
            config,
            result,
            reflection_lm,
            selected_idx=selected_idx,
            threshold=threshold,
            dev_a_f1=dev_a_f1,
            dev_b_f1=dev_b_f1,
            top10_indices=top10,
            candidate_rows=candidate_rows,
        )
        wandb_run.log(
            {
                "selection/dev_a_f1": dev_a_f1,
                "selection/dev_b_f1": dev_b_f1,
                "selection/threshold": threshold,
                "reflection/total_usd": float(reflection_lm.total_cost),
            }
        )
        if smoke:
            _finalize_smoke_artifacts(config, result)
        print(
            f"ablation_id={config.ablation_id} "
            f"total_metric_calls={result.total_metric_calls} "
            f"dev_a_f1={dev_a_f1:.4f} "
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
            max_metric_calls=SMOKE_METRIC_CALLS,
            seed=config.seed,
            run_dir=config.run_dir,
            val_subsample_size=config.val_subsample_size,
            rate_cap_per_min=config.rate_cap_per_min,
        )
    run_optimize(config, smoke=args.smoke)


if __name__ == "__main__":
    main(sys.argv[1:])
