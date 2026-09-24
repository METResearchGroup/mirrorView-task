"""Path helpers for the Part 3 original and mirror BERTopic experiment.

Run from repo root::

    PYTHONPATH=. uv run python -c \\
      "from experiments.bertopic_original_mirror_part3_2026_09_24.src import paths; print(paths.embeddings_dir('original'))"
"""

from __future__ import annotations

from pathlib import Path

EXPERIMENT_ROOT = Path(__file__).resolve().parents[1]
ALLOWED_TEXT_ROLES = frozenset({"original", "mirror", "joint"})


def embeddings_dir(role: str) -> Path:
    raise NotImplementedError


def embeddings_minilm_dir(role: str) -> Path:
    raise NotImplementedError


def topics_dir(role: str) -> Path:
    raise NotImplementedError


def labels_dir(role: str) -> Path:
    raise NotImplementedError


def figures_dir(role: str) -> Path:
    raise NotImplementedError


def analyses_dir() -> Path:
    raise NotImplementedError


def ablations_dir() -> Path:
    raise NotImplementedError


def dedupe_report_path() -> Path:
    raise NotImplementedError


def new_run_timestamp() -> str:
    raise NotImplementedError
