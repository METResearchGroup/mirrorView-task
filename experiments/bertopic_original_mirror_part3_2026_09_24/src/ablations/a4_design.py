"""Compare separate, joint, and transform designs without refitting."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from experiments.bertopic_original_mirror_part3_2026_09_24.src.analyze_cross_role import (
    agreement_rate_all,
    role_share_table,
)

NOISE_TOPIC_ID = -1


def _topic_frame(path: Path, role: str) -> pd.DataFrame:
    """Load one role's topic ids."""
    frame = pd.read_parquet(path / "assignments.parquet")
    if "text_role" in frame.columns:
        frame = frame.loc[frame["text_role"] == role]
    return frame[["post_id", "topic"]].copy()


def run_a4_design_comparison(
    original_run: Path,
    mirror_run: Path,
    joint_run: Path,
    assignments_run: Path,
    output_dir: Path,
) -> Path:
    """Write Q2 and Q3 metrics for the three fit designs.

    Does not create or modify topic run directories.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    _write_separate(original_run, mirror_run, output_dir / "separate")
    _write_joint(joint_run, output_dir / "joint")
    _write_transform(original_run, assignments_run, output_dir / "original_assign_mirror")
    return output_dir


def _write_metrics(directory: Path, payload: dict) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "q2_q3_metrics.json").write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def _write_separate(original_run: Path, mirror_run: Path, directory: Path) -> None:
    original = _topic_frame(original_run, "original").rename(columns={"topic": "original_topic"})
    mirror = _topic_frame(mirror_run, "mirror").rename(columns={"topic": "mirror_topic"})
    pairs = original.merge(mirror, on="post_id", how="inner")
    stacked = pd.concat(
        [
            pairs[["post_id", "original_topic"]].rename(columns={"original_topic": "topic"}).assign(text_role="original"),
            pairs[["post_id", "mirror_topic"]].rename(columns={"mirror_topic": "topic"}).assign(text_role="mirror"),
        ],
        ignore_index=True,
    )
    shares = role_share_table(stacked)
    _write_metrics(
        directory,
        {
            "q2_pair_agreement": agreement_rate_all(pairs),
            "q3_role_dominated_topics": int(shares["role_dominated_flag"].sum()),
            "notes": "Separate models use unrelated topic ids, so role share is one-sided.",
        },
    )


def _write_joint(joint_run: Path, directory: Path) -> None:
    assignments = pd.read_parquet(joint_run / "assignments.parquet")
    original = assignments.loc[assignments["text_role"] == "original", ["post_id", "topic"]]
    mirror = assignments.loc[assignments["text_role"] == "mirror", ["post_id", "topic"]]
    pairs = original.merge(mirror, on="post_id", suffixes=("_original", "_mirror"))
    pairs = pairs.rename(columns={"topic_original": "original_topic", "topic_mirror": "mirror_topic"})
    shares = role_share_table(assignments)
    _write_metrics(
        directory,
        {
            "q2_pair_agreement": agreement_rate_all(pairs),
            "q3_role_dominated_topics": int(shares["role_dominated_flag"].sum()),
        },
    )


def _write_transform(original_run: Path, assignments_run: Path, directory: Path) -> None:
    pairs = pd.read_parquet(assignments_run / "pair_assignments.parquet")
    original_rows = pairs[["post_id", "original_topic"]].rename(columns={"original_topic": "topic"})
    original_rows["text_role"] = "original"
    mirror_rows = pairs[["post_id", "mirror_topic"]].rename(columns={"mirror_topic": "topic"})
    mirror_rows["text_role"] = "mirror"
    shares = role_share_table(pd.concat([original_rows, mirror_rows], ignore_index=True))
    _ = original_run
    _write_metrics(
        directory,
        {
            "q2_pair_agreement": agreement_rate_all(pairs),
            "q3_role_dominated_topics": int(shares["role_dominated_flag"].sum()),
        },
    )
