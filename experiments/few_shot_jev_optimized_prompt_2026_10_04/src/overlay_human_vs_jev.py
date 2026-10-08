"""Draw the human vote and Jev bin overlay for this run's all pairs.

Run from repo root::

    PYTHONPATH=. uv run python -m experiments.few_shot_jev_optimized_prompt_2026_10_04.src.overlay_human_vs_jev
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from data_platform.generate_features.s3_feature_campaign import CampaignObjectStore

from experiments.compare_jev_human_uncertainty_2026_09_25.compare import attach_jev_bin
from experiments.compare_jev_human_uncertainty_2026_09_25.plots import plot_overlay
from experiments.few_shot_jev_optimized_prompt_2026_10_04.shared.config import OPTIMIZED_VARIANT
from experiments.few_shot_jev_optimized_prompt_2026_10_04.src.plot_threshold_curves import (
    _load_probabilities,
    _load_records,
)
from experiments.zero_shot_llm_inference_2026_09_30.shared.schemas import Study2InputRecord
from experiments.zero_shot_llm_inference_2026_09_30.shared.storage import (
    apply_lab_aws_credentials_when_unset,
)

_ALL_ROW_COUNT = 13992
_HUMAN_REMOVE_COUNTS = {0: 3743, 1: 4244, 2: 3037, 3: 1777, 4: 883, 5: 308}
_FIGURE_PATH = (
    Path(__file__).resolve().parent.parent / "static" / "overlay_human_vs_jev.png"
)


def main() -> None:
    """Load all pairs and write the grouped human and Jev bar chart."""
    apply_lab_aws_credentials_when_unset()
    store = CampaignObjectStore(OPTIMIZED_VARIANT.s3_bucket, region_name="us-east-2")
    records = _load_records(store)
    frame = _comparison_frame(records, _load_probabilities(store, records))
    _reject_human_counts(frame)
    plot_overlay(frame, _FIGURE_PATH)
    print(f"wrote={_FIGURE_PATH}")
    print(_bin_summary(frame))


def _comparison_frame(
    records: tuple[Study2InputRecord, ...],
    probabilities: dict[str, float],
) -> pd.DataFrame:
    if len(records) != _ALL_ROW_COUNT:
        raise ValueError(f"expected {_ALL_ROW_COUNT} pairs, found {len(records)}")
    rows = [_pair_row(record, probabilities[record.post_id]) for record in records]
    return attach_jev_bin(pd.DataFrame(rows))


def _pair_row(record: Study2InputRecord, probability: float) -> dict[str, object]:
    return {
        "post_id": record.post_id,
        "n_remove": record.n_remove,
        "p_remove": probability,
    }


def _reject_human_counts(frame: pd.DataFrame) -> None:
    counts = frame["n_remove"].value_counts().to_dict()
    for votes, expected in _HUMAN_REMOVE_COUNTS.items():
        if int(counts.get(votes, 0)) != expected:
            raise ValueError(f"remove votes {votes} count is {counts.get(votes, 0)}")


def _bin_summary(frame: pd.DataFrame) -> str:
    counts = frame["jev_bin"].value_counts().sort_index()
    parts = [f"jev_bin_{int(bin_id)}={int(count)}" for bin_id, count in counts.items()]
    return " ".join(parts)


if __name__ == "__main__":
    main()
