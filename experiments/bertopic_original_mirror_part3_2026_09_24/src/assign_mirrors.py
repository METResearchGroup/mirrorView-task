"""Assign mirror texts with a fitted original BERTopic model.

Run from repo root::

    PYTHONPATH=. uv run --extra bertopic python \\
      experiments/bertopic_original_mirror_part3_2026_09_24/src/assign_mirrors.py \\
      --original-topics-run-dir experiments/bertopic_original_mirror_part3_2026_09_24/outputs/topics/original/<UTC_TS>
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd
from bertopic import BERTopic

from experiments.bertopic_original_mirror_part3_2026_09_24.src import paths
from experiments.bertopic_original_mirror_part3_2026_09_24.src.fit_bertopic import (
    load_fit_corpus,
    max_topic_probability,
    subset_corpus,
)

NOISE_TOPIC_ID = -1


def make_pair_row(
    post_id: str,
    original_topic: int,
    mirror_topic: int,
    original_probability: float | None,
    mirror_probability: float | None,
) -> dict:
    """Return one pair-assignment row.

    Parameters
    ----------
    post_id
        Stimulus post id. ``pair_post_id`` equals this value.
    original_topic
        Topic from the original fit.
    mirror_topic
        Topic from ``transform`` on the mirror text.
    original_probability
        Max original-topic probability.
    mirror_probability
        Max mirror-topic probability.

    Returns
    -------
    dict
        Columns for ``pair_assignments.parquet``.
    """
    return {
        "post_id": post_id,
        "pair_post_id": post_id,
        "original_topic": int(original_topic),
        "mirror_topic": int(mirror_topic),
        "original_probability": original_probability,
        "mirror_probability": mirror_probability,
        "topics_agree": int(original_topic) == int(mirror_topic),
    }


def assign_mirror_topics(topic_model: BERTopic, docs: list[str], embeddings: np.ndarray) -> tuple[list[int], list[float | None]]:
    """Assign topics with ``transform``. Does not refit the model.

    Parameters
    ----------
    topic_model
        Fitted original model.
    docs
        Mirror documents.
    embeddings
        Mirror embeddings aligned to ``docs``.

    Returns
    -------
    tuple[list[int], list[float | None]]
        Topic ids and max probabilities.
    """
    topics, probabilities = topic_model.transform(docs, embeddings)
    topic_ids = [int(topic) for topic in topics]
    return topic_ids, max_topic_probability(probabilities, len(docs))


def _original_topics_by_post(assignments: pd.DataFrame) -> pd.DataFrame:
    """Keep original-role assignment rows."""
    original_rows = assignments.loc[assignments["text_role"] == "original"].copy()
    return original_rows.drop_duplicates("post_id")


def run_assign_mirrors(original_topics_run_dir: Path) -> Path:
    """Write pair assignments for the original model's deduped posts.

    Parameters
    ----------
    original_topics_run_dir
        A topics run directory containing ``model/`` and ``assignments.parquet``.

    Returns
    -------
    pathlib.Path
        The new assignments run directory.
    """
    metadata = json.loads((original_topics_run_dir / "metadata.json").read_text(encoding="utf-8"))
    model = BERTopic.load(str(original_topics_run_dir / "model"))
    original_assignments = _original_topics_by_post(
        pd.read_parquet(original_topics_run_dir / "assignments.parquet")
    )
    mirror_corpus, _report = load_fit_corpus("mirror")
    sample_ids = metadata.get("sample_post_ids")
    if sample_ids:
        mirror_corpus = subset_corpus(mirror_corpus, sample_ids)
    mirror_topics, mirror_probs = assign_mirror_topics(
        model, mirror_corpus.docs, mirror_corpus.embeddings
    )
    original_by_id = original_assignments.set_index("post_id")
    rows = []
    for index, post_id in enumerate(mirror_corpus.post_ids):
        original = original_by_id.loc[post_id]
        rows.append(
            make_pair_row(
                post_id,
                int(original["topic"]),
                mirror_topics[index],
                None if pd.isna(original["probability"]) else float(original["probability"]),
                mirror_probs[index],
            )
        )
    frame = pd.DataFrame(rows)
    both_labeled = (frame["original_topic"] != NOISE_TOPIC_ID) & (frame["mirror_topic"] != NOISE_TOPIC_ID)
    run_dir = paths.assignments_dir() / paths.new_run_timestamp()
    run_dir.mkdir(parents=True, exist_ok=True)
    frame.to_parquet(run_dir / "pair_assignments.parquet", index=False)
    summary = {
        "source_original_topics_run": str(original_topics_run_dir),
        "n_pairs": int(len(frame)),
        "n_agree": int(frame["topics_agree"].sum()),
        "n_agree_excl_noise": int(frame.loc[both_labeled, "topics_agree"].sum()),
        "seed": metadata.get("seed"),
        "dedupe_report_path": metadata.get("dedupe_report_path"),
    }
    (run_dir / "metadata.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(f"assignments_run_dir={run_dir} n_pairs={len(frame)} n_agree={summary['n_agree']}")
    return run_dir


def main() -> None:
    """CLI entry for mirror assignment."""
    parser = argparse.ArgumentParser(description="Assign mirror texts with the original model.")
    parser.add_argument("--original-topics-run-dir", type=Path, required=True)
    args = parser.parse_args()
    run_assign_mirrors(args.original_topics_run_dir)


if __name__ == "__main__":
    main()
