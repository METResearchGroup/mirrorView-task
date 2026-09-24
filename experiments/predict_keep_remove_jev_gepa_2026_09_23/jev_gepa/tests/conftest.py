"""Shared fixtures for jev_gepa tests."""

from __future__ import annotations

import pytest

from experiments.predict_keep_remove_jev_gepa_2026_09_23.jev_gepa.adapter import JevDataInst


@pytest.fixture
def sample_jev_data_inst() -> JevDataInst:
    return JevDataInst(
        post_id="post-1",
        original_text="original text",
        mirror_text="mirror text",
        post_1_role="original",
        post_2_role="mirror",
        label=1,
        n_keep=2,
        n_remove=8,
        n_raters=10,
        sampled_stance="liberal",
        sample_toxicity_type="insult",
    )
