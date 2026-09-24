"""Assemble RESULTS.md from analysis outputs and self-consistency scores.

Run from the repo root::

    PYTHONPATH=. uv run python -m experiments.llm_feature_generation_phase_2_part_3_2026_09_24.src.write_results \\
      --analysis-dir outputs/paired/analysis/<ts> \\
      --self-consistency outputs/shared/self_consistency/<ts>/scores.json \\
      --part2-map outputs/shared/part2_theme_map/<ts>/theme_map.csv
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from experiments.llm_feature_generation_phase_2_part_3_2026_09_24.src import constants, paths
from experiments.llm_feature_generation_phase_2_part_3_2026_09_24.src.constants import SELF_CONSISTENCY_THRESHOLD

PART2_MODEL_NAME = "gpt-5.4-nano"
PART3_MODEL_NAME = "gpt-6-luna"
CAVEAT_PROVISIONAL = "Labels are provisional LLM labels without human validation."


def load_self_consistency_flags(scores_path: Path | None) -> list[str]:
    """Return feature IDs below the self-consistency threshold."""
    if scores_path is None or not scores_path.is_file():
        return []
    payload = json.loads(scores_path.read_text(encoding="utf-8"))
    flagged: list[str] = []
    for feature_id, score in payload.get("per_feature", {}).items():
        if float(score) < SELF_CONSISTENCY_THRESHOLD:
            flagged.append(str(feature_id))
    flagged.extend(str(item) for item in payload.get("features_below_threshold", []))
    return sorted(set(flagged))


def render_results_markdown(
    analysis_dir: Path,
    flagged_features: list[str],
    part2_map_path: Path | None,
) -> str:
    """Build RESULTS.md body from analysis artifacts."""
    summary_path = analysis_dir / "summary_tables.md"
    summary_text = summary_path.read_text(encoding="utf-8") if summary_path.is_file() else ""
    lines = [
        "# LLM feature generation Phase 2 Part 3",
        "",
        "## Summary",
        "",
        summary_text.strip(),
        "",
        "## Caveats",
        "",
        f"- Part 2 used `{PART2_MODEL_NAME}`; Part 3 used `{PART3_MODEL_NAME}`.",
        f"- {CAVEAT_PROVISIONAL}",
        "",
        "## Self-consistency flags",
        "",
    ]
    if flagged_features:
        lines.extend(f"- `{feature_id}`" for feature_id in flagged_features)
    else:
        lines.append("- None below threshold.")
    lines.extend(["", "## Part 2 theme map", ""])
    if part2_map_path and part2_map_path.is_file():
        lines.append(f"Provisional rank-1 mapping: `{part2_map_path}`")
    lines.append("")
    return "\n".join(lines)


def write_results_file(
    analysis_dir: Path,
    scores_path: Path | None,
    part2_map_path: Path | None,
    results_path: Path,
) -> Path:
    """Write RESULTS.md beside the experiment root."""
    flagged = load_self_consistency_flags(scores_path)
    content = render_results_markdown(analysis_dir, flagged, part2_map_path)
    results_path.write_text(content, encoding="utf-8")
    return results_path


def main(argv: list[str] | None = None) -> None:
    """CLI entry to render RESULTS.md."""
    args = _parse_args(argv)
    analysis_dir = Path(args.analysis_dir)
    scores_path = Path(args.self_consistency) if args.self_consistency else None
    part2_map_path = Path(args.part2_map) if args.part2_map else None
    results_path = paths.EXPERIMENT_ROOT / "RESULTS.md"
    write_results_file(analysis_dir, scores_path, part2_map_path, results_path)
    print(f"Wrote {results_path}")


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Write RESULTS.md from analysis outputs.")
    parser.add_argument("--analysis-dir", required=True)
    parser.add_argument("--self-consistency", default=None)
    parser.add_argument("--part2-map", default=None)
    return parser.parse_args(argv)


if __name__ == "__main__":
    main()
