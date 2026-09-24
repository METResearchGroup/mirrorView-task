"""Orchestrate Step 8 analysis: clustering, criteria mining, Wandb, and S3 upload."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parents[3]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from experiments.predict_keep_remove_jev_gepa_2026_09_23.analysis.cluster_errors import (  # noqa: E402
    run_cluster_analysis,
)
from experiments.predict_keep_remove_jev_gepa_2026_09_23.analysis.mine_gepa_criteria import (  # noqa: E402
    run_criteria_mining,
)

EXPERIMENT_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_ROOT = EXPERIMENT_ROOT / "analysis" / "outputs"
RESULTS_PATH = EXPERIMENT_ROOT / "RESULTS.md"
S3_PREFIX = "experiments/predict_keep_remove_jev_gepa_2026_09_23/analysis/"


def write_analysis_summary_json(
    *,
    output_dir: Path,
    cluster_summary: dict[str, Any],
    criteria_summary: dict[str, Any],
) -> Path:
    """Write combined analysis summary JSON."""
    raise NotImplementedError


def append_results_analysis_section(*, results_path: Path, summary: dict[str, Any]) -> None:
    """Append the eight key questions section to RESULTS.md."""
    raise NotImplementedError


def upload_analysis_outputs(*, output_dir: Path, prefix: str = S3_PREFIX) -> int:
    """Upload all files under output_dir to S3."""
    raise NotImplementedError


def log_wandb_analysis(*, cluster_summary: dict[str, Any], criteria_summary: dict[str, Any]) -> None:
    """Log analysis run to Wandb with group analysis and job_type analyze."""
    raise NotImplementedError


def main(argv: list[str] | None = None) -> None:
    """Run clustering, criteria mining, summary writes, Wandb, and S3 upload."""
    parser = argparse.ArgumentParser(description="Run Step 8 analysis.")
    parser.parse_args(argv)

    output_dir = OUTPUT_ROOT
    output_dir.mkdir(parents=True, exist_ok=True)

    cluster_summary = run_cluster_analysis(output_dir=output_dir / "cluster_errors")
    criteria_summary = run_criteria_mining(output_dir=output_dir / "criteria")

    summary_path = write_analysis_summary_json(
        output_dir=output_dir,
        cluster_summary=cluster_summary,
        criteria_summary=criteria_summary,
    )
    combined = {
        "cluster": cluster_summary,
        "criteria": criteria_summary,
        "summary_path": str(summary_path),
    }
    append_results_analysis_section(results_path=RESULTS_PATH, summary=combined)
    log_wandb_analysis(cluster_summary=cluster_summary, criteria_summary=criteria_summary)
    upload_analysis_outputs(output_dir=output_dir)

    print(
        f"cluster_errors_written={cluster_summary.get('cluster_arms_written', 0)} "
        f"criteria_ablations={criteria_summary.get('ablations_processed', 0)} "
        "wandb_group=analysis job_type=analyze "
        "results_section=appended"
    )


if __name__ == "__main__":
    main()
