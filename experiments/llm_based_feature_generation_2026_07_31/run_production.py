"""Run the 50% production pipeline and write RESULTS.md."""

from __future__ import annotations

import pathlib

from experiments.llm_based_feature_generation_2026_07_31.main import run_pipeline
from experiments.llm_based_feature_generation_2026_07_31.stage1 import DEFAULT_MODEL
from experiments.llm_based_feature_generation_2026_07_31.write_results import write_results_md

EXPERIMENT_ROOT = pathlib.Path(__file__).resolve().parent
DONE_MARKER = EXPERIMENT_ROOT / ".production_complete"


def main() -> int:
    """Execute stage 1 + stage 2 on the frozen 50% subset, then write RESULTS.md."""
    result = run_pipeline(
        sample_fraction=0.50,
        seed=42,
        keep_per_batch=10,
        remove_per_batch=10,
        model=DEFAULT_MODEL,
        exclude_ids_from=None,
        stage1_only=False,
        stage2_only=False,
        stage1_dir=None,
    )
    stage1_dir = result.get("stage1_dir")
    stage2_dir = result.get("stage2_dir")
    if not isinstance(stage1_dir, pathlib.Path) or not isinstance(stage2_dir, pathlib.Path):
        raise RuntimeError("production run missing output directories")

    write_results_md(
        stage1_dir=stage1_dir,
        stage2_dir=stage2_dir,
        batch_count=int(result["batch_count"]),
        model=DEFAULT_MODEL,
        sample_fraction=0.50,
    )
    DONE_MARKER.write_text("ok\n", encoding="utf-8")
    print("production: ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
