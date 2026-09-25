"""Parse GEPA smoke artifacts and evaluate R1 / R4 pass criteria.

Run from the repo root:

    PYTHONPATH=. uv run pytest experiments/predict_keep_remove_jev_gepa_2026_09_23/jev_gepa_rebuilt/tests/test_smoke_checks.py -q
"""

from __future__ import annotations

import json
from pathlib import Path

from experiments.predict_keep_remove_jev_gepa_2026_09_23.jev_gepa_rebuilt.constants import (
    ACCEPTANCE_LOG_FILENAME,
    COMPONENT_UPDATE_LOG_FILENAME,
    DEV_SELECTION_FILENAME,
    GEPA_RESULT_FILENAME,
    GEPA_RUN_DIRNAME,
    R4_ROUND_ROBIN_COMPONENT_KEYS,
    REFLECTION_USAGE_JSONL,
    SMOKE_METRIC_CALLS,
    STOP_REASON_FILENAME,
)

MAX_R4_ITERATIONS_TO_CHECK = 8
MIN_R4_MUTATED_KEYS = 3


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _read_jsonl(path: Path) -> list[dict]:
    if not path.is_file():
        return []
    rows: list[dict] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def _reflection_usd_total(gepa_run_dir: Path, ablation_dir: Path) -> float:
    usage_rows = _read_jsonl(gepa_run_dir / REFLECTION_USAGE_JSONL)
    usage_total = sum(float(row.get("usd", 0.0) or 0.0) for row in usage_rows)
    if usage_total > 0:
        return usage_total
    dev_selection = ablation_dir / DEV_SELECTION_FILENAME
    if dev_selection.is_file():
        payload = _read_json(dev_selection)
        return float(payload.get("reflection_total_usd", 0.0) or 0.0)
    stop_reason = gepa_run_dir / STOP_REASON_FILENAME
    if stop_reason.is_file():
        payload = _read_json(stop_reason)
        return float(payload.get("reflection_cost_usd", 0.0) or 0.0)
    return 0.0


def _count_rejects(gepa_run_dir: Path, gepa_result: dict) -> int:
    acceptance_rows = _read_jsonl(gepa_run_dir / ACCEPTANCE_LOG_FILENAME)
    reject_count = sum(1 for row in acceptance_rows if not row.get("accepted", True))
    if reject_count > 0:
        return reject_count
    parents = gepa_result.get("parents") or []
    if len(parents) > 1:
        return 1
    stop_reason = gepa_run_dir / STOP_REASON_FILENAME
    if stop_reason.is_file():
        payload = _read_json(stop_reason)
        guard_rejects = payload.get("guard_reject_count")
        if isinstance(guard_rejects, int) and guard_rejects >= 1:
            return guard_rejects
    return 0


def assert_r1_smoke_pass(ablation_dir: Path) -> dict[str, object]:
    """Raise AssertionError unless R1 smoke artifacts satisfy Step 5 checks."""
    gepa_run_dir = ablation_dir / GEPA_RUN_DIRNAME
    result_path = gepa_run_dir / GEPA_RESULT_FILENAME
    if not result_path.is_file():
        raise AssertionError(f"missing {result_path}")

    gepa_result = _read_json(result_path)
    total_metric_calls = int(gepa_result.get("total_metric_calls") or 0)
    if total_metric_calls > SMOKE_METRIC_CALLS:
        raise AssertionError(
            f"total_metric_calls {total_metric_calls} exceeds smoke budget {SMOKE_METRIC_CALLS}"
        )

    stop_reason_path = gepa_run_dir / STOP_REASON_FILENAME
    if not stop_reason_path.is_file():
        raise AssertionError(f"missing {stop_reason_path}")

    reject_count = _count_rejects(gepa_run_dir, gepa_result)
    if reject_count < 1:
        raise AssertionError("expected at least one rejected proposal in smoke run")

    reflection_usd = _reflection_usd_total(gepa_run_dir, ablation_dir)
    if reflection_usd <= 0:
        raise AssertionError("expected non-zero reflection USD in smoke artifacts")

    num_iterations = int(gepa_result.get("num_iterations") or gepa_result.get("total_iterations") or 0)
    posts_per_iteration_estimate = (
        float(total_metric_calls) / num_iterations if num_iterations > 0 else None
    )

    return {
        "passed": True,
        "total_metric_calls": total_metric_calls,
        "reject_count": reject_count,
        "reflection_usd": reflection_usd,
        "posts_per_iteration_estimate": posts_per_iteration_estimate,
        "stop_reason": _read_json(stop_reason_path).get("stop_reason"),
    }


def write_r1_smoke_report(ablation_dir: Path, smoke_dir: Path, report: dict[str, object]) -> Path:
    """Persist R1 smoke report JSON under outputs/_smoke."""
    smoke_dir.mkdir(parents=True, exist_ok=True)
    path = smoke_dir / "r1_smoke_report.json"
    path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def evaluate_r4_round_robin_smoke(
    ablation_dir: Path,
    *,
    log_path: Path | None = None,
) -> dict[str, object]:
    """Return whether R4 component_update_log satisfies round-robin smoke criteria."""
    gepa_run_dir = ablation_dir / GEPA_RUN_DIRNAME
    path = log_path or (gepa_run_dir / COMPONENT_UPDATE_LOG_FILENAME)
    rows = _read_jsonl(path)
    if not rows:
        return {"passed": False, "reason": "missing component_update_log"}

    iteration_rows = [row for row in rows if int(row.get("iteration", -1)) >= 1]
    if not iteration_rows:
        return {"passed": False, "reason": "missing iteration rows"}

    seed_rows = [row for row in rows if int(row.get("iteration", -1)) == 0]
    seed_hash_by_key = {
        str(row["module_selected"]): str(row["keys_snapshot_hash"]) for row in seed_rows
    }

    window = iteration_rows[: min(MAX_R4_ITERATIONS_TO_CHECK, len(iteration_rows))]
    order = R4_ROUND_ROBIN_COMPONENT_KEYS
    cycling_ok = all(
        row.get("module_selected") == order[index % len(order)]
        for index, row in enumerate(window)
    )

    mutated_keys: set[str] = set()
    for row in window:
        module = str(row.get("module_selected", ""))
        snapshot_hash = str(row.get("keys_snapshot_hash", ""))
        seed_hash = seed_hash_by_key.get(module)
        if seed_hash is not None and snapshot_hash != seed_hash:
            mutated_keys.add(module)

    passed = cycling_ok and len(mutated_keys) >= MIN_R4_MUTATED_KEYS
    return {
        "passed": passed,
        "cycling_ok": cycling_ok,
        "mutated_key_count": len(mutated_keys),
        "mutated_keys": sorted(mutated_keys),
        "iterations_checked": len(window),
    }


def write_r4_smoke_passed(ablation_dir: Path, smoke_dir: Path) -> Path:
    """Evaluate R4 log and write outputs/_smoke/r4_smoke_passed.json."""
    result = evaluate_r4_round_robin_smoke(ablation_dir)
    smoke_dir.mkdir(parents=True, exist_ok=True)
    path = smoke_dir / "r4_smoke_passed.json"
    path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path
