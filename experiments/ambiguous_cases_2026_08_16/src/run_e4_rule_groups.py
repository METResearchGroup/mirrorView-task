"""Join free-response rule groups to disagreements (E4).

Run from repo root::

    PYTHONPATH=. uv run python experiments/ambiguous_cases_2026_08_16/src/run_e4_rule_groups.py
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

EXPERIMENT_ROOT = Path(__file__).resolve().parents[1]
TRIAL_FRAME_CSV = EXPERIMENT_ROOT / "outputs" / "frames" / "trial_frame.csv"
POST_FRAME_CSV = EXPERIMENT_ROOT / "outputs" / "frames" / "post_frame.csv"
RATER_EFFECTS_CSV = EXPERIMENT_ROOT / "outputs" / "e2" / "rater_effects.csv"
RATER_RULE_GROUPS_CSV = EXPERIMENT_ROOT / "outputs" / "e4" / "rater_rule_groups.csv"
GROUP_SEVERITY_CSV = EXPERIMENT_ROOT / "outputs" / "e4" / "group_severity.csv"
SUMMARY_JSON = EXPERIMENT_ROOT / "outputs" / "e4" / "summary.json"

_CLUSTER_ROOT = (
    Path(__file__).resolve().parents[2]
    / "mine_free_response_for_features_2026_08_03"
    / "part_2_mine_free_responses"
    / "outputs"
    / "clusters"
)
_SEED = 42
_N_PERM = 200
_UNASSIGNED = "unassigned"


def _latest_assignment_path(band: str) -> Path:
    """Return the latest timestamped HDBSCAN assignment file for a band."""
    band_dir = _CLUSTER_ROOT / band
    dirs = sorted([d for d in band_dir.iterdir() if d.is_dir()])
    if not dirs:
        raise FileNotFoundError(f"No cluster directories under {band_dir}")
    path = dirs[-1] / "assignments_hdbscan.json"
    if not path.is_file():
        raise FileNotFoundError(path)
    return path


def _modal_rule_group(assignments: list[dict], band: str) -> dict[str, str]:
    """Map participant_id to modal non-noise cluster label."""
    by_participant: dict[str, list[int]] = {}
    for row in assignments:
        participant_id = str(row.get("participant_id", "")).strip()
        cluster_id = int(row.get("cluster_id", -1))
        if not participant_id or cluster_id < 0:
            continue
        by_participant.setdefault(participant_id, []).append(cluster_id)
    mapping: dict[str, str] = {}
    for participant_id, clusters in by_participant.items():
        values, counts = np.unique(clusters, return_counts=True)
        modal = int(values[int(np.argmax(counts))])
        mapping[participant_id] = f"{band}_cluster_{modal}"
    return mapping


def _build_rater_rule_groups(all_raters: pd.Series) -> pd.DataFrame:
    """Build the rater-to-rule-group mapping table."""
    mapping: dict[str, str] = {}
    for band in ("high", "low"):
        assignments = json.loads(_latest_assignment_path(band).read_text(encoding="utf-8"))
        mapping.update(_modal_rule_group(assignments, band))
    rows = []
    for participant_id in all_raters.astype(str).unique():
        rows.append(
            {
                "participant_id": participant_id,
                "rule_group": mapping.get(participant_id, _UNASSIGNED),
            }
        )
    return pd.DataFrame(rows)


def _disagree_pairs(trials: pd.DataFrame, posts: pd.DataFrame) -> pd.DataFrame:
    """Build unordered disagreeing rater pairs on posts with three-plus raters."""
    eligible = set(posts["post_id"].astype(str))
    frame = trials[trials["post_id"].astype(str).isin(eligible)].copy()
    pairs: list[dict] = []
    for post_id, group in frame.groupby("post_id"):
        raters = group[["participant_id", "is_remove"]].drop_duplicates("participant_id")
        ids = raters["participant_id"].tolist()
        removes = raters["is_remove"].tolist()
        for i in range(len(ids)):
            for j in range(i + 1, len(ids)):
                if removes[i] == removes[j]:
                    continue
                a, b = sorted([str(ids[i]), str(ids[j])])
                pairs.append(
                    {
                        "post_id": post_id,
                        "rater_a": a,
                        "rater_b": b,
                    }
                )
    return pd.DataFrame(pairs)


def _cross_group_share(pairs: pd.DataFrame, labels: dict[str, str]) -> tuple[float, int]:
    """Return share of disagreeing pairs with different assigned rule groups."""
    used = 0
    cross = 0
    for row in pairs.itertuples(index=False):
        group_a = labels.get(row.rater_a, _UNASSIGNED)
        group_b = labels.get(row.rater_b, _UNASSIGNED)
        if group_a == _UNASSIGNED or group_b == _UNASSIGNED:
            continue
        used += 1
        if group_a != group_b:
            cross += 1
    if used == 0:
        return float("nan"), 0
    return float(cross / used), used


def run_e4() -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    """Join rule groups and write E4 outputs."""
    trials = pd.read_csv(TRIAL_FRAME_CSV)
    posts = pd.read_csv(POST_FRAME_CSV)
    rater_effects = pd.read_csv(RATER_EFFECTS_CSV)

    mapping = _build_rater_rule_groups(trials["participant_id"])
    empirical = (
        trials.groupby("participant_id")
        .agg(empirical_remove_rate=("is_remove", "mean"))
        .reset_index()
    )
    mapping = mapping.merge(empirical, on="participant_id", how="left")
    mapping = mapping.merge(
        rater_effects[["participant_id", "rater_effect"]],
        on="participant_id",
        how="left",
    )

    severity = (
        mapping[mapping["rule_group"] != _UNASSIGNED]
        .groupby("rule_group")
        .agg(
            n_raters=("participant_id", "size"),
            mean_empirical_remove_rate=("empirical_remove_rate", "mean"),
            mean_rater_effect=("rater_effect", "mean"),
        )
        .reset_index()
    )

    pairs = _disagree_pairs(trials, posts)
    labels = dict(zip(mapping["participant_id"], mapping["rule_group"], strict=True))
    observed, n_used = _cross_group_share(pairs, labels)

    rng = np.random.default_rng(_SEED)
    assigned = mapping[mapping["rule_group"] != _UNASSIGNED].copy()
    assigned_ids = assigned["participant_id"].tolist()
    assigned_groups = assigned["rule_group"].to_numpy()
    null_shares = []
    for _ in range(_N_PERM):
        shuffled = dict(
            zip(assigned_ids, rng.permutation(assigned_groups), strict=True)
        )
        share, _ = _cross_group_share(pairs, shuffled)
        if not np.isnan(share):
            null_shares.append(share)
    null_mean = float(np.mean(null_shares)) if null_shares else float("nan")
    null_p = (
        float(np.mean([s >= observed for s in null_shares]))
        if null_shares and not np.isnan(observed)
        else float("nan")
    )

    summary = {
        "n_raters_assigned": int((mapping["rule_group"] != _UNASSIGNED).sum()),
        "n_raters_unassigned": int((mapping["rule_group"] == _UNASSIGNED).sum()),
        "observed_cross_group_share": observed,
        "null_mean_cross_group_share": null_mean,
        "null_p_greater": null_p,
        "n_disagree_pairs_used": n_used,
        "seed": _SEED,
    }

    RATER_RULE_GROUPS_CSV.parent.mkdir(parents=True, exist_ok=True)
    mapping.to_csv(RATER_RULE_GROUPS_CSV, index=False)
    severity.to_csv(GROUP_SEVERITY_CSV, index=False)
    SUMMARY_JSON.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    return mapping, severity, summary


def main() -> None:
    """CLI entry for E4."""
    mapping, severity, summary = run_e4()
    print(f"Wrote {RATER_RULE_GROUPS_CSV}")
    print(f"Wrote {GROUP_SEVERITY_CSV}")
    print(f"Wrote {SUMMARY_JSON}")
    print(f"n_raters {len(mapping)}")
    print(f"n_groups {len(severity)}")
    print(f"observed_cross_group_share {summary['observed_cross_group_share']:.6f}")


if __name__ == "__main__":
    main()
