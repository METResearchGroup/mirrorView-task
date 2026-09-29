"""Mining prompts and LabelTask construction for step 2."""

from __future__ import annotations

import pandas as pd

from data_platform.generate_features.models import LabelTask

SYSTEM_PROMPT: str = ""
USER_TEMPLATE: str = ""


def render_pair_list(pairs: list[tuple[str, str]]) -> str:
    raise NotImplementedError


def render_user_prompt(
    kept_pairs: list[tuple[str, str]], removed_pairs: list[tuple[str, str]]
) -> str:
    raise NotImplementedError


def build_mining_tasks(batches: list[dict], cohort: pd.DataFrame) -> list[LabelTask]:
    raise NotImplementedError
