"""Tests for stimulus dedupe."""

from __future__ import annotations

import pandas as pd

from experiments.bertopic_original_mirror_part3_2026_09_24.src.data import load_stimuli_posts
from experiments.bertopic_original_mirror_part3_2026_09_24.src.dedupe import (
    build_dedupe_report,
    dedupe_stimuli,
)

REPORT_KEYS = {
    "n_stimuli_raw",
    "n_removed_duplicate_original",
    "n_removed_identical_pair",
    "n_after_dedupe",
    "dedupe_rule_duplicate_original",
    "dedupe_rule_identical_pair",
}


def _row(post_id: str, original_text: str, mirror_text: str) -> dict[str, str]:
    return {"post_id": post_id, "original_text": original_text, "mirror_text": mirror_text}


class TestDedupeStimuli:
    """Tests for dedupe_stimuli."""

    def test_dedupe_removes_duplicate_original_keeps_lowest_post_id(self) -> None:
        """The lower post_id survives when original text is repeated."""
        stimuli = pd.DataFrame([_row("b", "same", "m1"), _row("a", "same", "m2")])

        result, _report = dedupe_stimuli(stimuli)

        assert list(result["post_id"]) == ["a"]

    def test_dedupe_removes_identical_pair(self) -> None:
        """A row whose mirror equals the original is dropped."""
        stimuli = pd.DataFrame([_row("a", "same", "same"), _row("b", "orig", "flip")])

        result, _report = dedupe_stimuli(stimuli)

        assert list(result["post_id"]) == ["b"]


class TestBuildDedupeReport:
    """Tests for build_dedupe_report."""

    def test_dedupe_report_counts(self) -> None:
        """The report records raw, removed, and remaining counts."""
        before = pd.DataFrame([_row("c", "x", "y"), _row("a", "x", "z"), _row("b", "same", "same")])
        after, report = dedupe_stimuli(before)
        expected_keys = REPORT_KEYS

        result = build_dedupe_report(before, after, 1, 1)

        assert set(result) == expected_keys
        assert report["n_after_dedupe"] == 1
        assert list(after["post_id"]) == ["a"]


class TestLiveDedupe:
    """Tests for dedupe on the live stimulus catalog."""

    def test_live_stimuli_counts(self) -> None:
        """Live stimuli shrink from 20000 to 19763."""
        stimuli = load_stimuli_posts()

        _deduped, report = dedupe_stimuli(stimuli)

        assert len(stimuli) == 20000
        assert report["n_removed_duplicate_original"] == 205
        assert report["n_removed_identical_pair"] == 32
        assert report["n_after_dedupe"] == 19763
