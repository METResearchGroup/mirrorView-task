"""Stage A Jev baseline runner for cohort A ablations A1 through A4.

Run from the repo root:

    PYTHONPATH=. uv run python experiments/predict_keep_remove_jev_gepa_2026_09_23/jev_baseline/run.py --ablation-id A1_pair_study_prompt
"""

from __future__ import annotations

import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[3]
_SCRIPT_DIR = str(Path(__file__).resolve().parent)
if sys.path and sys.path[0] == _SCRIPT_DIR:
    sys.path.pop(0)
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

import argparse
import json
from dataclasses import dataclass
from typing import Any

import pandas as pd

from experiments.predict_keep_remove_jev_gepa_2026_09_23.shared import jev_scorer
from experiments.predict_keep_remove_jev_gepa_2026_09_23.shared.metrics import build_results_payload
from experiments.predict_keep_remove_jev_gepa_2026_09_23.shared.splits import COHORT_PARQUET

ABLATION_IDS: tuple[str, ...] = (
    "A1_pair_study_prompt",
    "A2_original_only",
    "A3_mirror_only",
    "A4_pair_features_addendum",
)

EXPERIMENT_ROOT = _REPO_ROOT / "experiments/predict_keep_remove_jev_gepa_2026_09_23"
OUTPUT_ROOT = EXPERIMENT_ROOT / "jev_baseline/outputs"


@dataclass(frozen=True)
class AblationConfig:
    ablation_id: str
    view: str
    add_criteria: bool
    output_dir: Path
    wandb_name: str


def resolve_ablation(ablation_id: str) -> AblationConfig:
    """Map ablation_id to view, prompt arm, output dir, and Wandb run name."""
    raise NotImplementedError


def build_post_tasks(
    cohort: pd.DataFrame,
    *,
    view: str,
    add_criteria: bool,
) -> list[jev_scorer.PostTask]:
    """Shuffle post_ids and build PostTask list for scoring."""
    raise NotImplementedError


def score_ablation(
    ablation_id: str,
    *,
    cohort_path: Path,
    output_dir: Path,
    resume: bool = True,
) -> Path:
    """Score cohort A for one ablation and return output_dir."""
    raise NotImplementedError


def finalize_ablation(output_dir: Path, cohort: pd.DataFrame) -> dict[str, Any]:
    """Join predictions, write labels/requests parquet and results.json."""
    raise NotImplementedError


def main(argv: list[str] | None = None) -> None:
    """CLI: --ablation-id (required), --cohort-path, --all, --no-resume."""
    parser = argparse.ArgumentParser(description="Stage A Jev baseline runner")
    parser.add_argument("--ablation-id", choices=ABLATION_IDS)
    parser.add_argument("--cohort-path", type=Path, default=COHORT_PARQUET)
    parser.add_argument("--all", action="store_true")
    parser.add_argument("--no-resume", action="store_true")
    args = parser.parse_args(argv)

    if not args.all and args.ablation_id is None:
        parser.error("pass --ablation-id or --all")

    ablation_ids = ABLATION_IDS if args.all else (args.ablation_id,)
    for ablation in ablation_ids:
        config = resolve_ablation(ablation)
        score_ablation(
            ablation,
            cohort_path=args.cohort_path,
            output_dir=config.output_dir,
            resume=not args.no_resume,
        )


if __name__ == "__main__":
    main(sys.argv[1:])  # pragma: no cover
