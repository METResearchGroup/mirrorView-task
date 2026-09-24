"""Shared fixtures for Part 3 keep/remove aggregation tests."""

from __future__ import annotations

import pandas as pd
import pytest


@pytest.fixture
def filter_input_frame() -> pd.DataFrame:
    """Mixed trial rows for filter_keep_remove_trials tests."""
    return pd.DataFrame(
        {
            "prolific_id": ["W1", "W1", "W2", "W3", "W4", "W5"],
            "post_id": ["X1", "X1", "X2", "X3", "X4", ""],
            "decision": ["keep", "remove", "keep", "KEEP", "keep", "keep"],
            "evaluation_mode": [
                "linked_fate",
                "linked_fate",
                "linked_fate",
                "linked_fate",
                "single",
                "linked_fate",
            ],
            "original_text": ["a", "a", "b", "c", "d", "e"],
            "mirror_text": ["a'", "a'", "b'", "c'", "d'", "e'"],
        }
    )


@pytest.fixture
def dedupe_conflict_frame() -> pd.DataFrame:
    """Worker W1 rates post X1 keep then remove (conflicting)."""
    return pd.DataFrame(
        {
            "prolific_id": ["W1", "W1"],
            "post_id": ["X1", "X1"],
            "decision": ["keep", "remove"],
            "evaluation_mode": ["linked_fate", "linked_fate"],
            "original_text": ["text", "text"],
            "mirror_text": ["mirror", "mirror"],
        }
    )


@pytest.fixture
def dedupe_duplicate_frame() -> pd.DataFrame:
    """Worker W1 rates post X1 keep twice (non-conflicting duplicate)."""
    return pd.DataFrame(
        {
            "prolific_id": ["W1", "W1"],
            "post_id": ["X1", "X1"],
            "decision": ["keep", "keep"],
            "evaluation_mode": ["linked_fate", "linked_fate"],
            "original_text": ["text", "text"],
            "mirror_text": ["mirror", "mirror"],
        }
    )


@pytest.fixture
def modal_trials_frame() -> pd.DataFrame:
    """Trials for modal aggregation: post A (2 keep, 1 remove), post B (1 keep, 1 remove)."""
    return pd.DataFrame(
        {
            "prolific_id": ["W1", "W2", "W3", "W4", "W5"],
            "post_id": ["A", "A", "A", "B", "B"],
            "decision": ["keep", "keep", "remove", "keep", "remove"],
            "original_text": ["oa", "oa", "oa", "ob", "ob"],
            "mirror_text": ["ma", "ma", "ma", "mb", "mb"],
        }
    )


@pytest.fixture
def modal_tie_frame() -> pd.DataFrame:
    """Post C with tied keep and remove counts."""
    return pd.DataFrame(
        {
            "prolific_id": ["W1", "W2"],
            "post_id": ["C", "C"],
            "decision": ["keep", "remove"],
            "original_text": ["oc", "oc"],
            "mirror_text": ["mc", "mc"],
        }
    )


@pytest.fixture
def modal_n_raters_frame() -> pd.DataFrame:
    """Post H with three unique raters (two keep, one remove)."""
    return pd.DataFrame(
        {
            "prolific_id": ["W1", "W2", "W3"],
            "post_id": ["H", "H", "H"],
            "decision": ["keep", "keep", "remove"],
            "original_text": ["oh", "oh", "oh"],
            "mirror_text": ["mh", "mh", "mh"],
        }
    )


@pytest.fixture
def modal_text_conflict_frame() -> pd.DataFrame:
    """One post_id with conflicting original_text."""
    return pd.DataFrame(
        {
            "prolific_id": ["W1", "W2"],
            "post_id": ["Z", "Z"],
            "decision": ["keep", "keep"],
            "original_text": ["text1", "text2"],
            "mirror_text": ["mirror", "mirror"],
        }
    )


@pytest.fixture
def unanimous_posts_frame() -> pd.DataFrame:
    """Post D (3 keep) and post E (2 keep)."""
    return pd.DataFrame(
        {
            "prolific_id": ["W1", "W2", "W3", "W4", "W5"],
            "post_id": ["D", "D", "D", "E", "E"],
            "decision": ["keep", "keep", "keep", "keep", "keep"],
            "original_text": ["od", "od", "od", "oe", "oe"],
            "mirror_text": ["md", "md", "md", "me", "me"],
        }
    )


@pytest.fixture
def unanimous_split_frame() -> pd.DataFrame:
    """Post F with split decisions across 4 trials."""
    return pd.DataFrame(
        {
            "prolific_id": ["W1", "W2", "W3", "W4"],
            "post_id": ["F", "F", "F", "F"],
            "decision": ["keep", "keep", "remove", "remove"],
            "original_text": ["of", "of", "of", "of"],
            "mirror_text": ["mf", "mf", "mf", "mf"],
        }
    )


@pytest.fixture
def unanimous_remove_frame() -> pd.DataFrame:
    """Post G with 4 remove ratings."""
    return pd.DataFrame(
        {
            "prolific_id": ["W1", "W2", "W3", "W4"],
            "post_id": ["G", "G", "G", "G"],
            "decision": ["remove", "remove", "remove", "remove"],
            "original_text": ["og", "og", "og", "og"],
            "mirror_text": ["mg", "mg", "mg", "mg"],
        }
    )
