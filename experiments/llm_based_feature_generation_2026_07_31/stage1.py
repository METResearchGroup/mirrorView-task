"""Stage 1: feature generation via research_tools.llm.runner."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from research_tools.llm.runner import run

from experiments.llm_based_feature_generation_2026_07_31.batching import (
    EXPERIMENT_ROOT,
    all_message_ids,
)
from experiments.llm_based_feature_generation_2026_07_31.prompts import (
    build_feature_generation_messages,
)
from experiments.llm_based_feature_generation_2026_07_31.schemas import (
    BatchFeatureGeneration,
)

DEFAULT_MODEL = "gpt-5.4-nano"


def prompt_fn(item: dict[str, Any]) -> list[dict]:
    """Build chat messages for one mixed keep/remove batch."""
    return build_feature_generation_messages(item)


def writer_map_fn(item: dict[str, Any], result: BatchFeatureGeneration) -> dict[str, Any]:
    """Map (batch, structured result) to a JSON-serializable result row."""
    return {
        "batch_id": item["batch_id"],
        "message_ids": list(item["message_ids"]),
        "n_keep": len(item["keep_posts"]),
        "n_remove": len(item["remove_posts"]),
        "result": result.model_dump(),
    }


def run_stage1(
    batches: list[dict[str, Any]],
    *,
    output_base_path: str | Path | None = None,
    model: str = DEFAULT_MODEL,
    sample_fraction: float,
    seed: int,
    leftover_count: int = 0,
) -> Path:
    """Run feature generation over batches; return the timestamped output folder."""
    if not batches:
        raise ValueError("batches must be non-empty")

    message_ids = all_message_ids(batches)
    if len(message_ids) != len(set(message_ids)):
        raise ValueError("Duplicate message_ids across batches")

    base = Path(output_base_path) if output_base_path is not None else EXPERIMENT_ROOT
    return run(
        batches,
        prompt_fn=prompt_fn,
        response_model=BatchFeatureGeneration,
        model=model,
        output_base_path=base,
        writer_map_fn=writer_map_fn,
        run_metadata={
            "stage": "feature_generation",
            "sample_fraction": sample_fraction,
            "seed": seed,
            "model": model,
            "n_batches": len(batches),
            "leftover_count": leftover_count,
            "message_ids": message_ids,
        },
    )
