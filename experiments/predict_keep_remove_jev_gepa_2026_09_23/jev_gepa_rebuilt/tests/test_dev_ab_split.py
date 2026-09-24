"""Tests for stratified dev-A/dev-B split."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from experiments.predict_keep_remove_jev_gepa_2026_09_23.jev_gepa_rebuilt.constants import GEPA_SEED
from experiments.predict_keep_remove_jev_gepa_2026_09_23.jev_gepa_rebuilt.dev_ab import (
    build_or_load_dev_ab_split,
    dev_ab_split_path,
)


def _make_dev_fixture_parquet(path: Path, n_per_label: int = 40) -> None:
    rows: list[dict[str, object]] = []
    for label in (0, 1):
        for index in range(n_per_label):
            rows.append(
                {
                    "post_id": f"p_{label}_{index}",
                    "original_text": f"orig {label} {index}",
                    "mirror_text": f"mirror {label} {index}",
                    "label": label,
                    "majority_decision": "remove" if label else "keep",
                    "n_raters": 3,
                    "n_keep": 1 if label == 0 else 0,
                    "n_remove": 0 if label == 0 else 1,
                    "n_raters_part2": 3,
                    "n_raters_part3": 0,
                    "remove_share": 0.0 if label == 0 else 1.0,
                    "is_unanimous": True,
                    "sampled_stance": "neutral",
                    "sample_toxicity_type": "none",
                    "post_1_role": "original",
                    "post_2_role": "mirror",
                    "in_part3_cohort_a": False,
                    "label_changed_vs_part3": False,
                    "split": "dev",
                    "gepa_subset": "none",
                }
            )
    pd.DataFrame(rows).to_parquet(path, index=False)


class TestDevAbSplit:
    """Tests for build_or_load_dev_ab_split."""

    def test_stratified_split_and_reproducibility(self, tmp_path: Path, monkeypatch) -> None:
        """50/50 dev split preserves remove rate and is deterministic for a fixed seed."""
        parquet_path = tmp_path / "cohort.parquet"
        split_path = tmp_path / "dev_ab_split.json"
        _make_dev_fixture_parquet(parquet_path)
        monkeypatch.setattr(
            "experiments.predict_keep_remove_jev_gepa_2026_09_23.jev_gepa_rebuilt.dev_ab.dev_ab_split_path",
            lambda: split_path,
        )
        monkeypatch.setattr(
            "experiments.predict_keep_remove_jev_gepa_2026_09_23.jev_gepa_rebuilt.dev_ab.upload_rebuilt",
            lambda _path: None,
        )

        first = build_or_load_dev_ab_split(parquet_path=parquet_path, seed=GEPA_SEED, write=True)
        dev_a_ids = first["dev_a_ids"]
        dev_b_ids = first["dev_b_ids"]
        n_dev = len(dev_a_ids) + len(dev_b_ids)
        assert n_dev == 80

        def remove_rate(ids: list[str]) -> float:
            remove = sum(1 for post_id in ids if post_id.startswith("p_1_"))
            return remove / len(ids)

        full_remove = 0.5
        assert abs(remove_rate(dev_a_ids) - full_remove) <= 0.02
        assert abs(remove_rate(dev_b_ids) - full_remove) <= 0.02

        second = build_or_load_dev_ab_split(parquet_path=parquet_path, seed=GEPA_SEED, write=False)
        assert second["dev_a_ids"] == dev_a_ids
        assert second["dev_b_ids"] == dev_b_ids

    def test_dev_ab_split_path_under_experiment_data(self) -> None:
        """Default sidecar path lives under experiment data/."""
        assert dev_ab_split_path().name == "dev_ab_split.json"
        assert "data" in dev_ab_split_path().parts
