"""Build the five-label cohort with modal labels and stimulus text."""

import pandas as pd


def assign_modal_label(counts: pd.DataFrame) -> pd.DataFrame:
    raise NotImplementedError


def attach_pair_text(labeled: pd.DataFrame, stimuli: pd.DataFrame) -> pd.DataFrame:
    raise NotImplementedError


def build_cohort(results: pd.DataFrame, stimuli: pd.DataFrame) -> pd.DataFrame:
    raise NotImplementedError
