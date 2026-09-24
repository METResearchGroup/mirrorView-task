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
from experiments.predict_keep_remove_jev_gepa_2026_09_23.shared.artifacts import (  # noqa: E402
    upload_under_prefix,
)
from experiments.predict_keep_remove_jev_gepa_2026_09_23.shared.wandb_tracking import (  # noqa: E402
    WandbRunSpec,
    init_run,
    log_artifact,
)
from lib.constants import REPO_ROOT

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
    payload = {
        "cluster": cluster_summary,
        "criteria": criteria_summary,
    }
    summary_path = output_dir / "analysis_summary.json"
    summary_path.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
    return summary_path


def append_results_analysis_section(*, results_path: Path, summary: dict[str, Any]) -> None:
    """Append the eight key questions section to RESULTS.md."""
    criteria = summary["criteria"]
    cluster = summary["cluster"]
    b1_summary = criteria["per_ablation"].get("B1_gepa_pair", {})
    total_gepa = criteria.get("total_gepa_criteria", 0)
    total_matched = criteria.get("total_matched", 0)
    total_novel = criteria.get("total_novel", 0)

    a1_original = cluster["models"]["A1"]["original"]
    a1_mirror = cluster["models"]["A1"]["mirror"]
    b1_original = cluster["models"]["B1"]["original"]
    b1_mirror = cluster["models"]["B1"]["mirror"]

    section = f"""
## Analysis

### Q1. Jev baseline vs trivial baselines
A1 test F1 **0.5267** beats keep-all (**0.0000**), remove-all (**0.3512**), and prevalence-random (**0.2116**, std **0.0143**). See Stage A table.

### Q2. GEPA improvement and cost
B1 test F1 **0.5484** vs A1 **0.5267** (delta **+0.0217**). B1-T test F1 **0.5635** at reflection cost **unknown** vs B1 **unknown**. See Stage B and spend table.

### Q3. Which text carries signal (pair vs original vs mirror)
| Arm | Test F1 |
| --- | --- |
| A1 pair | 0.5267 |
| A2 original | 0.4987 |
| A3 mirror | 0.5201 |
| B2 original-trained | 0.5372 |
| B3 mirror-trained | 0.5536 |
Transfer: B1 on original **0.3131**, B1 on mirror **0.2000**.

### Q4. Errors by stance and toxicity
Stage A subgroup tables show higher A1 test F1 on left stance (**0.5466**) than right (**0.4899**), and on high-toxicity posts (**0.6860**) vs low-toxicity (**0.1515**). Cluster summaries: A1 original errors **{a1_original.get('n_errors', 0)}** (label **{a1_original.get('error_kind_counts', {}).get('label_error', 0)}**, grouping **{a1_original.get('error_kind_counts', {}).get('grouping_error', 0)}**); A1 mirror **{a1_mirror.get('n_errors', 0)}**; B1 original **{b1_original.get('n_errors', 0)}**; B1 mirror **{b1_mirror.get('n_errors', 0)}**. See `analysis/outputs/cluster_errors/**/topic_summary.json`.

### Q5. P(remove) vs human disagreement
Spearman rho on full cohort: A1 **0.4927** (see Stage A).

### Q6. GEPA prompt transfer across views
See Stage B transfer table: B1 pair prompt collapses on original (**0.3131**) and mirror (**0.2000**); B2→mirror **0.5444** and B3→original **0.5523** stay near in-domain scores.

### Q7. GEPA criteria vs human-mined criteria
`analysis/outputs/criteria/comparison_summary.csv`: **{total_gepa}** GEPA atomic criteria across five ablations, **{total_matched}** matched to `KEEP_REMOVE_FEATURES_ADDENDUM` by conservative synonym rules, **{total_novel}** novel. B1 alone: **{b1_summary.get('gepa_criteria_count', 0)}** criteria, **{b1_summary.get('matched_count', 0)}** matched, **{b1_summary.get('novel_count', 0)}** novel. Held-out spot-check rows in `analysis/outputs/criteria/*_spot_check.csv`.

### Q8. Latency percentiles (batch 10)
A1 per-request p50 **369.8** ms, p90 **687.5** ms, p99 **1547.4** ms; per-post p50 **37.0** ms (Stage A latency table).

### Error clustering summary
K-means (k=5,10) then BERTopic on MiniLM embeddings for A1 and B1 test FN/FP, original and mirror clustered separately. Outputs: `analysis/outputs/cluster_errors/` (`cluster_assignments.parquet`, `topic_summary.json`, `spot_checks.csv`).
"""
    existing = results_path.read_text(encoding="utf-8")
    if "## Analysis" in existing:
        prefix = existing.split("## Analysis", maxsplit=1)[0].rstrip()
        results_path.write_text(prefix + section, encoding="utf-8")
        return
    results_path.write_text(existing.rstrip() + section, encoding="utf-8")


def upload_analysis_outputs(*, output_dir: Path, prefix: str = S3_PREFIX) -> int:
    """Upload all files under output_dir to S3."""
    uploaded = 0
    for path in output_dir.rglob("*"):
        if path.is_file():
            upload_under_prefix(path, prefix.rstrip("/"))
            uploaded += 1
    return uploaded


def log_wandb_analysis(*, cluster_summary: dict[str, Any], criteria_summary: dict[str, Any]) -> None:
    """Log analysis run to Wandb with group analysis and job_type analyze."""
    run = init_run(
        WandbRunSpec(
            group="analysis",
            name="step8_error_clustering_and_criteria_mining",
            job_type="analyze",
            config={
                "cluster_arms_written": cluster_summary.get("cluster_arms_written", 0),
                "criteria_ablations": criteria_summary.get("ablations_processed", 0),
                "total_gepa_criteria": criteria_summary.get("total_gepa_criteria", 0),
                "total_matched_criteria": criteria_summary.get("total_matched", 0),
            },
        )
    )
    summary_path = OUTPUT_ROOT / "analysis_summary.json"
    if summary_path.is_file():
        log_artifact(run, summary_path, name="analysis_summary", artifact_type="analysis")
    run.log(
        {
            "cluster_arms_written": cluster_summary.get("cluster_arms_written", 0),
            "criteria_ablations": criteria_summary.get("ablations_processed", 0),
            "total_gepa_criteria": criteria_summary.get("total_gepa_criteria", 0),
            "total_matched_criteria": criteria_summary.get("total_matched", 0),
        }
    )
    run.finish()


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
        "summary_path": str(summary_path.relative_to(REPO_ROOT)),
    }
    append_results_analysis_section(results_path=RESULTS_PATH, summary=combined)
    log_wandb_analysis(cluster_summary=cluster_summary, criteria_summary=criteria_summary)
    uploaded = upload_analysis_outputs(output_dir=output_dir)

    print(
        f"cluster_errors_written={cluster_summary.get('cluster_arms_written', 0)} "
        f"criteria_ablations={criteria_summary.get('ablations_processed', 0)} "
        f"s3_files_uploaded={uploaded} "
        "wandb_group=analysis job_type=analyze "
        "results_section=appended"
    )


if __name__ == "__main__":
    main()
