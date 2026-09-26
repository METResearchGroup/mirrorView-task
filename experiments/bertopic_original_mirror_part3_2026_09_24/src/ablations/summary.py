"""Shared ablation metrics and the summary table."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
from scipy.stats import spearmanr
from sklearn.metrics import adjusted_rand_score

from experiments.bertopic_original_mirror_part3_2026_09_24.src import paths

SUMMARY_COLUMNS = [
    "ablation_id",
    "run_ts",
    "setting_changed",
    "setting_value",
    "n_topics",
    "n_noise",
    "noise_share",
    "ari_vs_production",
    "nmi_vs_production",
    "spearman_q5_keep_rate",
    "q2_pair_agreement",
    "q3_role_dominated_topics",
    "notes",
]


def pairwise_ari_hungarian(labels_a: list[int], labels_b: list[int]) -> float:
    """Adjusted Rand index of two labelings.

    Adjusted Rand is invariant to topic-id permutation, which is the
    quantity left after a one-to-one topic match.
    """
    return float(adjusted_rand_score(labels_a, labels_b))


def spearman_q5_keep_rate(production_rates: list[float], ablation_rates: list[float]) -> float:
    """Spearman correlation of aligned per-topic keep rates."""
    if len(production_rates) < 2 or len(ablation_rates) < 2:
        return float("nan")
    rho, _pvalue = spearmanr(production_rates, ablation_rates)
    return float(rho)


def append_summary_row(row: dict) -> Path:
    """Append one ablation setting to ``outputs/ablations/summary.csv``."""
    path = paths.ablations_dir() / "summary.csv"
    path.parent.mkdir(parents=True, exist_ok=True)
    frame = pd.DataFrame([{column: row.get(column) for column in SUMMARY_COLUMNS}])
    if path.exists():
        existing = pd.read_csv(path)
        frame = pd.concat([existing, frame], ignore_index=True)
    frame.to_csv(path, index=False)
    return path
