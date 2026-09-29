"""Build mining batches of kept and removed pairs."""

import numpy as np
import pandas as pd


def shuffled_post_ids(
    cohort: pd.DataFrame, modal_label: str, rng: np.random.Generator
) -> list[str]:
    raise NotImplementedError


def format_batch_id(index: int) -> str:
    raise NotImplementedError


def build_batches(cohort: pd.DataFrame, seed: int) -> list[dict]:
    raise NotImplementedError
