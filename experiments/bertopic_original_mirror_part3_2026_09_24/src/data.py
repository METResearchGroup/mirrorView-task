"""Load Part 3 stimuli and keep/remove labels for BERTopic.

Run from repo root::

    PYTHONPATH=. uv run python -c \\
      "from experiments.bertopic_original_mirror_part3_2026_09_24.src.data import load_stimuli_posts"
"""

from __future__ import annotations

import pandas as pd

POST_ID_COLUMN = "post_id"


def load_stimuli_posts() -> pd.DataFrame:
    raise NotImplementedError


def load_keep_remove_posts() -> pd.DataFrame:
    raise NotImplementedError


def select_text_column(role: str) -> str:
    raise NotImplementedError


def texts_for_role(frame: pd.DataFrame, role: str) -> list[str]:
    raise NotImplementedError


def build_joint_frame(deduped: pd.DataFrame) -> pd.DataFrame:
    raise NotImplementedError


def load_fit_corpus(role: str) -> pd.DataFrame:
    raise NotImplementedError
