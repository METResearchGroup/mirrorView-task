"""Build the shared September 2026 cohort from Prolific CSV exports."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from experiments.ai_simulation_responses_2026_09_11.shared.constants import (
    COHORT_CAP,
    POSTS_PER_USER,
    STUDY_SINCE_DATE,
    CohortTrial,
    CohortUser,
)
from scripts.export_study_results import (
    INVALID_PROLIFIC_SUBSTRINGS,
    list_csv_keys,
    utc_midnight_ms,
)

DATA_CSV_FILENAME_PATTERN = re.compile(r"^data_(\d+)")
LINKED_FATE_MODE = "linked_fate"
VALID_DECISIONS = frozenset({"keep", "remove"})
VALID_PAIR_ROLES = frozenset({"original", "mirror"})


@dataclass(frozen=True)
class BuildCohortResult:
    """Users, trials, and drop counts from one cohort build."""

    users: tuple[CohortUser, ...]
    trials: tuple[CohortTrial, ...]
    dropped_incomplete: int
    dropped_missing_pair_order: int
    dropped_missing_reflection: int


@dataclass(frozen=True)
class _CandidateUser:
    """One parsed participant before cohort cap."""

    user: CohortUser
    trials: tuple[CohortTrial, ...]


def list_september_csv_keys(store_or_s3_client) -> list[str]:
    """List September study CSV keys at or after 2026-09-09."""
    min_ms = utc_midnight_ms(STUDY_SINCE_DATE)
    return list_csv_keys(store_or_s3_client, min_file_epoch_ms=min_ms)


def build_cohort(csv_paths: list[Path]) -> BuildCohortResult:
    """Confirm complete participants from downloaded CSV paths."""
    candidates, drops = _load_candidates(csv_paths)
    selected = _select_capped_users(candidates)
    users = tuple(item.user for item in selected)
    trials = tuple(trial for item in selected for trial in item.trials)
    return BuildCohortResult(
        users=users,
        trials=trials,
        dropped_incomplete=drops["incomplete"],
        dropped_missing_pair_order=drops["pair_order"],
        dropped_missing_reflection=drops["reflection"],
    )


def _load_candidates(
    csv_paths: list[Path],
) -> tuple[list[_CandidateUser], dict[str, int]]:
    drops = {"incomplete": 0, "pair_order": 0, "reflection": 0}
    candidates: list[_CandidateUser] = []
    for path in csv_paths:
        frame = pd.read_csv(path)
        if not _valid_prolific_file(frame):
            continue
        parsed = _parse_candidate(path, frame, drops)
        if parsed is not None:
            candidates.append(parsed)
    candidates.sort(key=lambda item: (item.user.source_file_epoch_ms, item.user.prolific_id))
    return candidates, drops


def _select_capped_users(
    candidates: list[_CandidateUser],
) -> list[_CandidateUser]:
    return candidates[:COHORT_CAP]


def _parse_candidate(
    path: Path,
    frame: pd.DataFrame,
    drops: dict[str, int],
) -> _CandidateUser | None:
    epoch_ms = _epoch_ms_from_filename(path.name)
    prolific_id = str(frame["prolific_id"].iloc[0]).strip()
    if not _valid_reflection(frame, drops):
        return None
    trial_frame = _linked_fate_frame(frame)
    if len(trial_frame) != POSTS_PER_USER:
        drops["incomplete"] += 1
        return None
    trials = _build_trials(prolific_id, trial_frame, drops)
    if trials is None:
        return None
    user = _build_user(prolific_id, epoch_ms, frame.iloc[0])
    return _CandidateUser(user=user, trials=trials)


def _valid_prolific_file(frame: pd.DataFrame) -> bool:
    prolific_ids = frame["prolific_id"].fillna("").astype(str).str.lower()
    for sub in INVALID_PROLIFIC_SUBSTRINGS:
        if prolific_ids.str.contains(sub.lower(), regex=False).any():
            return False
    return True


def _valid_reflection(frame: pd.DataFrame, drops: dict[str, int]) -> bool:
    text = _cell(frame.iloc[0], "phase1_pair_reflection_text")
    rating = _parse_influence_rating(frame["phase1_pair_influence_rating"].iloc[0])
    if not text or rating is None:
        drops["reflection"] += 1
        return False
    return True


def _linked_fate_frame(frame: pd.DataFrame) -> pd.DataFrame:
    mask = frame["evaluation_mode"].astype(str).eq(LINKED_FATE_MODE)
    mask &= frame["decision"].astype(str).str.lower().isin(VALID_DECISIONS)
    return frame.loc[mask].sort_values("trial_index")


def _build_trials(
    prolific_id: str,
    trial_frame: pd.DataFrame,
    drops: dict[str, int],
) -> tuple[CohortTrial, ...] | None:
    trials: list[CohortTrial] = []
    for pair_index, (_, row) in enumerate(trial_frame.iterrows(), start=1):
        pair_order = _parse_pair_order(row.get("pair_order"))
        if pair_order is None:
            drops["pair_order"] += 1
            return None
        decision = str(row["decision"]).strip().lower()
        trials.append(
            CohortTrial(
                prolific_id=prolific_id,
                pair_index=pair_index,
                post_id=str(row["post_id"]),
                original_text=str(row["original_text"]),
                mirror_text=str(row["mirror_text"]),
                pair_order=pair_order,
                gold_remove=1 if decision == "remove" else 0,
                sampled_stance=str(row["sampled_stance"]),
                sample_toxicity_type=str(row["sample_toxicity_type"]),
                trial_index=int(row["trial_index"]),
            )
        )
    return tuple(trials)


def _build_user(prolific_id: str, epoch_ms: int, row: pd.Series) -> CohortUser:
    rating = _parse_influence_rating(row["phase1_pair_influence_rating"])
    assert rating is not None
    return CohortUser(
        prolific_id=prolific_id,
        participant_id=str(row["participant_id"]),
        source_file_epoch_ms=epoch_ms,
        party_group=_cell(row, "party_group"),
        age=_cell(row, "age"),
        gender=_cell(row, "gender"),
        education=_cell(row, "education"),
        political_affiliation=_cell(row, "political_affiliation"),
        party_lean=_cell(row, "party_lean"),
        political_ideology=_cell(row, "political_ideology"),
        political_follow=_cell(row, "political_follow"),
        rep_id=_cell(row, "rep_id"),
        dem_id=_cell(row, "dem_id"),
        attitude_reduce_abortion=_cell(row, "attitude_reduce_abortion"),
        attitude_citizenship_undocumented=_cell(row, "attitude_citizenship_undocumented"),
        attitude_restrict_guns=_cell(row, "attitude_restrict_guns"),
        attitude_regulate_environment=_cell(row, "attitude_regulate_environment"),
        attitude_raise_wealth_taxes=_cell(row, "attitude_raise_wealth_taxes"),
        attitude_expand_medicaid=_cell(row, "attitude_expand_medicaid"),
        phase1_pair_reflection_text=_cell(row, "phase1_pair_reflection_text"),
        phase1_pair_influence_rating=rating,
    )


def _epoch_ms_from_filename(filename: str) -> int:
    match = DATA_CSV_FILENAME_PATTERN.match(filename)
    if match is None:
        raise ValueError(f"Unexpected cohort CSV filename: {filename}")
    return int(match.group(1))


def _parse_pair_order(raw_value: object) -> tuple[str, str] | None:
    if pd.isna(raw_value) or str(raw_value).strip() == "":
        return None
    parsed = json.loads(str(raw_value)) if isinstance(raw_value, str) else raw_value
    if not isinstance(parsed, list) or len(parsed) != 2:
        return None
    roles = tuple(str(item).strip().lower() for item in parsed)
    if set(roles) != VALID_PAIR_ROLES:
        return None
    return roles  # type: ignore[return-value]


def _parse_influence_rating(raw_value: object) -> int | None:
    if pd.isna(raw_value) or str(raw_value).strip() == "":
        return None
    rating = int(float(raw_value))
    if rating < 1 or rating > 7:
        return None
    return rating


def _cell(row: pd.Series, column: str) -> str:
    value = row.get(column, "")
    if pd.isna(value):
        return ""
    return str(value).strip()
