"""Stage 1: feature generation via research_tools LLM runner."""

from __future__ import annotations

import pathlib
from collections.abc import Callable
from typing import Any

from tqdm import tqdm

from experiments.llm_based_feature_generation_2026_07_31.prompts import (
    build_feature_generation_messages,
)
from experiments.llm_based_feature_generation_2026_07_31.schemas import BatchFeatureGeneration
from research_tools.llm.runner import run

EXPERIMENT_ROOT = pathlib.Path(__file__).resolve().parent
DEFAULT_MODEL = "gpt-5.4-nano"


def prompt_fn(batch: dict[str, Any]) -> list[dict[str, str]]:
    """Build chat messages for one keep/remove batch."""
    return build_feature_generation_messages(batch)


def writer_map_fn(batch: dict[str, Any], result: BatchFeatureGeneration) -> dict[str, Any]:
    """Map one batch and structured result to a JSON-serializable output row."""
    return {
        "batch_id": batch["batch_id"],
        "message_ids": sorted(batch["message_ids"]),
        "keep_count": len(batch["keep_posts"]),
        "remove_count": len(batch["remove_posts"]),
        "result": result.model_dump(),
    }


def _wrap_writer_with_progress(
    base_writer: Callable[[dict[str, Any], BatchFeatureGeneration], dict[str, Any]],
    progress_bar: tqdm,
) -> Callable[[dict[str, Any], BatchFeatureGeneration], dict[str, Any]]:
    """Advance the progress bar after each completed runner item."""

    def wrapped(batch: dict[str, Any], result: BatchFeatureGeneration) -> dict[str, Any]:
        row = base_writer(batch, result)
        progress_bar.update(1)
        return row

    return wrapped


def run_stage1(
    batches: list[dict[str, Any]],
    *,
    output_base_path: str | pathlib.Path | None = None,
    model: str = DEFAULT_MODEL,
    seed: int,
    sample_fraction: float,
) -> pathlib.Path:
    """Run feature generation for each batch and return the output folder path."""
    if not batches:
        raise ValueError("run_stage1 requires at least one batch")

    base_path = pathlib.Path(output_base_path or EXPERIMENT_ROOT)
    flat_message_ids = sorted(
        {message_id for batch in batches for message_id in batch["message_ids"]}
    )
    progress_bar = tqdm(total=len(batches), desc="Stage 1 feature generation")
    try:
        return run(
            batches,
            prompt_fn=prompt_fn,
            response_model=BatchFeatureGeneration,
            model=model,
            output_base_path=base_path,
            writer_map_fn=_wrap_writer_with_progress(writer_map_fn, progress_bar),
            run_metadata={
                "stage": "feature_generation",
                "sample_fraction": sample_fraction,
                "seed": seed,
                "model": model,
                "message_ids": flat_message_ids,
            },
        )
    finally:
        progress_bar.close()
