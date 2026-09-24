"""Tests for dedupe-before-fit and smoke sampling."""

from __future__ import annotations

import pandas as pd

from experiments.bertopic_original_mirror_part3_2026_09_24.src.dedupe import dedupe_stimuli
from experiments.bertopic_original_mirror_part3_2026_09_24.src.fit_bertopic import sample_post_ids


def _row(post_id: str, original_text: str, mirror_text: str) -> dict[str, str]:
    return {"post_id": post_id, "original_text": original_text, "mirror_text": mirror_text}


class TestDedupeBeforeFit:
    """Tests for the dedupe rules applied before a fit."""

    def test_duplicate_originals_collapsed_before_row_count(self) -> None:
        """Two posts with the same original text collapse to one row."""
        stimuli = pd.DataFrame(
            [
                _row("b", "same", "m1"),
                _row("a", "same", "m2"),
                _row("c", "other", "m3"),
                _row("d", "third", "m4"),
            ]
        )

        deduped, _report = dedupe_stimuli(stimuli)

        assert len(deduped) == 3
        assert list(deduped["post_id"]) == ["a", "c", "d"]

    def test_identical_original_mirror_pair_dropped(self) -> None:
        """A post whose mirror equals the original is excluded."""
        stimuli = pd.DataFrame([_row("post-x", "same", "same"), _row("post-y", "orig", "flip")])

        deduped, _report = dedupe_stimuli(stimuli)

        assert "post-x" not in set(deduped["post_id"])


class TestSmokePostSampling:
    """Tests for sample_post_ids."""

    def test_sample_pairs_50_is_deterministic_with_seed_42(self) -> None:
        """Seed 42 draws the same 50 ids twice."""
        post_ids = [f"p{index:03d}" for index in range(80)]

        ids_a = sample_post_ids(post_ids, n=50, seed=42)
        ids_b = sample_post_ids(post_ids, n=50, seed=42)

        assert ids_a == ids_b
        assert len(ids_a) == 50
