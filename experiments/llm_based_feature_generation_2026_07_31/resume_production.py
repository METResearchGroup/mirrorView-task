"""Resume production run: stage 2 + RESULTS.md from completed stage 1."""

from __future__ import annotations

import pathlib
import sys

from experiments.llm_based_feature_generation_2026_07_31.stage1 import DEFAULT_MODEL
from experiments.llm_based_feature_generation_2026_07_31.stage2 import run_stage2
from experiments.llm_based_feature_generation_2026_07_31.write_results import write_results_md

EXPERIMENT_ROOT = pathlib.Path(__file__).resolve().parent
DONE_MARKER = EXPERIMENT_ROOT / ".production_complete"


def main() -> int:
    """Run sharded stage 2 and write RESULTS.md for an existing stage-1 output dir."""
    if len(sys.argv) != 2:
        print(f"usage: {sys.argv[0]} <stage1-output-dir>", file=sys.stderr)
        return 2

    stage1_dir = pathlib.Path(sys.argv[1]).resolve()
    stage2_dir = run_stage2(stage1_dir, model=DEFAULT_MODEL)
    print(f"stage2_dir={stage2_dir}")

    metadata_path = stage1_dir / "metadata.json"
    batch_count = 140
    if metadata_path.is_file():
        import json

        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        batch_count = int(metadata.get("total_items", batch_count))

    write_results_md(
        stage1_dir=stage1_dir,
        stage2_dir=stage2_dir,
        batch_count=batch_count,
        model=DEFAULT_MODEL,
        sample_fraction=0.50,
    )
    DONE_MARKER.write_text("ok\n", encoding="utf-8")
    print("production: ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
