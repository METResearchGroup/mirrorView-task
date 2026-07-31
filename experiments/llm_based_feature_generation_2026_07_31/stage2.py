"""Stage 2: thematic commonality synthesis via research_tools LLM runner."""

from __future__ import annotations

import json
import pathlib
from collections.abc import Callable
from typing import Any

from tqdm import tqdm

from experiments.llm_based_feature_generation_2026_07_31.prompts import (
    build_theme_synthesis_messages,
)
from experiments.llm_based_feature_generation_2026_07_31.schemas import ThemeSynthesisResult
from research_tools.llm.runner import run

EXPERIMENT_ROOT = pathlib.Path(__file__).resolve().parent
DEFAULT_MODEL = "gpt-5.4-nano"
_METADATA_FILENAME = "metadata.json"


def load_stage1_results(stage1_dir: str | pathlib.Path) -> list[dict[str, Any]]:
    """Load stage-1 result JSON files, skipping metadata.json."""
    directory = pathlib.Path(stage1_dir)
    if not directory.is_dir():
        raise FileNotFoundError(f"Stage 1 output directory not found: {directory}")

    results: list[dict[str, Any]] = []
    for path in sorted(directory.glob("*.json")):
        if path.name == _METADATA_FILENAME:
            continue
        results.append(json.loads(path.read_text(encoding="utf-8")))
    if not results:
        raise ValueError(f"No stage-1 result JSON files found in {directory}")
    return results


def _build_stage2_item(
    stage1_results: list[dict[str, Any]],
    *,
    source_stage1_dir: pathlib.Path,
) -> dict[str, Any]:
    """Aggregate stage-1 rows into a single theme-synthesis item."""
    return {
        "source_stage1_dir": str(source_stage1_dir),
        "n_stage1_batches": len(stage1_results),
        "stage1_results": stage1_results,
    }


def prompt_fn(item: dict[str, Any]) -> list[dict[str, str]]:
    """Build chat messages for theme synthesis."""
    return build_theme_synthesis_messages(item)


def writer_map_fn(item: dict[str, Any], result: ThemeSynthesisResult) -> dict[str, Any]:
    """Map one synthesis item and structured result to a JSON-serializable output row."""
    return {
        "source_stage1_dir": item["source_stage1_dir"],
        "n_stage1_batches": item["n_stage1_batches"],
        "result": result.model_dump(),
    }


def _wrap_writer_with_progress(
    base_writer: Callable[[dict[str, Any], ThemeSynthesisResult], dict[str, Any]],
    progress_bar: tqdm,
) -> Callable[[dict[str, Any], ThemeSynthesisResult], dict[str, Any]]:
    """Advance the progress bar after each completed runner item."""

    def wrapped(item: dict[str, Any], result: ThemeSynthesisResult) -> dict[str, Any]:
        row = base_writer(item, result)
        progress_bar.update(1)
        return row

    return wrapped


def run_stage2(
    stage1_output_dir: str | pathlib.Path,
    *,
    output_base_path: str | pathlib.Path | None = None,
    model: str = DEFAULT_MODEL,
) -> pathlib.Path:
    """Run theme synthesis over stage-1 outputs and return the output folder path."""
    stage1_path = pathlib.Path(stage1_output_dir)
    stage1_results = load_stage1_results(stage1_path)
    stage2_item = _build_stage2_item(stage1_results, source_stage1_dir=stage1_path)
    base_path = pathlib.Path(output_base_path or EXPERIMENT_ROOT)

    progress_bar = tqdm(total=1, desc="Stage 2 theme synthesis")
    try:
        return run(
            [stage2_item],
            prompt_fn=prompt_fn,
            response_model=ThemeSynthesisResult,
            model=model,
            output_base_path=base_path,
            writer_map_fn=_wrap_writer_with_progress(writer_map_fn, progress_bar),
            run_metadata={
                "stage": "theme_synthesis",
                "source_stage1_dir": str(stage1_path),
                "model": model,
            },
        )
    finally:
        progress_bar.close()
