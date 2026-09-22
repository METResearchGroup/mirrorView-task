"""Build aggregated study-progress metrics with no participant identifiers."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd

from experiments.study_progress_dashboard_2026_09_11.constants import (
    CELL_BY_STANCE_TOXICITY,
    CELL_TARGET_SLOTS,
    CONDITION,
    DECISION_KEEP,
    DECISION_ORDER,
    DECISION_REMOVE,
    EVALUATION_MODE_LINKED_FATE,
    KEEP_RATE_BIN_EDGES,
    KEEP_RATE_BIN_LABELS,
    PARTY_DEMOCRAT,
    PARTY_ORDER,
    PARTY_REPUBLICAN,
    POSTS_PER_USER,
    STANCE_ORDER,
    STUDY_BUCKET,
    STUDY_ID,
    STUDY_ITERATION_ID,
    TARGET_DEMOCRAT_SLOTS,
    TARGET_LABELS,
    TARGET_POSTS,
    TARGET_REPUBLICAN_SLOTS,
    TARGET_USERS,
    TOXICITY_ORDER,
    TRIAL_TYPE_MODERATION,
)


def first_non_empty(series: pd.Series) -> object:
    """Return the first non-null, non-blank value in ``series``."""
    for value in series:
        if pd.isna(value):
            continue
        if isinstance(value, str) and not value.strip():
            continue
        return value
    return pd.NA


def normalize_text(value: object) -> str:
    """Lowercase and strip a cell, returning "" for missing values."""
    if pd.isna(value):
        return ""
    return str(value).strip().lower()


def select_real_trials(export_df: pd.DataFrame) -> pd.DataFrame:
    """Return linked-fate keep/remove trials that have a stimulus post id.

    Practice trials have no ``post_id`` and are dropped.
    """
    if export_df.empty:
        return export_df.iloc[0:0].copy()

    trials = export_df.copy()
    trial_type = trials["trial_type"].map(normalize_text)
    decision = trials["decision"].map(normalize_text)
    post_id = trials["post_id"].astype("string").fillna("").str.strip()
    real = trials[
        (trial_type == TRIAL_TYPE_MODERATION)
        & post_id.ne("")
        & decision.isin(DECISION_ORDER)
    ].copy()
    real["decision"] = decision.loc[real.index]
    real["post_id"] = post_id.loc[real.index]
    real["party_group"] = trials.loc[real.index, "party_group"].map(normalize_text)
    real["sampled_stance"] = trials.loc[real.index, "sampled_stance"].map(normalize_text)
    real["sample_toxicity_type"] = trials.loc[
        real.index, "sample_toxicity_type"
    ].map(normalize_text)
    if "evaluation_mode" in real.columns:
        real["evaluation_mode"] = real["evaluation_mode"].map(normalize_text)
    real["response_time_ms"] = pd.to_numeric(
        real.get("response_time_ms"), errors="coerce"
    )
    real["cell"] = [
        CELL_BY_STANCE_TOXICITY.get((stance, toxicity))
        for stance, toxicity in zip(
            real["sampled_stance"], real["sample_toxicity_type"], strict=True
        )
    ]
    return real.reset_index(drop=True)


def build_user_frame(export_df: pd.DataFrame, trials: pd.DataFrame) -> pd.DataFrame:
    """Return one row per participant with party, attention, and keep/remove rates."""
    if export_df.empty:
        return pd.DataFrame(
            columns=[
                "prolific_id",
                "party_group",
                "political_affiliation",
                "party_lean",
                "attention_passed",
                "influence",
                "age",
                "gender",
                "education",
                "political_ideology",
                "session_minutes",
                "n_files",
                "n_trials",
                "n_keep",
                "n_remove",
                "keep_rate",
                "remove_rate",
                "median_rt_ms",
                "completed",
            ]
        )

    people = (
        export_df.groupby("prolific_id", as_index=False)
        .agg(
            party_group=("party_group", first_non_empty),
            political_affiliation=("political_affiliation", first_non_empty),
            party_lean=("party_lean", first_non_empty),
            attention_passed=("attention_check_passed", first_non_empty),
            influence=("phase1_pair_influence_rating", first_non_empty),
            age=("age", first_non_empty),
            gender=("gender", first_non_empty),
            education=("education", first_non_empty),
            political_ideology=("political_ideology", first_non_empty),
            session_ms=("time_elapsed", "max"),
        )
    )
    file_counts = (
        export_df.assign(
            _is_start=export_df["trial_index"].fillna(-1).astype(float).eq(0)
        )
        .groupby("prolific_id")["_is_start"]
        .sum()
        .astype(int)
    )
    people["n_files"] = people["prolific_id"].map(file_counts).fillna(1).astype(int)
    people.loc[people["n_files"] < 1, "n_files"] = 1
    people["party_group"] = people["party_group"].map(normalize_text)
    people["political_affiliation"] = people["political_affiliation"].map(normalize_text)
    people["party_lean"] = people["party_lean"].map(normalize_text)
    people["gender"] = people["gender"].map(normalize_text)
    people["education"] = people["education"].map(normalize_text)
    people["attention_passed"] = pd.to_numeric(people["attention_passed"], errors="coerce")
    people["influence"] = pd.to_numeric(people["influence"], errors="coerce")
    people["age"] = pd.to_numeric(people["age"], errors="coerce")
    people["political_ideology"] = pd.to_numeric(
        people["political_ideology"], errors="coerce"
    )
    people["session_minutes"] = pd.to_numeric(people["session_ms"], errors="coerce") / 60000.0

    trial_stats = (
        trials.groupby("prolific_id")
        .agg(
            n_trials=("decision", "size"),
            n_keep=("decision", lambda s: int((s == DECISION_KEEP).sum())),
            n_remove=("decision", lambda s: int((s == DECISION_REMOVE).sum())),
            median_rt_ms=("response_time_ms", "median"),
        )
        .reset_index()
    )
    users = people.merge(trial_stats, on="prolific_id", how="left")
    users["n_trials"] = users["n_trials"].fillna(0).astype(int)
    users["n_keep"] = users["n_keep"].fillna(0).astype(int)
    users["n_remove"] = users["n_remove"].fillna(0).astype(int)
    denom = users["n_trials"].replace(0, pd.NA)
    users["keep_rate"] = (users["n_keep"] / denom).astype(float)
    users["remove_rate"] = (users["n_remove"] / denom).astype(float)
    users["completed"] = users["n_trials"] >= POSTS_PER_USER
    return users


def numeric_summary(series: pd.Series) -> dict[str, float | int | None]:
    """Return count, mean, std, and selected quantiles for a numeric series."""
    values = pd.to_numeric(series, errors="coerce").dropna()
    if values.empty:
        return {
            "n": 0,
            "mean": None,
            "std": None,
            "min": None,
            "p05": None,
            "p25": None,
            "p50": None,
            "p75": None,
            "p95": None,
            "max": None,
        }
    return {
        "n": int(values.size),
        "mean": round(float(values.mean()), 4),
        "std": round(float(values.std(ddof=1)), 4) if values.size > 1 else 0.0,
        "min": round(float(values.min()), 4),
        "p05": round(float(values.quantile(0.05)), 4),
        "p25": round(float(values.quantile(0.25)), 4),
        "p50": round(float(values.quantile(0.50)), 4),
        "p75": round(float(values.quantile(0.75)), 4),
        "p95": round(float(values.quantile(0.95)), 4),
        "max": round(float(values.max()), 4),
    }


def rate_histogram(series: pd.Series) -> list[dict[str, Any]]:
    """Count per-user rates into 10-point bins from 0 to 1."""
    values = pd.to_numeric(series, errors="coerce").dropna()
    bins = pd.cut(
        values,
        bins=list(KEEP_RATE_BIN_EDGES),
        labels=list(KEEP_RATE_BIN_LABELS),
        include_lowest=True,
        right=True,
    )
    counts = bins.value_counts(sort=False)
    n = int(values.size)
    rows: list[dict[str, Any]] = []
    for label in KEEP_RATE_BIN_LABELS:
        count = int(counts.get(label, 0))
        rows.append(
            {
                "bin": label,
                "count": count,
                "share": round(count / n, 4) if n else 0.0,
            }
        )
    return rows


def _decision_share(trials: pd.DataFrame) -> dict[str, Any]:
    n = int(len(trials))
    n_keep = int((trials["decision"] == DECISION_KEEP).sum()) if n else 0
    n_remove = int((trials["decision"] == DECISION_REMOVE).sum()) if n else 0
    return {
        "n_trials": n,
        "n_keep": n_keep,
        "n_remove": n_remove,
        "keep_share": round(n_keep / n, 4) if n else None,
        "remove_share": round(n_remove / n, 4) if n else None,
    }


def _party_slice_metrics(users: pd.DataFrame, trials: pd.DataFrame) -> dict[str, Any]:
    completed = users[users["completed"]].copy()
    attention_known = completed.dropna(subset=["attention_passed"])
    n_attention_pass = int((attention_known["attention_passed"] == 1).sum())
    n_attention_fail = int((attention_known["attention_passed"] == 0).sum())
    affiliation = (
        completed["political_affiliation"].fillna("").value_counts().to_dict()
        if not completed.empty
        else {}
    )
    return {
        "n_completers": int(len(completed)),
        "n_files": int(completed["n_files"].sum()) if not completed.empty else 0,
        "n_repeat_submitters": int((completed["n_files"] > 1).sum()),
        "attention_passed": n_attention_pass,
        "attention_failed": n_attention_fail,
        "attention_pass_rate": round(n_attention_pass / len(attention_known), 4)
        if len(attention_known)
        else None,
        "affiliation": {
            "democrat": int(affiliation.get("democrat", 0)),
            "republican": int(affiliation.get("republican", 0)),
            "other": int(affiliation.get("other", 0)),
        },
        "trial_decisions": _decision_share(trials),
        "user_keep_rate": numeric_summary(completed["keep_rate"]),
        "user_remove_rate": numeric_summary(completed["remove_rate"]),
        "always_keep": int((completed["keep_rate"] == 1.0).sum()),
        "always_remove": int((completed["remove_rate"] == 1.0).sum()),
        "always_keep_passed": int(
            ((completed["attention_passed"] == 1) & (completed["keep_rate"] == 1.0)).sum()
        ),
        "always_keep_failed": int(
            ((completed["attention_passed"] == 0) & (completed["keep_rate"] == 1.0)).sum()
        ),
        "passed_user_remove_rate": numeric_summary(
            completed.loc[completed["attention_passed"] == 1, "remove_rate"]
        ),
        "failed_user_remove_rate": numeric_summary(
            completed.loc[completed["attention_passed"] == 0, "remove_rate"]
        ),
        "keep_rate_histogram": rate_histogram(completed["keep_rate"]),
        "remove_rate_histogram": rate_histogram(completed["remove_rate"]),
        "influence": numeric_summary(completed["influence"]),
        "session_minutes": numeric_summary(completed["session_minutes"]),
        "median_rt_ms": numeric_summary(completed["median_rt_ms"]),
        "age": numeric_summary(completed["age"]),
        "ideology": numeric_summary(completed["political_ideology"]),
        "gender": _count_map(completed["gender"]),
        "education": _count_map(completed["education"]),
    }


def _count_map(series: pd.Series) -> dict[str, int]:
    cleaned = series.fillna("unknown").map(lambda v: str(v).strip().lower() or "unknown")
    return {str(k): int(v) for k, v in cleaned.value_counts().items()}


def _crosstab_remove_rates(
    trials: pd.DataFrame, index_col: str, index_order: tuple[str, ...]
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for party in PARTY_ORDER:
        party_trials = trials[trials["party_group"] == party]
        for key in index_order:
            slice_trials = party_trials[party_trials[index_col] == key]
            share = _decision_share(slice_trials)
            rows.append(
                {
                    "party": party,
                    index_col: key,
                    **share,
                }
            )
    return rows


def _cell_coverage(trials: pd.DataFrame) -> list[dict[str, Any]]:
    counts = trials.groupby("cell").size() if not trials.empty else pd.Series(dtype=int)
    rows: list[dict[str, Any]] = []
    for cell, target in CELL_TARGET_SLOTS.items():
        n = int(counts.get(cell, 0))
        rows.append(
            {
                "cell": cell,
                "n_labels": n,
                "target_slots": target,
                "progress": round(n / target, 4) if target else None,
            }
        )
    return rows


def _label_coverage(trials: pd.DataFrame) -> dict[str, Any]:
    if trials.empty:
        per_post = pd.Series(dtype=int)
    else:
        per_post = trials.groupby("post_id").size()
    n_posts = int(per_post.size)
    return {
        "unique_posts_labeled": n_posts,
        "target_posts": TARGET_POSTS,
        "labels_per_post": numeric_summary(per_post.astype(float)),
        "posts_with_1_label": int((per_post == 1).sum()),
        "posts_with_2_labels": int((per_post == 2).sum()),
        "posts_with_3_or_more": int((per_post >= 3).sum()),
        "posts_unlabeled_this_wave": TARGET_POSTS - n_posts,
    }


def _assignment_hourly(assignments: pd.DataFrame) -> list[dict[str, Any]]:
    if assignments.empty or "created_at" not in assignments.columns:
        return []
    frame = assignments.copy()
    frame["hour"] = pd.to_datetime(frame["created_at"]).dt.floor("h")
    grouped = (
        frame.groupby(["hour", "party"], dropna=False)
        .size()
        .unstack(fill_value=0)
        .reindex(columns=list(PARTY_ORDER), fill_value=0)
        .sort_index()
    )
    rows: list[dict[str, Any]] = []
    for hour, row in grouped.iterrows():
        rows.append(
            {
                "hour": hour.strftime("%Y-%m-%d %H:%M UTC")
                if hasattr(hour, "strftime")
                else str(hour),
                PARTY_DEMOCRAT: int(row.get(PARTY_DEMOCRAT, 0)),
                PARTY_REPUBLICAN: int(row.get(PARTY_REPUBLICAN, 0)),
            }
        )
    return rows


def _toxicity_mix(trials: pd.DataFrame) -> list[dict[str, Any]]:
    """Return each party's share of trials in each toxicity band."""
    rows: list[dict[str, Any]] = []
    for party in PARTY_ORDER:
        party_trials = trials[trials["party_group"] == party]
        n = int(len(party_trials))
        for toxicity in TOXICITY_ORDER:
            n_tox = int((party_trials["sample_toxicity_type"] == toxicity).sum())
            rows.append(
                {
                    "party": party,
                    "sample_toxicity_type": toxicity,
                    "n_trials": n_tox,
                    "share": round(n_tox / n, 4) if n else None,
                }
            )
    return rows


def _assignment_pace(
    hourly: list[dict[str, Any]], assigned_n: int
) -> dict[str, Any]:
    """Return the busiest assignment hour and the share in the top three hours."""
    if not hourly:
        return {
            "busiest_hour": None,
            "busiest_n": 0,
            "top3_share": None,
        }
    ranked = sorted(
        hourly,
        key=lambda row: int(row.get(PARTY_DEMOCRAT, 0)) + int(row.get(PARTY_REPUBLICAN, 0)),
        reverse=True,
    )
    busiest = ranked[0]
    busiest_n = int(busiest.get(PARTY_DEMOCRAT, 0)) + int(busiest.get(PARTY_REPUBLICAN, 0))
    top3_n = sum(
        int(row.get(PARTY_DEMOCRAT, 0)) + int(row.get(PARTY_REPUBLICAN, 0))
        for row in ranked[:3]
    )
    return {
        "busiest_hour": busiest["hour"],
        "busiest_n": busiest_n,
        "top3_share": round(top3_n / assigned_n, 4) if assigned_n else None,
    }


def _toxicity_stance_table(trials: pd.DataFrame) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for party in PARTY_ORDER:
        for stance in STANCE_ORDER:
            for toxicity in TOXICITY_ORDER:
                slice_trials = trials[
                    (trials["party_group"] == party)
                    & (trials["sampled_stance"] == stance)
                    & (trials["sample_toxicity_type"] == toxicity)
                ]
                share = _decision_share(slice_trials)
                rows.append(
                    {
                        "party": party,
                        "sampled_stance": stance,
                        "sample_toxicity_type": toxicity,
                        **share,
                    }
                )
    return rows


def build_payload(
    export_df: pd.DataFrame,
    assignments: pd.DataFrame,
    *,
    generated_at: str,
    export_path: str,
    export_files: int,
    export_timestamp: str,
    grace_minutes: int,
    cutoff: datetime | None,
) -> dict[str, Any]:
    """Return a JSON-safe dashboard payload with no Prolific ids."""
    trials = select_real_trials(export_df)
    users = build_user_frame(export_df, trials)
    completers = users[users["completed"]].copy()
    exported_ids = set(completers["prolific_id"].astype(str))

    assigned_valid = assignments.copy() if assignments is not None else pd.DataFrame()
    if assigned_valid.empty:
        assigned_valid = pd.DataFrame(columns=["user_id", "party", "created_at"])

    assigned_n = int(assigned_valid["user_id"].nunique()) if not assigned_valid.empty else 0
    assigned_by_party = (
        assigned_valid.groupby("party")["user_id"].nunique().to_dict()
        if not assigned_valid.empty
        else {}
    )
    found = (
        assigned_valid["user_id"].astype(str).isin(exported_ids)
        if not assigned_valid.empty
        else pd.Series(dtype=bool)
    )
    missing_n = int((~found).sum()) if not assigned_valid.empty else 0
    in_grace = 0
    eligible = assigned_n
    missing_eligible = missing_n
    if cutoff is not None and not assigned_valid.empty:
        created = pd.to_datetime(assigned_valid["created_at"])
        in_grace = int((created >= cutoff).sum())
        eligible_mask = created < cutoff
        eligible = int(eligible_mask.sum())
        missing_eligible = int((~found & eligible_mask).sum())

    party_metrics: dict[str, Any] = {}
    for party in PARTY_ORDER:
        party_users = completers[completers["party_group"] == party]
        party_trials = trials[trials["party_group"] == party]
        metrics = _party_slice_metrics(party_users, party_trials)
        metrics["assigned"] = int(assigned_by_party.get(party, 0))
        metrics["target_slots"] = (
            TARGET_DEMOCRAT_SLOTS if party == PARTY_DEMOCRAT else TARGET_REPUBLICAN_SLOTS
        )
        party_metrics[party] = metrics

    all_metrics = _party_slice_metrics(completers, trials)
    all_metrics["assigned"] = assigned_n
    all_metrics["target_slots"] = TARGET_USERS

    n_labels = int(len(trials))
    n_completers = int(len(completers))
    hourly = _assignment_hourly(assigned_valid)

    return {
        "generated_at": generated_at,
        "study": {
            "id": STUDY_ID,
            "iteration_id": STUDY_ITERATION_ID,
            "bucket": STUDY_BUCKET,
            "condition": CONDITION,
            "posts_per_user": POSTS_PER_USER,
            "target_users": TARGET_USERS,
            "target_democrat_slots": TARGET_DEMOCRAT_SLOTS,
            "target_republican_slots": TARGET_REPUBLICAN_SLOTS,
            "target_labels": TARGET_LABELS,
            "target_posts": TARGET_POSTS,
            "evaluation_mode": EVALUATION_MODE_LINKED_FATE,
        },
        "export": {
            "path": Path(export_path).name if export_path else "",
            "timestamp": export_timestamp,
            "files": export_files,
            "unique_completers": n_completers,
            "rows": int(len(export_df)),
        },
        "progress": {
            "assigned_valid": assigned_n,
            "completers": n_completers,
            "missing_from_export": missing_n,
            "assignments_in_grace_window": in_grace,
            "eligible_assigned": eligible,
            "missing_after_grace": missing_eligible,
            "attrition_rate_raw": round(missing_n / assigned_n, 4) if assigned_n else None,
            "attrition_rate_after_grace": round(missing_eligible / eligible, 4)
            if eligible
            else None,
            "grace_minutes": grace_minutes,
            "labels": n_labels,
            "user_progress": round(n_completers / TARGET_USERS, 4),
            "assignment_progress": round(assigned_n / TARGET_USERS, 4),
            "label_progress": round(n_labels / TARGET_LABELS, 4),
        },
        "all": all_metrics,
        "by_party": party_metrics,
        "remove_rate_by_toxicity": _crosstab_remove_rates(
            trials, "sample_toxicity_type", TOXICITY_ORDER
        ),
        "remove_rate_by_stance": _crosstab_remove_rates(
            trials, "sampled_stance", STANCE_ORDER
        ),
        "remove_rate_by_party_stance_toxicity": _toxicity_stance_table(trials),
        "cell_coverage": _cell_coverage(trials),
        "post_coverage": _label_coverage(trials),
        "toxicity_mix": _toxicity_mix(trials),
        "assignment_hourly": hourly,
        "assignment_pace": _assignment_pace(hourly, assigned_n),
        "attention_remove_share": {
            "passed": _decision_share(
                trials[
                    trials["prolific_id"].isin(
                        completers.loc[completers["attention_passed"] == 1, "prolific_id"]
                    )
                ]
            ),
            "failed": _decision_share(
                trials[
                    trials["prolific_id"].isin(
                        completers.loc[completers["attention_passed"] == 0, "prolific_id"]
                    )
                ]
            ),
        },
    }
