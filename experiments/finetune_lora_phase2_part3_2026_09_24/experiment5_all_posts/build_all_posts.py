"""Build the all-posts table and chat JSONL for Experiment 5 inference.

Run from root:

PYTHONPATH=. uv run python \\
  experiments/finetune_lora_phase2_part3_2026_09_24/experiment5_all_posts/build_all_posts.py \\
  --force
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from experiments.finetune_qwen_model_2026_08_08.src.create_chat_dataset import (
    row_to_chat_record,
)
from shared.data.dataloader import load_dataset
from shared.data.registry import STUDY_PHASE_2_PART_2_AND_3_RESULTS_FULL
from shared.data.transformed.keep_remove_aggregation import (
    aggregate_modal_labels,
    filter_keep_remove_trials,
)

EXPERIMENT_ROOT = Path(__file__).resolve().parent
PART3_ROOT = EXPERIMENT_ROOT.parent
DATA_DIR = EXPERIMENT_ROOT / "data"
DEFAULT_MANIFEST_PATH = PART3_ROOT / "data" / "split_manifest.csv"
DEFAULT_CSV_PATH = DATA_DIR / "all_posts.csv"
DEFAULT_JSONL_PATH = DATA_DIR / "chat_all_posts.jsonl"

OUTPUT_COLUMNS = [
    "message_id",
    "original_text",
    "mirror_text",
    "decision",
    "keep_remove_label",
    "n_raters",
    "n_remove",
    "split",
    "in_unanimous",
]


def _compute_n_remove(trials: pd.DataFrame) -> pd.DataFrame:
    """Count remove decisions per post on filtered trial rows."""
    decisions = trials["decision"].astype(str).str.lower().str.strip()
    counted = trials.assign(_is_remove=decisions == "remove")
    return (
        counted.groupby("post_id", dropna=False)["_is_remove"]
        .sum()
        .astype(int)
        .reset_index(name="n_remove")
        .rename(columns={"post_id": "message_id"})
    )


def build_all_posts_frame(raw_df: pd.DataFrame, manifest_df: pd.DataFrame) -> pd.DataFrame:
    """Build one row per modal keep/remove post with split metadata.

    Parameters
    ----------
    raw_df
        Combined Part 2 and Part 3 study results table.
    manifest_df
        Post-level split manifest with ``post_id``, ``split``,
        ``modal_label``, and ``in_unanimous``.

    Returns
    -------
    pandas.DataFrame
        Columns: ``message_id``, ``original_text``, ``mirror_text``,
        ``decision``, ``keep_remove_label``, ``n_raters``, ``n_remove``,
        ``split``, ``in_unanimous``.

    Raises
    ------
    ValueError
        If a modal post is missing from the manifest or disagrees with
        ``modal_label``.
    """
    trials = filter_keep_remove_trials(raw_df, dedupe_worker_post=True)
    labels = aggregate_modal_labels(trials)
    n_remove = _compute_n_remove(trials)
    labels = labels.merge(n_remove, on="message_id", how="left")

    manifest = manifest_df.copy()
    manifest["post_id"] = manifest["post_id"].astype(str)
    merged = labels.merge(
        manifest,
        left_on="message_id",
        right_on="post_id",
        how="left",
    )

    missing_mask = merged["split"].isna()
    if missing_mask.any():
        missing_ids = merged.loc[missing_mask, "message_id"].astype(str).tolist()
        example = missing_ids[0]
        raise ValueError(
            "Modal post missing from split manifest. "
            f"Example message_id={example!r} (count={len(missing_ids)})."
        )

    modal_label = merged["modal_label"].astype(str).str.lower().str.strip()
    decision = merged["decision"].astype(str).str.lower().str.strip()
    disagree = modal_label != decision
    if disagree.any():
        bad = merged.loc[disagree].iloc[0]
        raise ValueError(
            "Aggregated decision disagrees with manifest modal_label. "
            f"Example message_id={bad['message_id']!r}, "
            f"decision={bad['decision']!r}, modal_label={bad['modal_label']!r}."
        )

    return merged[OUTPUT_COLUMNS].reset_index(drop=True)


def write_all_posts(frame: pd.DataFrame, csv_path: Path) -> None:
    """Write the all-posts CSV with the canonical column order.

    Parameters
    ----------
    frame
        Output of ``build_all_posts_frame``.
    csv_path
        Destination CSV path.
    """
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    frame[list(OUTPUT_COLUMNS)].to_csv(csv_path, index=False)


def write_chat_jsonl(frame: pd.DataFrame, jsonl_path: Path) -> int:
    """Write chat JSONL records for every row in ``frame``.

    Parameters
    ----------
    frame
        All-posts frame with message text and gold ``decision``.
    jsonl_path
        Destination JSONL path.

    Returns
    -------
    int
        Number of lines written.
    """
    jsonl_path.parent.mkdir(parents=True, exist_ok=True)
    records = [row_to_chat_record(row) for _, row in frame.iterrows()]
    with jsonl_path.open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")
    return len(records)


def build_and_write_all_posts(
    *,
    force: bool,
    manifest_path: Path = DEFAULT_MANIFEST_PATH,
    csv_path: Path = DEFAULT_CSV_PATH,
    jsonl_path: Path = DEFAULT_JSONL_PATH,
) -> tuple[int, int]:
    """Load raw results, build the table, and write CSV plus chat JSONL.

    Parameters
    ----------
    force
        Overwrite existing outputs when True.
    manifest_path
        Path to ``split_manifest.csv``.
    csv_path
        Destination all-posts CSV path.
    jsonl_path
        Destination chat JSONL path.

    Returns
    -------
    tuple[int, int]
        ``(n_csv_rows, n_jsonl_lines)``.

    Raises
    ------
    FileExistsError
        If an output path exists and ``force`` is False.
    """
    if csv_path.exists() and not force:
        raise FileExistsError(
            f"Refusing to overwrite {csv_path}; pass --force."
        )
    if jsonl_path.exists() and not force:
        raise FileExistsError(
            f"Refusing to overwrite {jsonl_path}; pass --force."
        )

    raw_df = load_dataset(STUDY_PHASE_2_PART_2_AND_3_RESULTS_FULL, low_memory=False)
    manifest_df = pd.read_csv(manifest_path)
    frame = build_all_posts_frame(raw_df, manifest_df)
    write_all_posts(frame, csv_path)
    n_jsonl = write_chat_jsonl(frame, jsonl_path)
    return len(frame), n_jsonl


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse CLI arguments."""
    parser = argparse.ArgumentParser(
        description="Build all-posts CSV and chat JSONL for Experiment 5."
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite existing CSV and JSONL outputs.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    """CLI entrypoint."""
    args = parse_args(argv)
    n_rows, n_jsonl = build_and_write_all_posts(force=bool(args.force))
    print(f"Wrote {DEFAULT_CSV_PATH} ({n_rows} rows)")
    print(f"Wrote {DEFAULT_JSONL_PATH} ({n_jsonl} lines)")


if __name__ == "__main__":
    main()
