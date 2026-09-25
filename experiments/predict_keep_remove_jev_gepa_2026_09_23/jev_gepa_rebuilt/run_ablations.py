"""Launch rebuilt GEPA ablation optimize jobs in documented waves.

Run from the repo root:

    PYTHONPATH=. uv run python experiments/predict_keep_remove_jev_gepa_2026_09_23/jev_gepa_rebuilt/run_ablations.py --wave parallel_r1_r2_r3_r7
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[3]
_SCRIPT_DIR = str(Path(__file__).resolve().parent)
if sys.path and sys.path[0] == _SCRIPT_DIR:
    sys.path.pop(0)
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from experiments.predict_keep_remove_jev_gepa_2026_09_23.jev_gepa_rebuilt.constants import (
    DEFAULT_MAX_METRIC_CALLS,
    OUTPUT_ROOT,
    R4_SMOKE_PASSED_FILENAME,
    SMOKE_OUTPUT_DIR,
)
from experiments.predict_keep_remove_jev_gepa_2026_09_23.jev_gepa_rebuilt.optimize import ABLATION_REGISTRY

OPTIMIZE_SCRIPT = (
    _REPO_ROOT
    / "experiments/predict_keep_remove_jev_gepa_2026_09_23/jev_gepa_rebuilt/optimize.py"
)
STAGE_A_A1_TEST_F1_BAR = 0.538
WAVE_PARALLEL_R1_R2_R3_R7 = "parallel_r1_r2_r3_r7"
WAVE_R4 = "r4"
WAVE_R5_R6 = "r5_r6"
MAX_PARALLEL_FULL_BUDGET_JOBS = 5
RATE_CAP_NOTE = (
    "Each optimize subprocess uses RequestStartLimiter(200) req/min; "
    f"wave 1 runs at most {MAX_PARALLEL_FULL_BUDGET_JOBS} jobs (~1000 req/min combined)."
)

WAVE_ABLATIONS: dict[str, tuple[str, ...]] = {
    WAVE_PARALLEL_R1_R2_R3_R7: (
        "R1_gepa_pair",
        "R2_majority_weighted",
        "R3_gepa_pair_terra",
        "R7_plain_majority",
    ),
    WAVE_R4: ("R4_gepa_multi_component",),
    WAVE_R5_R6: ("R5_gepa_original", "R6_gepa_mirror"),
}


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def r4_smoke_passed(smoke_dir: Path = SMOKE_OUTPUT_DIR) -> bool:
    """Return True when the R4 round-robin smoke file records passed=true."""
    path = smoke_dir / R4_SMOKE_PASSED_FILENAME
    if not path.is_file():
        return False
    payload = _read_json(path)
    return bool(payload.get("passed"))


def r5_r6_gate_passed(outputs_root: Path = OUTPUT_ROOT) -> tuple[bool, float]:
    """Return whether R1 dev-B F1 strictly exceeds the Stage A A1 test F1 bar."""
    dev_selection_path = outputs_root / "R1_gepa_pair" / "dev_selection.json"
    if not dev_selection_path.is_file():
        return False, float("nan")
    dev_b_f1 = float(_read_json(dev_selection_path)["dev_b_f1"])
    return dev_b_f1 > STAGE_A_A1_TEST_F1_BAR, dev_b_f1


def write_r5_r6_skipped(dev_b_f1: float, smoke_dir: Path = SMOKE_OUTPUT_DIR) -> Path:
    """Persist skip reason when the R5/R6 gate does not pass."""
    smoke_dir.mkdir(parents=True, exist_ok=True)
    path = smoke_dir / "r5_r6_skipped.json"
    payload = {
        "dev_b_f1": dev_b_f1,
        "stage_a_a1_test_f1_bar": STAGE_A_A1_TEST_F1_BAR,
        "skipped_ablations": list(WAVE_ABLATIONS[WAVE_R5_R6]),
    }
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def _max_metric_calls_for_ablation(ablation_id: str) -> int:
    entry = ABLATION_REGISTRY[ablation_id]
    return int(entry.get("max_metric_calls", DEFAULT_MAX_METRIC_CALLS))


def _launch_optimize(ablation_id: str) -> subprocess.Popen[str]:
    max_metric_calls = _max_metric_calls_for_ablation(ablation_id)
    command = [
        "uv",
        "run",
        "python",
        str(OPTIMIZE_SCRIPT),
        "--ablation-id",
        ablation_id,
        "--max-metric-calls",
        str(max_metric_calls),
    ]
    env = os.environ.copy()
    env["PYTHONPATH"] = "."
    process = subprocess.Popen(
        command,
        cwd=str(_REPO_ROOT),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    print(f"started ablation_id={ablation_id} pid={process.pid} max_metric_calls={max_metric_calls}")
    return process


def run_wave(wave: str) -> list[subprocess.Popen[str]]:
    """Start subprocess optimize jobs for a named wave."""
    if wave == WAVE_R4 and not r4_smoke_passed():
        print(
            "Refusing to start R4: round-robin smoke did not pass "
            f"(see {SMOKE_OUTPUT_DIR / R4_SMOKE_PASSED_FILENAME})."
        )
        raise SystemExit(1)

    if wave == WAVE_R5_R6:
        gate_ok, dev_b_f1 = r5_r6_gate_passed()
        if not gate_ok:
            skipped_path = write_r5_r6_skipped(dev_b_f1)
            print(
                f"R5/R6 skipped: R1 dev_b_f1={dev_b_f1} is not strictly greater than "
                f"{STAGE_A_A1_TEST_F1_BAR}; wrote {skipped_path}"
            )
            raise SystemExit(0)

    try:
        ablation_ids = WAVE_ABLATIONS[wave]
    except KeyError as exc:
        raise ValueError(f"unknown wave: {wave}") from exc

    print(RATE_CAP_NOTE)
    return [_launch_optimize(ablation_id) for ablation_id in ablation_ids]


def main(argv: list[str] | None = None) -> None:
    """CLI entrypoint for parallel ablation launches."""
    parser = argparse.ArgumentParser(description="Launch rebuilt GEPA ablation waves")
    parser.add_argument(
        "--wave",
        required=True,
        choices=sorted(WAVE_ABLATIONS),
        help="Which ablation wave to start",
    )
    args = parser.parse_args(argv)
    run_wave(args.wave)


if __name__ == "__main__":
    main(sys.argv[1:])
