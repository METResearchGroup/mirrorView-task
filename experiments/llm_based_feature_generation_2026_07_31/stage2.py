"""Stage 2: thematic commonality synthesis via research_tools.llm.runner."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from research_tools.llm.runner import run

from experiments.llm_based_feature_generation_2026_07_31.batching import EXPERIMENT_ROOT
from experiments.llm_based_feature_generation_2026_07_31.prompts import (
    build_theme_synthesis_messages,
)
from experiments.llm_based_feature_generation_2026_07_31.schemas import (
    ThemeSynthesisResult,
)

DEFAULT_MODEL = "gpt-5.4-nano"


def load_stage1_results(stage1_dir: str | Path) -> list[dict[str, Any]]:
    """Load stage-1 result JSON files (skip metadata.json)."""
    directory = Path(stage1_dir)
    if not directory.is_dir():
        raise FileNotFoundError(f"stage1_dir is not a directory: {directory}")

    rows: list[dict[str, Any]] = []
    for path in sorted(directory.glob("*.json")):
        if path.name == "metadata.json":
            continue
        rows.append(json.loads(path.read_text(encoding="utf-8")))
    if not rows:
        raise ValueError(f"No stage-1 result JSON files found in {directory}")
    return rows


def prompt_fn(item: dict[str, Any]) -> list[dict]:
    """Build chat messages for theme synthesis."""
    return build_theme_synthesis_messages(item)


def writer_map_fn(item: dict[str, Any], result: ThemeSynthesisResult) -> dict[str, Any]:
    """Map (item, theme result) to a JSON-serializable result row."""
    return {
        "source_stage1_dir": item["source_stage1_dir"],
        "n_stage1_batches": item["n_stage1_batches"],
        "result": result.model_dump(),
    }


def run_stage2(
    stage1_dir: str | Path,
    *,
    output_base_path: str | Path | None = None,
    model: str = DEFAULT_MODEL,
) -> Path:
    """Aggregate stage-1 features and run theme synthesis; return output folder."""
    stage1_path = Path(stage1_dir).resolve()
    rows = load_stage1_results(stage1_path)
    corpus = [
        {
            "batch_id": row.get("batch_id"),
            "message_ids": row.get("message_ids"),
            "result": row.get("result"),
        }
        for row in rows
    ]
    item = {
        "source_stage1_dir": str(stage1_path),
        "n_stage1_batches": len(rows),
        "corpus": corpus,
    }
    base = Path(output_base_path) if output_base_path is not None else EXPERIMENT_ROOT
    return run(
        [item],
        prompt_fn=prompt_fn,
        response_model=ThemeSynthesisResult,
        model=model,
        output_base_path=base,
        writer_map_fn=writer_map_fn,
        run_metadata={
            "stage": "theme_synthesis",
            "model": model,
            "source_stage1_dir": str(stage1_path),
            "n_stage1_batches": len(rows),
        },
    )
