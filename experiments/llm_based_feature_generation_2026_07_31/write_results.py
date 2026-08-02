"""Write RESULTS.md from a completed 50% production run."""

from __future__ import annotations

import json
import pathlib
from typing import Any

from experiments.llm_based_feature_generation_2026_07_31.batching import FROZEN_SUBSET_CSV
from experiments.llm_based_feature_generation_2026_07_31.stage1 import DEFAULT_MODEL
from experiments.llm_based_feature_generation_2026_07_31.stage2 import load_stage1_results

EXPERIMENT_ROOT = pathlib.Path(__file__).resolve().parent
RESULTS_PATH = EXPERIMENT_ROOT / "RESULTS.md"
_METADATA_FILENAME = "metadata.json"


def _load_stage2_themes(stage2_dir: pathlib.Path) -> dict[str, Any]:
    themes: list[dict[str, Any]] = []
    cross_cutting: list[str] = []
    next_id = 1
    for path in sorted(stage2_dir.glob("*.json")):
        if path.name == _METADATA_FILENAME:
            continue
        payload = json.loads(path.read_text(encoding="utf-8"))
        shard_result = payload.get("result", {})
        for theme in shard_result.get("themes", []):
            renumbered = dict(theme)
            renumbered["id"] = next_id
            next_id += 1
            themes.append(renumbered)
        for theme in shard_result.get("cross_cutting_themes", []):
            if theme not in cross_cutting:
                cross_cutting.append(theme)
    if not themes:
        raise FileNotFoundError(f"No stage-2 theme results in {stage2_dir}")
    return {"themes": themes, "cross_cutting_themes": cross_cutting}


def _format_theme_table(themes: list[dict[str, Any]]) -> str:
    lines = [
        "| id | Theme | keep | remove |",
        "| -- | ----- | ---- | ------ |",
    ]
    for theme in themes:
        lines.append(
            f"| {theme['id']} | {theme['label']} | {theme['keep_count']} | {theme['remove_count']} |"
        )
    return "\n".join(lines)


def write_results_md(
    *,
    stage1_dir: pathlib.Path,
    stage2_dir: pathlib.Path,
    batch_count: int,
    model: str = DEFAULT_MODEL,
    sample_fraction: float = 0.50,
) -> pathlib.Path:
    """Generate RESULTS.md for a completed production run."""
    stage1_dir = stage1_dir.resolve()
    stage2_dir = stage2_dir.resolve()
    stage1_results = load_stage1_results(stage1_dir)
    stage2_result = _load_stage2_themes(stage2_dir)
    themes = stage2_result.get("themes", [])
    cross_cutting = stage2_result.get("cross_cutting_themes", [])

    keep_features = sum(
        len(row.get("result", {}).get("keep_features", [])) for row in stage1_results
    )
    remove_features = sum(
        len(row.get("result", {}).get("remove_features", [])) for row in stage1_results
    )

    cross_cutting_block = "\n".join(f"{index}. {theme}" for index, theme in enumerate(cross_cutting, 1))

    content = f"""# LLM feature generation — 50% production results

**Date:** 2026-08-01  
**Status:** Complete  
**Model:** `{model}`  
**Sample fraction:** {sample_fraction}  
**Frozen subset:** `{FROZEN_SUBSET_CSV.relative_to(EXPERIMENT_ROOT.parent.parent)}`

## Summary

Ran the two-stage pipeline on the frozen 50% Study Phase 2 Part 2 subset: **{batch_count}** stage-1 batches (10 keep + 10 remove each), **{keep_features}** keep features and **{remove_features}** remove features extracted, then **{len(themes)}** synthesized themes.

| Stage | Output directory |
| ----- | ---------------- |
| 1 — feature generation | `{stage1_dir.relative_to(EXPERIMENT_ROOT)}` |
| 2 — theme synthesis | `{stage2_dir.relative_to(EXPERIMENT_ROOT)}` |

## Themes

{_format_theme_table(themes)}

## Cross-cutting themes

{cross_cutting_block}

## Interpretation

Stage 1 used the six fixed category checklists (max 8 keep + 8 remove features per batch). Stage 2 aggregated all batch features into the theme list above. See per-batch JSON under the stage-1 output directory for feature-level detail.
"""
    RESULTS_PATH.write_text(content, encoding="utf-8")
    return RESULTS_PATH


def main() -> None:
    """CLI helper: write RESULTS.md from latest output dirs passed as env or args."""
    import argparse

    parser = argparse.ArgumentParser(description="Write RESULTS.md from production run outputs.")
    parser.add_argument("--stage1-dir", required=True)
    parser.add_argument("--stage2-dir", required=True)
    parser.add_argument("--batch-count", type=int, required=True)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--sample-fraction", type=float, default=0.50)
    args = parser.parse_args()
    path = write_results_md(
        stage1_dir=pathlib.Path(args.stage1_dir),
        stage2_dir=pathlib.Path(args.stage2_dir),
        batch_count=args.batch_count,
        model=args.model,
        sample_fraction=args.sample_fraction,
    )
    print(f"wrote {path}")


if __name__ == "__main__":
    main()
