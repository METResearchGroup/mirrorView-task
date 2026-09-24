"""Mine atomic criteria from GEPA final prompts and compare to human addendum."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

EXPERIMENT_ROOT = Path(__file__).resolve().parents[1]
GEPA_OUTPUTS = EXPERIMENT_ROOT / "jev_gepa" / "outputs"

ABLATION_PROMPT_PATHS: dict[str, Path] = {
    "B1_gepa_pair": GEPA_OUTPUTS / "B1_gepa_pair" / "final_prompt.txt",
    "B1T_gepa_pair_terra": GEPA_OUTPUTS / "B1T_gepa_pair_terra" / "final_prompt.txt",
    "B2_gepa_original": GEPA_OUTPUTS / "B2_gepa_original" / "final_prompt.txt",
    "B3_gepa_mirror": GEPA_OUTPUTS / "B3_gepa_mirror" / "final_prompt.txt",
    "B4_gepa_asymmetric_reward": GEPA_OUTPUTS
    / "B4_gepa_asymmetric_reward"
    / "final_prompt.txt",
}


def split_into_atomic_criteria(prompt_text: str) -> list[str]:
    """Split on numbered lists, bullets, and newlines."""
    raise NotImplementedError


def normalize_criterion(text: str, synonyms: dict[str, str]) -> str:
    """Lowercase, strip, apply conservative hardcoded synonym merges."""
    raise NotImplementedError


def load_human_mined_criteria() -> list[str]:
    """Parse KEEP_REMOVE_FEATURES_ADDENDUM into atomic strings."""
    raise NotImplementedError


def compare_criteria(
    gepa_criteria: list[str],
    human_criteria: list[str],
    *,
    synonyms: dict[str, str],
) -> pd.DataFrame:
    """Compare GEPA criteria to human addendum with conservative matching."""
    raise NotImplementedError


def held_out_spot_check(
    gepa_criteria: list[str],
    *,
    holdout_fraction: float = 0.2,
    seed: int = 20260924,
) -> pd.DataFrame:
    """Reserve holdout_fraction of criteria for manual review rows."""
    raise NotImplementedError


def run_criteria_mining(*, output_dir: Path) -> dict[str, Any]:
    """Process all GEPA ablations and write criteria comparison outputs."""
    raise NotImplementedError
