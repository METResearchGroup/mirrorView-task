"""Generate dataset metrics for the keep/remove prediction dataset.

How to run (from repo root):

PYTHONPATH=. uv run python experiments/predict_keep_remove_2026_05_07/generate_dataset_metrics.py

This prints:
- Unique counts (rows, unique posts, unique participants, unique text pairs).
- Distributions for key contextual variables (counts + percents).

Notes:
- Metrics are computed on the linked-fate subset with `decision ∈ {keep, remove}`.
- If the most recent `scripts/mirrorview_pilot_data_*.csv` export is malformed or
  missing expected columns, the script falls back to the most recent export that
  has the required schema.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
import re

import pandas as pd

from experiments.mirrors_content_analysis_2026_04_24.dataloader import (
    Dataloader as MirrorViewPilotDataloader,
)
from experiments.predict_keep_remove_2026_05_07.dataloader import Dataloader
from experiments.predict_keep_remove_2026_05_07.embeddings.text_hash import text_hash


@dataclass(frozen=True)
class DistributionSummary:
    variable: str
    n_rows: int
    n_categories: int
    max_pct: float
    min_pct: float
    max_to_min_ratio: float


def _distribution_table(df: pd.DataFrame, column: str) -> tuple[pd.DataFrame, DistributionSummary]:
    s = df[column]
    # Keep missingness visible as a category (useful for data-quality reporting).
    s = s.astype("string")
    s = s.fillna("<NA>")

    counts = s.value_counts(dropna=False)
    out = counts.rename("n").to_frame().reset_index()
    # pandas may name the reset_index() column either "index" or the series name.
    out = out.rename(columns={out.columns[0]: "category"})
    out.insert(0, "variable", column)
    out["pct"] = (out["n"] / max(int(out["n"].sum()), 1) * 100.0).astype(float)

    if len(out):
        max_pct = float(out["pct"].max())
        min_pct = float(out["pct"].min())
        ratio = float("inf") if min_pct == 0 else float(max_pct / min_pct)
    else:
        max_pct = float("nan")
        min_pct = float("nan")
        ratio = float("nan")

    summary = DistributionSummary(
        variable=column,
        n_rows=int(len(df)),
        n_categories=int(out["category"].nunique(dropna=False)),
        max_pct=max_pct,
        min_pct=min_pct,
        max_to_min_ratio=ratio,
    )
    return out, summary


_EXPORT_TS_RE = re.compile(
    r"^mirrorview_pilot_data_(\d{4}_\d{2}_\d{2}-\d{2}:\d{2}:\d{2})\.csv$"
)
_EXPORT_DATE_RE = re.compile(r"^mirrorview_pilot_data_(\d{4}-\d{2}-\d{2})\.csv$")
_EXPORT_TS_FMT = "%Y_%m_%d-%H:%M:%S"
_EXPORT_DATE_FMT = "%Y-%m-%d"


def _parse_export_time(path: Path) -> datetime | None:
    m = _EXPORT_TS_RE.match(path.name)
    if m:
        return datetime.strptime(m.group(1), _EXPORT_TS_FMT)
    m = _EXPORT_DATE_RE.match(path.name)
    if m:
        return datetime.strptime(m.group(1), _EXPORT_DATE_FMT)
    return None


def _choose_latest_valid_export_csv(
    scripts_dir: Path,
    *,
    required_columns: set[str],
) -> Path:
    candidates = sorted(scripts_dir.glob("mirrorview_pilot_data_*.csv"))
    if not candidates:
        raise FileNotFoundError(f"No mirrorview_pilot_data_*.csv under {scripts_dir}")

    valid: list[tuple[datetime, Path]] = []
    for p in candidates:
        try:
            cols = set(pd.read_csv(p, nrows=0).columns)
        except Exception:
            continue
        if not required_columns.issubset(cols):
            continue

        ts = _parse_export_time(p)
        if ts is None:
            ts = datetime.fromtimestamp(p.stat().st_mtime)
        valid.append((ts, p))

    if not valid:
        raise RuntimeError(
            "Found mirrorview_pilot_data_*.csv files, but none had the required columns: "
            f"{sorted(required_columns)}"
        )

    valid.sort(key=lambda t: t[0])
    return valid[-1][1]


def _load_linked_fate_keep_remove_rows() -> pd.DataFrame:
    """Load the decision-row dataset: linked-fate keep/remove trials only."""
    try:
        # Preferred path: use the experiment's canonical dataloader.
        loader = Dataloader()
        return loader.load_training_dataframe()
    except Exception:
        # Fallback: choose a valid export and apply the same filtering logic.
        pilot = MirrorViewPilotDataloader()
        raw_required = {
            "trial_type",
            "phase",
            "prolific_id",
            "party_group",
            "condition",
            "evaluation_mode",
            "sample_toxicity_type",
            "sampled_stance",
            "post_id",
            "original_text",
            "mirror_text",
            "decision",
        }
        export_path = _choose_latest_valid_export_csv(
            pilot.SCRIPTS_DIR,
            required_columns=raw_required,
        )
        raw = pd.read_csv(export_path, low_memory=False)
        trials = pilot.transform_latest_mirrorview_run_data(raw)

        out = trials.copy()
        out["evaluation_mode"] = out["evaluation_mode"].astype(str).str.lower().str.strip()
        out = out[out["evaluation_mode"] == "linked_fate"].copy()
        out["decision"] = out["decision"].astype(str).str.lower().str.strip()
        out = out[out["decision"].isin(["keep", "remove"])].copy()
        return out


def main() -> None:
    """Print dataset metrics for the linked-fate keep/remove decision rows."""
    df = _load_linked_fate_keep_remove_rows().copy()

    required = [
        "post_id",
        "prolific_id",
        "original_text",
        "mirror_text",
        "party_group",
        "condition",
        "sample_toxicity_type",
        "sampled_stance",
    ]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise KeyError(f"Dataset is missing required columns: {missing}")

    # Approximate unique (original_text, mirror_text) pairs using stable text hashes.
    orig_hash = df["original_text"].fillna("").astype(str).map(text_hash)
    mirr_hash = df["mirror_text"].fillna("").astype(str).map(text_hash)
    pair_hash = (orig_hash + "||" + mirr_hash).map(text_hash)

    post_counts = df["post_id"].astype(str).value_counts(dropna=False)
    avg_rows_per_post_id = float(post_counts.mean()) if len(post_counts) else float("nan")

    overview = pd.DataFrame(
        [
            {"metric": "n_rows", "value": int(len(df))},
            {"metric": "unique_post_id", "value": int(df["post_id"].astype(str).nunique())},
            {"metric": "avg_rows_per_post_id", "value": avg_rows_per_post_id},
            {"metric": "unique_participants_prolific_id", "value": int(df["prolific_id"].astype(str).nunique())},
            {"metric": "unique_(original_text,mirror_text)_pairs__via_hash", "value": int(pair_hash.nunique())},
        ]
    )

    print("\n=== Dataset overview (linked-fate keep/remove decision rows) ===")
    print(overview.to_string(index=False))

    distribution_vars = [
        "party_group",
        "condition",
        "sample_toxicity_type",
        "sampled_stance",
    ]

    all_rows: list[pd.DataFrame] = []
    summaries: list[DistributionSummary] = []
    for col in distribution_vars:
        tab, summ = _distribution_table(df, col)
        all_rows.append(tab)
        summaries.append(summ)

    dist_df = pd.concat(all_rows, ignore_index=True)
    # Friendly ordering: group by variable, then descending pct.
    dist_df = dist_df.sort_values(["variable", "pct"], ascending=[True, False]).reset_index(drop=True)

    summary_df = pd.DataFrame([s.__dict__ for s in summaries]).sort_values("variable").reset_index(drop=True)

    print("\n=== Distribution tables ===")
    print(dist_df.to_string(index=False))

    print("\n=== Balance/imbalance summary (higher max_pct / higher max_to_min_ratio => less balanced) ===")
    print(summary_df.to_string(index=False))


if __name__ == "__main__":
    main()

