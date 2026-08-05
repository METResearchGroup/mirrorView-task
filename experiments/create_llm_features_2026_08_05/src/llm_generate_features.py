"""Stage 1: single-class LLM feature generation via research_tools runner.

Run from repo root::

    PYTHONPATH=. uv run python experiments/create_llm_features_2026_08_05/src/llm_generate_features.py \\
      --label-class keep --sample-size 10 --posts-per-batch 10 --seed 42
"""

from __future__ import annotations

import argparse
from collections.abc import Callable
from typing import Any

import pandas as pd
from tqdm import tqdm

from experiments.create_llm_features_2026_08_05.src.paths import (
    LabelClass,
    load_keep_remove_posts,
    split_by_decision,
    stage1_root,
    validate_label_class,
)
from experiments.create_llm_features_2026_08_05.src.prompts import (
    build_feature_generation_messages,
)
from experiments.create_llm_features_2026_08_05.src.schemas import (
    MAX_FEATURES_PER_BATCH,
    SingleClassBatchFeatureGeneration,
)
from research_tools.llm.runner import run

DEFAULT_MODEL = "gpt-5.4-nano"
DEFAULT_SAMPLE_SIZE = 10
DEFAULT_POSTS_PER_BATCH = 10
DEFAULT_SEED = 42
SMOKE_SAMPLE_SIZE = 10
PRODUCTION_SAMPLE_SIZE = 500


def prompt_fn(batch: dict[str, Any]) -> list[dict[str, str]]:
    """Build chat messages for one single-class batch."""
    return build_feature_generation_messages(batch)


def writer_map_fn(
    batch: dict[str, Any],
    result: SingleClassBatchFeatureGeneration,
) -> dict[str, Any]:
    """Map one batch and structured result to a JSON-serializable output row."""
    return {
        "batch_id": batch["batch_id"],
        "label_class": batch["label_class"],
        "message_ids": sorted(batch["message_ids"]),
        "feature_count": len(result.features),
        "result": result.model_dump(),
    }


def _wrap_writer_with_progress(
    base_writer: Callable[
        [dict[str, Any], SingleClassBatchFeatureGeneration], dict[str, Any]
    ],
    progress_bar: tqdm,
) -> Callable[[dict[str, Any], SingleClassBatchFeatureGeneration], dict[str, Any]]:
    """Advance the progress bar after each completed runner item."""

    def wrapped(
        batch: dict[str, Any],
        result: SingleClassBatchFeatureGeneration,
    ) -> dict[str, Any]:
        row = base_writer(batch, result)
        progress_bar.update(1)
        return row

    return wrapped


def _posts_for_label_class(label_class: LabelClass) -> pd.DataFrame:
    """Load and return the keep or remove frame only."""
    keep_df, remove_df = split_by_decision(load_keep_remove_posts())
    class_frames = {
        LabelClass.KEEP: keep_df,
        LabelClass.REMOVE: remove_df,
    }
    return class_frames[label_class]


def sample_class_posts(
    class_df: pd.DataFrame,
    sample_size: int,
    seed: int,
) -> pd.DataFrame:
    """Sample ``sample_size`` posts without replacement from one class.

    Parameters
    ----------
    class_df
        Single-class posts frame.
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
    if class_df.empty:
        raise ValueError("Cannot sample from an empty class frame")
    n_take = min(sample_size, len(class_df))
    return class_df.sample(n=n_take, random_state=seed).reset_index(drop=True)


def _row_to_post(row: pd.Series, label_class: LabelClass) -> dict[str, str]:
    """Convert one dataframe row to a batch post dict."""
    return {
        "message_id": str(row["message_id"]),
        "original_text": str(row["original_text"]),
        "mirror_text": str(row["mirror_text"]),
        "decision": label_class.value,
    }


def form_single_class_batches(
    sample: pd.DataFrame,
    label_class: LabelClass,
    posts_per_batch: int,
) -> tuple[list[dict[str, Any]], list[str]]:
    """Form single-class batches of exactly ``posts_per_batch`` posts.

    Leftover posts that cannot fill a full batch are returned as leftover ids
    and are not sent to the LLM.

    Parameters
    ----------
    sample
        Sampled posts for one label class.
    label_class
        keep or remove.
    posts_per_batch
        Exact batch size.

    Returns
    -------
    tuple[list[dict[str, Any]], list[str]]
        Batches and leftover message ids.

    Raises
    ------
    ValueError
        When zero full batches can be formed.
    """
    if posts_per_batch <= 0:
        raise ValueError(f"posts_per_batch must be positive, got {posts_per_batch}")

    batch_count = len(sample) // posts_per_batch
    if batch_count == 0:
        raise ValueError(
            "Cannot form any full batches from the sample. "
            f"rows={len(sample)}, posts_per_batch={posts_per_batch}."
        )

    batches: list[dict[str, Any]] = []
    for batch_id in range(batch_count):
        start = batch_id * posts_per_batch
        end = start + posts_per_batch
        slice_df = sample.iloc[start:end]
        posts = [_row_to_post(row, label_class) for _, row in slice_df.iterrows()]
        message_ids = sorted(post["message_id"] for post in posts)
        batches.append(
            {
                "batch_id": batch_id,
                "label_class": label_class.value,
                "message_ids": message_ids,
                "posts": posts,
            }
        )

    leftover = sample.iloc[batch_count * posts_per_batch :]
    leftover_message_ids = sorted(str(mid) for mid in leftover["message_id"].tolist())
    return batches, leftover_message_ids


def run_feature_generation(
    batches: list[dict[str, Any]],
    label_class: LabelClass,
    sample_size: int,
    posts_per_batch: int,
    seed: int,
    leftover_message_ids: list[str],
    model: str,
) -> Any:
    """Run feature generation for each batch and return the runner output path.

    Parameters
    ----------
    batches
        Single-class runner items.
    label_class
        keep or remove.
    sample_size
        Requested sample size recorded in metadata.
    posts_per_batch
        Batch size recorded in metadata.
    seed
        Sampling seed recorded in metadata.
    leftover_message_ids
        Message ids not sent because they could not fill a full batch.
    model
        OpenAI model id.

    Returns
    -------
    pathlib.Path
        Timestamped output directory written by the runner.
    """
    if not batches:
        raise ValueError("run_feature_generation requires at least one batch")

    flat_message_ids = sorted(
        {message_id for batch in batches for message_id in batch["message_ids"]}
    )
    progress_bar = tqdm(total=len(batches), desc=f"Stage 1 features ({label_class.value})")
    try:
        return run(
            batches,
            prompt_fn=prompt_fn,
            response_model=SingleClassBatchFeatureGeneration,
            model=model,
            output_base_path=stage1_root(label_class.value),
            writer_map_fn=_wrap_writer_with_progress(writer_map_fn, progress_bar),
            run_metadata={
                "stage": "feature_generation",
                "label_class": label_class.value,
                "sample_size": sample_size,
                "posts_per_batch": posts_per_batch,
                "seed": seed,
                "model": model,
                "max_features_per_batch": MAX_FEATURES_PER_BATCH,
                "message_ids": flat_message_ids,
                "leftover_message_ids": leftover_message_ids,
            },
        )
    finally:
        progress_bar.close()


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse CLI arguments for Stage 1."""
    parser = argparse.ArgumentParser(
        description="Generate LLM features for keep or remove posts (single-class batches)."
    )
    parser.add_argument(
        "--label-class",
        required=True,
        choices=[LabelClass.KEEP.value, LabelClass.REMOVE.value],
    )
    parser.add_argument("--sample-size", type=int, default=DEFAULT_SAMPLE_SIZE)
    parser.add_argument("--posts-per-batch", type=int, default=DEFAULT_POSTS_PER_BATCH)
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    """CLI entry: sample, batch, and run single-class feature generation."""
    args = parse_args(argv)
    label_class = validate_label_class(args.label_class)
    class_df = _posts_for_label_class(label_class)
    sampled = sample_class_posts(class_df, args.sample_size, args.seed)
    batches, leftover_message_ids = form_single_class_batches(
        sampled,
        label_class,
        args.posts_per_batch,
    )
    print(
        f"label_class={label_class.value} corpus={len(class_df)} "
        f"sample={len(sampled)} batches={len(batches)} "
        f"leftover={len(leftover_message_ids)}"
    )
    output_dir = run_feature_generation(
        batches,
        label_class,
        args.sample_size,
        args.posts_per_batch,
        args.seed,
        leftover_message_ids,
        args.model,
    )
    print(f"Wrote Stage-1 features to {output_dir}")


if __name__ == "__main__":
    main()
