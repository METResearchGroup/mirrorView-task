"""Stage 1: free-response LLM feature generation via research_tools runner.

Run from repo root::

    PYTHONPATH=. uv run python experiments/mine_free_response_for_features_2026_08_03/part_2_mine_free_responses/src/llm_generate_features.py \\
      --likert-group low --sample-size 10 --docs-per-batch 10 --seed 42
"""

from __future__ import annotations

import argparse
from collections.abc import Callable
from typing import Any

import pandas as pd
from tqdm import tqdm

from experiments.mine_free_response_for_features_2026_08_03.part_2_mine_free_responses.src.paths import (
    LikertGroup,
    group_frame_for_likert,
    load_reflection_feedback,
    stage1_root,
    validate_likert_group,
)
from experiments.mine_free_response_for_features_2026_08_03.part_2_mine_free_responses.src.prompts import (
    build_feature_generation_messages,
)
from experiments.mine_free_response_for_features_2026_08_03.part_2_mine_free_responses.src.schemas import (
    MAX_FEATURES_PER_BATCH,
    BatchFeatureGeneration,
    QaStatus,
)
from research_tools.llm.runner import run

DEFAULT_MODEL = "gpt-5.4-nano"
DEFAULT_SAMPLE_SIZE = 10
DEFAULT_DOCS_PER_BATCH = 10
DEFAULT_SEED = 42
TEXT_COLUMN = "phase1_pair_reflection_text"
RATING_COLUMN = "phase1_pair_influence_rating"


def prompt_fn(batch: dict[str, Any]) -> list[dict[str, str]]:
    """Build chat messages for one free-response batch."""
    return build_feature_generation_messages(batch)


def writer_map_fn(
    batch: dict[str, Any],
    result: BatchFeatureGeneration,
) -> dict[str, Any]:
    """Map one batch and structured result to a JSON-serializable output row."""
    return {
        "batch_id": batch["batch_id"],
        "likert_group": batch["likert_group"],
        "participant_ids": sorted(batch["participant_ids"]),
        "feature_count": len(result.features),
        "qa_status": result.qa_status.value
        if isinstance(result.qa_status, QaStatus)
        else result.qa_status,
        "result": result.model_dump(),
    }


def _wrap_writer_with_progress(
    base_writer: Callable[
        [dict[str, Any], BatchFeatureGeneration], dict[str, Any]
    ],
    progress_bar: tqdm,
) -> Callable[[dict[str, Any], BatchFeatureGeneration], dict[str, Any]]:
    """Advance the progress bar after each completed runner item."""

    def wrapped(
        batch: dict[str, Any],
        result: BatchFeatureGeneration,
    ) -> dict[str, Any]:
        row = base_writer(batch, result)
        progress_bar.update(1)
        return row

    return wrapped


def sample_group_reflections(
    group_df: pd.DataFrame,
    sample_size: int,
    seed: int,
) -> pd.DataFrame:
    """Sample ``sample_size`` reflections without replacement from one group.

    Parameters
    ----------
    group_df
        Single Likert-group reflection frame.
    sample_size
        Target sample size; uses the full frame when larger than available.
    seed
        RNG seed for sampling.

    Returns
    -------
    pd.DataFrame
        Sampled rows.
    """
    if sample_size <= 0:
        raise ValueError(f"sample_size must be positive, got {sample_size}")
    if group_df.empty:
        raise ValueError("Cannot sample from an empty Likert group frame")
    n_take = min(sample_size, len(group_df))
    return group_df.sample(n=n_take, random_state=seed).reset_index(drop=True)


def _row_to_reflection(row: pd.Series) -> dict[str, Any]:
    """Convert one dataframe row to a batch reflection dict."""
    return {
        "participant_id": str(row["participant_id"]),
        "phase1_pair_reflection_text": str(row[TEXT_COLUMN]),
        "phase1_pair_influence_rating": float(row[RATING_COLUMN]),
    }


def form_reflection_batches(
    sample: pd.DataFrame,
    likert_group: LikertGroup,
    docs_per_batch: int,
) -> tuple[list[dict[str, Any]], list[str]]:
    """Form reflection batches of exactly ``docs_per_batch`` documents.

    Leftover docs that cannot fill a full batch are returned as leftover ids
    and are not sent to the LLM.

    Parameters
    ----------
    sample
        Sampled reflections for one Likert group.
    likert_group
        low or high.
    docs_per_batch
        Exact batch size.

    Returns
    -------
    tuple[list[dict[str, Any]], list[str]]
        Batches and leftover participant ids.
    """
    if docs_per_batch <= 0:
        raise ValueError(f"docs_per_batch must be positive, got {docs_per_batch}")

    batch_count = len(sample) // docs_per_batch
    if batch_count == 0:
        raise ValueError(
            "Cannot form any full batches from the sample. "
            f"rows={len(sample)}, docs_per_batch={docs_per_batch}."
        )

    batches: list[dict[str, Any]] = []
    for batch_id in range(batch_count):
        start = batch_id * docs_per_batch
        end = start + docs_per_batch
        slice_df = sample.iloc[start:end]
        reflections = [_row_to_reflection(row) for _, row in slice_df.iterrows()]
        participant_ids = sorted(
            reflection["participant_id"] for reflection in reflections
        )
        batches.append(
            {
                "batch_id": batch_id,
                "likert_group": likert_group.value,
                "participant_ids": participant_ids,
                "reflections": reflections,
            }
        )

    leftover = sample.iloc[batch_count * docs_per_batch :]
    leftover_participant_ids = sorted(
        str(pid) for pid in leftover["participant_id"].tolist()
    )
    return batches, leftover_participant_ids


def run_feature_generation(
    batches: list[dict[str, Any]],
    likert_group: LikertGroup,
    sample_size: int,
    docs_per_batch: int,
    seed: int,
    leftover_participant_ids: list[str],
    model: str,
) -> Any:
    """Run feature generation for each batch and return the runner output path.

    Parameters
    ----------
    batches
        Free-response runner items.
    likert_group
        low or high.
    sample_size
        Requested sample size recorded in metadata.
    docs_per_batch
        Batch size recorded in metadata.
    seed
        Sampling seed recorded in metadata.
    leftover_participant_ids
        Participant ids not sent because they could not fill a full batch.
    model
        OpenAI model id.

    Returns
    -------
    pathlib.Path
        Timestamped output directory written by the runner.
    """
    if not batches:
        raise ValueError("run_feature_generation requires at least one batch")

    flat_participant_ids = sorted(
        {
            participant_id
            for batch in batches
            for participant_id in batch["participant_ids"]
        }
    )
    progress_bar = tqdm(
        total=len(batches),
        desc=f"Stage 1 features ({likert_group.value})",
    )
    try:
        return run(
            batches,
            prompt_fn=prompt_fn,
            response_model=BatchFeatureGeneration,
            model=model,
            output_base_path=stage1_root(likert_group.value),
            writer_map_fn=_wrap_writer_with_progress(writer_map_fn, progress_bar),
            run_metadata={
                "stage": "feature_generation",
                "likert_group": likert_group.value,
                "sample_size": sample_size,
                "docs_per_batch": docs_per_batch,
                "seed": seed,
                "model": model,
                "max_features_per_batch": MAX_FEATURES_PER_BATCH,
                "participant_ids": flat_participant_ids,
                "leftover_participant_ids": leftover_participant_ids,
            },
        )
    finally:
        progress_bar.close()


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse CLI arguments for Stage 1."""
    parser = argparse.ArgumentParser(
        description=(
            "Generate LLM features from free-response reflections "
            "(low/high Likert groups)."
        )
    )
    parser.add_argument(
        "--likert-group",
        required=True,
        choices=[LikertGroup.LOW.value, LikertGroup.HIGH.value],
    )
    parser.add_argument("--sample-size", type=int, default=DEFAULT_SAMPLE_SIZE)
    parser.add_argument("--docs-per-batch", type=int, default=DEFAULT_DOCS_PER_BATCH)
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    """CLI entry: sample, batch, and run free-response feature generation."""
    args = parse_args(argv)
    likert_group = validate_likert_group(args.likert_group)
    full_df = load_reflection_feedback()
    group_df = group_frame_for_likert(full_df, likert_group.value)
    sampled = sample_group_reflections(group_df, args.sample_size, args.seed)
    batches, leftover_participant_ids = form_reflection_batches(
        sampled,
        likert_group,
        args.docs_per_batch,
    )
    print(
        f"likert_group={likert_group.value} corpus={len(group_df)} "
        f"sample={len(sampled)} batches={len(batches)} "
        f"leftover={len(leftover_participant_ids)}"
    )
    output_dir = run_feature_generation(
        batches,
        likert_group,
        args.sample_size,
        args.docs_per_batch,
        args.seed,
        leftover_participant_ids,
        args.model,
    )
    print(f"Wrote Stage-1 features to {output_dir}")


if __name__ == "__main__":
    main()
