"""Mine atomic criteria from GEPA final prompts and compare to human addendum."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import pandas as pd

from experiments.predict_keep_remove_jev_gepa_2026_09_23.analysis.synonyms import SYNONYM_MAP

EXPERIMENT_ROOT = Path(__file__).resolve().parents[1]
GEPA_OUTPUTS = EXPERIMENT_ROOT / "jev_gepa" / "outputs"
HUMAN_PROMPT_PATH = (
    EXPERIMENT_ROOT.parent
    / "llm_prompt_engineering_2026_08_05"
    / "prompt.py"
)
MIN_CRITERION_LENGTH = 8
CRITERIA_HOLDOUT_SEED = 20260924

ABLATION_PROMPT_PATHS: dict[str, Path] = {
    "B1_gepa_pair": GEPA_OUTPUTS / "B1_gepa_pair" / "final_prompt.txt",
    "B1T_gepa_pair_terra": GEPA_OUTPUTS / "B1T_gepa_pair_terra" / "final_prompt.txt",
    "B2_gepa_original": GEPA_OUTPUTS / "B2_gepa_original" / "final_prompt.txt",
    "B3_gepa_mirror": GEPA_OUTPUTS / "B3_gepa_mirror" / "final_prompt.txt",
    "B4_gepa_asymmetric_reward": GEPA_OUTPUTS
    / "B4_gepa_asymmetric_reward"
    / "final_prompt.txt",
}

NUMBERED_ITEM_PATTERN = re.compile(r"^\s*(?:\d+[\.)]|[-*•])\s+(.+)$", re.MULTILINE)


def split_into_atomic_criteria(prompt_text: str) -> list[str]:
    """Split on numbered lists, bullets, and newlines."""
    criteria: list[str] = []
    for match in NUMBERED_ITEM_PATTERN.finditer(prompt_text):
        fragment = match.group(1).strip()
        if len(fragment) >= MIN_CRITERION_LENGTH:
            criteria.append(fragment)

    if criteria:
        return criteria

    for line in prompt_text.splitlines():
        fragment = line.strip()
        if len(fragment) >= MIN_CRITERION_LENGTH and not fragment.startswith("#"):
            criteria.append(fragment)
    return criteria


def normalize_criterion(text: str, synonyms: dict[str, str]) -> str:
    """Lowercase, strip, apply conservative hardcoded synonym merges."""
    normalized = " ".join(text.lower().strip().split())
    for source, target in sorted(synonyms.items(), key=lambda item: len(item[0]), reverse=True):
        normalized = normalized.replace(source.lower(), target.lower())
    return normalized


def load_human_mined_criteria() -> list[str]:
    """Parse KEEP_REMOVE_FEATURES_ADDENDUM into atomic strings."""
    prompt_source = HUMAN_PROMPT_PATH.read_text(encoding="utf-8")
    match = re.search(
        r'KEEP_REMOVE_FEATURES_ADDENDUM\s*=\s*"""(.*?)"""',
        prompt_source,
        re.DOTALL,
    )
    if match is None:
        raise ValueError("KEEP_REMOVE_FEATURES_ADDENDUM not found")
    return split_into_atomic_criteria(match.group(1))


def _best_human_match(
    gepa_criterion: str,
    human_criteria: list[str],
    *,
    synonyms: dict[str, str],
) -> tuple[str, bool, str]:
    normalized_gepa = normalize_criterion(gepa_criterion, synonyms)
    best_human = ""
    best_score = 0.0
    for human_criterion in human_criteria:
        normalized_human = normalize_criterion(human_criterion, synonyms)
        if normalized_gepa == normalized_human:
            return human_criterion, True, "exact_normalized"
        if normalized_gepa in normalized_human or normalized_human in normalized_gepa:
            score = min(len(normalized_gepa), len(normalized_human)) / max(
                len(normalized_gepa),
                len(normalized_human),
                1,
            )
            if score > best_score:
                best_score = score
                best_human = human_criterion
    if best_human:
        return best_human, True, "substring_synonym"
    return "", False, "no_conservative_match"


def compare_criteria(
    gepa_criteria: list[str],
    human_criteria: list[str],
    *,
    synonyms: dict[str, str],
) -> pd.DataFrame:
    """Compare GEPA criteria to human addendum with conservative matching."""
    rows: list[dict[str, object]] = []
    for gepa_criterion in gepa_criteria:
        best_human, matched, notes = _best_human_match(
            gepa_criterion,
            human_criteria,
            synonyms=synonyms,
        )
        rows.append(
            {
                "gepa_criterion": gepa_criterion,
                "best_human_match": best_human,
                "exact_or_synonym_match": matched,
                "notes": notes,
            }
        )
    return pd.DataFrame(rows)


def held_out_spot_check(
    gepa_criteria: list[str],
    *,
    holdout_fraction: float = 0.2,
    seed: int = CRITERIA_HOLDOUT_SEED,
) -> pd.DataFrame:
    """Reserve holdout_fraction of criteria for manual review rows."""
    import random

    rng = random.Random(seed)
    indexed = list(enumerate(gepa_criteria))
    rng.shuffle(indexed)
    holdout_size = max(1, int(round(len(gepa_criteria) * holdout_fraction)))
    holdout_ids = {index for index, _criterion in indexed[:holdout_size]}

    rows: list[dict[str, object]] = []
    for index, criterion in enumerate(gepa_criteria):
        split_name = "holdout" if index in holdout_ids else "mining"
        rows.append(
            {
                "criterion_index": index,
                "criterion": criterion,
                "split": split_name,
                "manual_review_status": "pending",
            }
        )
    return pd.DataFrame(rows)


def run_criteria_mining(*, output_dir: Path) -> dict[str, Any]:
    """Process all GEPA ablations and write criteria comparison outputs."""
    output_dir.mkdir(parents=True, exist_ok=True)
    human_criteria = load_human_mined_criteria()
    pd.DataFrame({"human_criterion": human_criteria}).to_csv(
        output_dir / "human_criteria.csv",
        index=False,
    )

    comparison_frames: list[pd.DataFrame] = []
    spot_check_frames: list[pd.DataFrame] = []
    summary: dict[str, Any] = {
        "ablations_processed": 0,
        "human_criteria_count": len(human_criteria),
        "per_ablation": {},
    }

    for ablation_id, prompt_path in ABLATION_PROMPT_PATHS.items():
        prompt_text = prompt_path.read_text(encoding="utf-8")
        gepa_criteria = split_into_atomic_criteria(prompt_text)
        pd.DataFrame({"gepa_criterion": gepa_criteria}).to_csv(
            output_dir / f"{ablation_id}_atomic_criteria.csv",
            index=False,
        )

        comparison = compare_criteria(
            gepa_criteria,
            human_criteria,
            synonyms=SYNONYM_MAP,
        )
        comparison.insert(0, "ablation_id", ablation_id)
        comparison.to_csv(output_dir / f"{ablation_id}_comparison.csv", index=False)
        comparison_frames.append(comparison)

        spot_check = held_out_spot_check(gepa_criteria)
        spot_check.insert(0, "ablation_id", ablation_id)
        spot_check.to_csv(output_dir / f"{ablation_id}_spot_check.csv", index=False)
        spot_check_frames.append(spot_check)

        matched_count = int(comparison["exact_or_synonym_match"].sum())
        summary["per_ablation"][ablation_id] = {
            "gepa_criteria_count": len(gepa_criteria),
            "matched_count": matched_count,
            "novel_count": len(gepa_criteria) - matched_count,
        }
        summary["ablations_processed"] += 1

    combined = pd.concat(comparison_frames, ignore_index=True)
    combined.to_csv(output_dir / "comparison_summary.csv", index=False)
    pd.concat(spot_check_frames, ignore_index=True).to_csv(
        output_dir / "spot_check_all.csv",
        index=False,
    )

    summary["total_gepa_criteria"] = int(len(combined))
    summary["total_matched"] = int(combined["exact_or_synonym_match"].sum())
    summary["total_novel"] = int(summary["total_gepa_criteria"] - summary["total_matched"])
    (output_dir / "criteria_mining_summary.json").write_text(
        json.dumps(summary, indent=2),
        encoding="utf-8",
    )
    return summary
