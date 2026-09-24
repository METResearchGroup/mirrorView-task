"""Build RESULTS.md ablation tables from rebuilt GEPA output artifacts.

Run from the repo root:

    PYTHONPATH=. uv run python experiments/predict_keep_remove_jev_gepa_2026_09_23/jev_gepa_rebuilt/summarize_results.py --ablation-ids R1_gepa_pair --baseline-test-f1 0.538
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parents[3]
_SCRIPT_DIR = str(Path(__file__).resolve().parent)
if sys.path and sys.path[0] == _SCRIPT_DIR:
    sys.path.pop(0)
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from experiments.predict_keep_remove_jev_gepa_2026_09_23.jev_gepa_rebuilt.constants import (
    ACCEPTANCE_LOG_FILENAME,
    DEV_SELECTION_FILENAME,
    GEPA_RESULT_FILENAME,
    GEPA_RUN_DIRNAME,
    OUTPUT_ROOT,
    REFLECTION_USAGE_JSONL,
    STOP_REASON_FILENAME,
    STUDY_COMPONENT_KEY,
)
from experiments.predict_keep_remove_jev_gepa_2026_09_23.jev_gepa_rebuilt.evaluate import (
    TEST_RESULTS_FILENAME,
)

STAGE_A_UNION_A1_ABLATION_ID = "A1_pair_study_prompt"
STAGE_A_UNION_A1_BASELINE_TEST_F1 = 0.538
REBUILT_GEPA_SECTION_HEADER = "## Rebuilt GEPA (jev_gepa_rebuilt)"
DEFAULT_RESULTS_PATH = Path(
    "experiments/predict_keep_remove_jev_gepa_2026_09_23/RESULTS.md"
)
_FOUR_DP = "{:.4f}"


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def _ablation_dir(outputs_root: Path, ablation_id: str) -> Path:
    return outputs_root / ablation_id


def _reflection_usd_total(gepa_run_dir: Path, ablation_dir: Path) -> float:
    usage_rows = _read_jsonl(gepa_run_dir / REFLECTION_USAGE_JSONL)
    usage_total = sum(float(row.get("usd", 0.0) or 0.0) for row in usage_rows)
    if usage_total > 0:
        return usage_total
    dev_selection_path = ablation_dir / DEV_SELECTION_FILENAME
    if dev_selection_path.is_file():
        payload = _read_json(dev_selection_path)
        return float(payload.get("reflection_total_usd", 0.0) or 0.0)
    stop_reason_path = gepa_run_dir / STOP_REASON_FILENAME
    if stop_reason_path.is_file():
        payload = _read_json(stop_reason_path)
        return float(payload.get("reflection_cost_usd", 0.0) or 0.0)
    return 0.0


def _acceptance_rate(gepa_run_dir: Path) -> float | None:
    rows = _read_jsonl(gepa_run_dir / ACCEPTANCE_LOG_FILENAME)
    if not rows:
        return None
    accepted = sum(1 for row in rows if row.get("accepted") is True)
    rejected = sum(1 for row in rows if row.get("accepted") is False)
    decisions = accepted + rejected
    if decisions == 0:
        return None
    return accepted / decisions


def _iteration_count(gepa_result: dict[str, Any]) -> int | None:
    candidates = gepa_result.get("candidates")
    if not isinstance(candidates, list):
        return None
    return max(len(candidates) - 1, 0)


def _selected_prompt_chars(ablation_dir: Path, gepa_run_dir: Path) -> int | None:
    dev_selection_path = ablation_dir / DEV_SELECTION_FILENAME
    gepa_result_path = gepa_run_dir / GEPA_RESULT_FILENAME
    if not dev_selection_path.is_file() or not gepa_result_path.is_file():
        return None
    dev_selection = _read_json(dev_selection_path)
    gepa_result = _read_json(gepa_result_path)
    selected_idx = int(dev_selection["selected_candidate_idx"])
    candidates = gepa_result.get("candidates") or []
    if selected_idx < 0 or selected_idx >= len(candidates):
        return None
    candidate = candidates[selected_idx]
    if not isinstance(candidate, dict):
        return None
    instruction = candidate.get(STUDY_COMPONENT_KEY)
    if instruction is None:
        return None
    return len(str(instruction))


def load_ablation_summary(ablation_id: str, outputs_root: Path) -> dict[str, Any]:
    """Merge dev_selection, stop_reason, gepa_result, test_results, reflection totals.

    Parameters
    ----------
    ablation_id
        Rebuilt ablation directory name under ``outputs_root``.
    outputs_root
        Parent directory containing per-ablation output folders.

    Returns
    -------
    dict
        Row fields for ``format_results_markdown_table``.

    Raises
    ------
    FileNotFoundError
        When the ablation directory or ``test_results.json`` is missing.
    """
    ablation_dir = _ablation_dir(outputs_root, ablation_id)
    if not ablation_dir.is_dir():
        raise FileNotFoundError(f"missing ablation output dir {ablation_dir}")

    test_results_path = ablation_dir / TEST_RESULTS_FILENAME
    if not test_results_path.is_file():
        raise FileNotFoundError(f"missing test results at {test_results_path}")

    test_results = _read_json(test_results_path)
    test_f1 = float(test_results["metrics_at_dev_threshold"]["f1"])
    test_f1_at_0_5 = float(test_results["metrics_at_0_5"]["f1"])

    dev_a_f1: float | None = None
    dev_b_f1: float | None = None
    dev_selection_path = ablation_dir / DEV_SELECTION_FILENAME
    if dev_selection_path.is_file():
        dev_selection = _read_json(dev_selection_path)
        dev_a_f1 = float(dev_selection["dev_a_f1"])
        dev_b_f1 = float(dev_selection["dev_b_f1"])

    gepa_run_dir = ablation_dir / GEPA_RUN_DIRNAME
    stop_reason: str | None = None
    stop_reason_path = gepa_run_dir / STOP_REASON_FILENAME
    if stop_reason_path.is_file():
        stop_reason = str(_read_json(stop_reason_path).get("stop_reason") or "")

    iterations: int | None = None
    gepa_result_path = gepa_run_dir / GEPA_RESULT_FILENAME
    if gepa_result_path.is_file():
        iterations = _iteration_count(_read_json(gepa_result_path))

    accept_rate = _acceptance_rate(gepa_run_dir)
    reflection_usd = _reflection_usd_total(gepa_run_dir, ablation_dir)
    prompt_chars = _selected_prompt_chars(ablation_dir, gepa_run_dir)

    return {
        "ablation_id": ablation_id,
        "dev_a_f1": dev_a_f1,
        "dev_b_f1": dev_b_f1,
        "test_f1": test_f1,
        "test_f1_at_0_5": test_f1_at_0_5,
        "iterations": iterations,
        "accept_rate": accept_rate,
        "stop_reason": stop_reason,
        "reflection_usd": reflection_usd,
        "prompt_chars": prompt_chars,
    }


def collect_ablation_summaries(
    ablation_ids: list[str],
    outputs_root: Path,
) -> list[dict[str, Any]]:
    """Load summaries for ablations that have output directories on disk."""
    rows: list[dict[str, Any]] = []
    for ablation_id in ablation_ids:
        ablation_dir = _ablation_dir(outputs_root, ablation_id)
        if not ablation_dir.is_dir():
            continue
        rows.append(load_ablation_summary(ablation_id, outputs_root))
    return rows


def _format_optional_float(value: float | None) -> str:
    if value is None:
        return "—"
    return _FOUR_DP.format(value)


def _format_accept_rate(value: float | None) -> str:
    if value is None:
        return "—"
    return _FOUR_DP.format(value)


def _format_usd(value: float | None) -> str:
    if value is None:
        return "—"
    return f"{value:.2f}"


def _format_int(value: int | None) -> str:
    if value is None:
        return "—"
    return str(value)


def format_results_markdown_table(
    rows: list[dict[str, Any]],
    baseline_a1_test_f1: float,
) -> str:
    """Markdown table for RESULTS.md section.

    Parameters
    ----------
    rows
        Summaries from ``load_ablation_summary`` / ``collect_ablation_summaries``.
    baseline_a1_test_f1
        Union cohort Stage A A1 test F1 reference (default 0.538).

    Returns
    -------
    str
        Markdown table including the read-only A1 baseline row.
    """
    header = (
        "| Ablation | dev-A F1 | dev-B F1 | test F1 | test F1 @0.5 | "
        "iterations | accept rate | stop reason | reflection USD | prompt chars |"
    )
    separator = (
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |"
    )
    table_rows = [
        "| "
        f"{STAGE_A_UNION_A1_ABLATION_ID} | — | — | {_FOUR_DP.format(baseline_a1_test_f1)} | "
        "— | — | — | baseline | — | — |"
    ]
    for row in rows:
        table_rows.append(
            "| "
            f"{row['ablation_id']} | "
            f"{_format_optional_float(row.get('dev_a_f1'))} | "
            f"{_format_optional_float(row.get('dev_b_f1'))} | "
            f"{_format_optional_float(row.get('test_f1'))} | "
            f"{_format_optional_float(row.get('test_f1_at_0_5'))} | "
            f"{_format_int(row.get('iterations'))} | "
            f"{_format_accept_rate(row.get('accept_rate'))} | "
            f"{row.get('stop_reason') or '—'} | "
            f"{_format_usd(row.get('reflection_usd'))} | "
            f"{_format_int(row.get('prompt_chars'))} |"
        )
    return "\n".join([header, separator, *table_rows]) + "\n"


def _headline_for_rows(rows: list[dict[str, Any]], baseline_a1_test_f1: float) -> str:
    if not rows:
        return (
            f"No rebuilt ablations scored yet; union A1 baseline test F1 is "
            f"**{_FOUR_DP.format(baseline_a1_test_f1)}**."
        )
    best = max(rows, key=lambda row: float(row["test_f1"]))
    beats = float(best["test_f1"]) > baseline_a1_test_f1
    verdict = "beats" if beats else "does not beat"
    return (
        f"Best rebuilt ablation **{best['ablation_id']}** {verdict} union "
        f"A1 test F1 **{_FOUR_DP.format(baseline_a1_test_f1)}** at the dev-A "
        f"threshold (test F1 **{_FOUR_DP.format(float(best['test_f1']))}**)."
    )


def format_rebuilt_gepa_section(
    rows: list[dict[str, Any]],
    baseline_a1_test_f1: float,
) -> str:
    """Headline plus ablation table for RESULTS.md."""
    headline = _headline_for_rows(rows, baseline_a1_test_f1)
    table = format_results_markdown_table(rows, baseline_a1_test_f1)
    return f"{REBUILT_GEPA_SECTION_HEADER}\n\n{headline}\n\n{table}"


def _upsert_results_section(results_path: Path, section_markdown: str) -> None:
    if results_path.is_file():
        existing = results_path.read_text(encoding="utf-8")
    else:
        existing = ""
    pattern = re.compile(
        rf"{re.escape(REBUILT_GEPA_SECTION_HEADER)}.*?(?=\n## |\Z)",
        re.DOTALL,
    )
    if pattern.search(existing):
        updated = pattern.sub(section_markdown.rstrip() + "\n\n", existing, count=1)
    else:
        anchor = "## Stage A on Part 2 + Part 3 union"
        if anchor in existing:
            parts = existing.split(anchor, maxsplit=1)
            updated = parts[0] + anchor + parts[1] + "\n\n" + section_markdown.rstrip() + "\n"
        else:
            updated = existing.rstrip() + "\n\n" + section_markdown.rstrip() + "\n"
    results_path.parent.mkdir(parents=True, exist_ok=True)
    results_path.write_text(updated, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Summarize rebuilt GEPA ablation outputs.")
    parser.add_argument(
        "--ablation-ids",
        nargs="+",
        required=True,
        help="Ablation directory names under outputs/",
    )
    parser.add_argument(
        "--outputs-root",
        type=Path,
        default=OUTPUT_ROOT,
        help="Root directory containing per-ablation output folders",
    )
    parser.add_argument(
        "--baseline-test-f1",
        type=float,
        default=STAGE_A_UNION_A1_BASELINE_TEST_F1,
        help="Union Stage A A1 test F1 reference",
    )
    parser.add_argument(
        "--write-results-md",
        action="store_true",
        help="Upsert the Rebuilt GEPA section into RESULTS.md",
    )
    parser.add_argument(
        "--results-path",
        type=Path,
        default=DEFAULT_RESULTS_PATH,
        help="RESULTS.md path for --write-results-md",
    )
    args = parser.parse_args()

    rows = collect_ablation_summaries(args.ablation_ids, args.outputs_root)
    section = format_rebuilt_gepa_section(rows, args.baseline_test_f1)
    if args.write_results_md:
        _upsert_results_section(args.results_path, section)
    print(section, end="")


if __name__ == "__main__":
    main()
