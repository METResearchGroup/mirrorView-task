"""Skip preprocess candidates that were already used as study stimuli.

Run this import from the repo root with

    PYTHONPATH=. uv run python -c \\
        "from data_platform.preprocessing.previously_used_stimuli import load_previously_used_stimuli_ids"
"""

from __future__ import annotations


def extract_stimuli_ids(frame, dataset_name):
    raise NotImplementedError


def load_previously_used_stimuli_ids():
    raise NotImplementedError


def filter_previously_used_stimuli(records, stimuli_ids):
    raise NotImplementedError
