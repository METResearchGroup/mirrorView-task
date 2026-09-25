"""Tests for jev_baseline finalize coverage guard."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

from experiments.predict_keep_remove_jev_gepa_2026_09_23.jev_baseline.run import finalize_ablation


class TestFinalizeAblation:
    """Tests for finalize_ablation."""

    def test_raises_when_prediction_count_does_not_match_cohort(self, tmp_path: Path) -> None:
        cohort = pd.DataFrame(
            {
                "post_id": ["post-a", "post-b"],
                "split": ["test", "dev"],
                "label": [1, 0],
                "sampled_stance": ["liberal", "conservative"],
                "sample_toxicity_type": ["insult", "threat"],
                "remove_share": [0.8, 0.2],
                "is_unanimous": [False, True],
                "n_raters": [10, 10],
            }
        )
        output_dir = tmp_path / "A1_pair_study_prompt"
        output_dir.mkdir(parents=True, exist_ok=True)
        (output_dir / "predictions.jsonl").write_text(
            json.dumps({"post_id": "post-a", "probability_remove": 0.9}) + "\n",
            encoding="utf-8",
        )

        with pytest.raises(RuntimeError, match="1/2 rows scored; 1 missing"):
            finalize_ablation(output_dir, cohort)
