"""Tests for study-progress aggregation."""

from __future__ import annotations

from datetime import datetime

import pandas as pd

from experiments.study_progress_dashboard_2026_09_11.analyze import (
    build_payload,
    build_user_frame,
    rate_histogram,
    select_real_trials,
)
from experiments.study_progress_dashboard_2026_09_11.constants import (
    DECISION_KEEP,
    DECISION_REMOVE,
    PARTY_DEMOCRAT,
    PARTY_REPUBLICAN,
    TOXICITY_HIGH,
    TOXICITY_LOW,
    TOXICITY_MIDDLE,
)
from experiments.study_progress_dashboard_2026_09_11.render import fmt_pct, render_html
from experiments.study_progress_dashboard_2026_09_11.write import write_dashboard


def _trial(
    prolific_id: str,
    party: str,
    post_id: str,
    decision: str,
    *,
    stance: str = "left",
    toxicity: str = TOXICITY_MIDDLE,
    trial_index: int = 8,
    rt_ms: float = 1000.0,
) -> dict:
    return {
        "trial_type": "moderation-trial",
        "trial_index": trial_index,
        "time_elapsed": 120000,
        "post_id": post_id,
        "decision": decision,
        "sampled_stance": stance,
        "sample_toxicity_type": toxicity,
        "evaluation_mode": "linked_fate",
        "response_time_ms": rt_ms,
        "prolific_id": prolific_id,
        "party_group": party,
        "political_affiliation": party,
        "party_lean": "",
        "attention_check_passed": 1,
        "phase1_pair_influence_rating": 5,
        "age": 40,
        "gender": "female",
        "education": "bachelors",
        "political_ideology": 2 if party == PARTY_DEMOCRAT else 6,
        "condition": "training_assisted",
    }


def _practice(prolific_id: str, party: str) -> dict:
    row = _trial(prolific_id, party, "", DECISION_KEEP, trial_index=6)
    row["post_id"] = ""
    row["sampled_stance"] = ""
    row["sample_toxicity_type"] = ""
    return row


def _person_trials(prolific_id: str, party: str, n_keep: int, n_remove: int) -> list[dict]:
    rows = [_practice(prolific_id, party)]
    rows.append(
        {
            **_trial(prolific_id, party, "meta", DECISION_KEEP, trial_index=0),
            "trial_type": "instructions",
            "post_id": "",
            "decision": "",
        }
    )
    n = 0
    for i in range(n_keep):
        stance = "left" if i % 2 == 0 else "right"
        tox = (TOXICITY_LOW, TOXICITY_MIDDLE, TOXICITY_HIGH)[i % 3]
        rows.append(
            _trial(
                prolific_id,
                party,
                f"{prolific_id}-k{i}",
                DECISION_KEEP,
                stance=stance,
                toxicity=tox,
                trial_index=8 + n,
            )
        )
        n += 1
    for i in range(n_remove):
        stance = "left" if i % 2 == 0 else "right"
        tox = (TOXICITY_LOW, TOXICITY_MIDDLE, TOXICITY_HIGH)[i % 3]
        rows.append(
            _trial(
                prolific_id,
                party,
                f"{prolific_id}-r{i}",
                DECISION_REMOVE,
                stance=stance,
                toxicity=tox,
                trial_index=8 + n,
            )
        )
        n += 1
    return rows


def test_select_real_trials_drops_practice() -> None:
    frame = pd.DataFrame(
        [_practice("u1", PARTY_DEMOCRAT)]
        + [_trial("u1", PARTY_DEMOCRAT, "p1", DECISION_KEEP)]
        + [_trial("u1", PARTY_DEMOCRAT, "p2", "skip")]
    )
    real = select_real_trials(frame)
    assert len(real) == 1
    assert real.iloc[0]["post_id"] == "p1"


def test_user_keep_rate_and_histogram() -> None:
    rows = _person_trials("d1", PARTY_DEMOCRAT, n_keep=16, n_remove=4)
    rows += _person_trials("r1", PARTY_REPUBLICAN, n_keep=10, n_remove=10)
    export_df = pd.DataFrame(rows)
    trials = select_real_trials(export_df)
    users = build_user_frame(export_df, trials)
    assert set(users["prolific_id"]) == {"d1", "r1"}
    d = users.set_index("prolific_id").loc["d1"]
    assert d["keep_rate"] == 0.8
    assert d["remove_rate"] == 0.2
    assert bool(d["completed"]) is True
    hist = rate_histogram(users["keep_rate"])
    by_bin = {row["bin"]: row["count"] for row in hist}
    assert by_bin["70 to 80%"] == 1
    assert by_bin["40 to 50%"] == 1


def test_payload_and_html_have_party_tables() -> None:
    rows = _person_trials("d1", PARTY_DEMOCRAT, n_keep=18, n_remove=2)
    rows += _person_trials("r1", PARTY_REPUBLICAN, n_keep=12, n_remove=8)
    export_df = pd.DataFrame(rows)
    assignments = pd.DataFrame(
        [
            {
                "user_id": "d1",
                "party": PARTY_DEMOCRAT,
                "created_at": datetime(2026, 9, 10, 18, 0, 0),
            },
            {
                "user_id": "r1",
                "party": PARTY_REPUBLICAN,
                "created_at": datetime(2026, 9, 10, 18, 5, 0),
            },
            {
                "user_id": "missing-d",
                "party": PARTY_DEMOCRAT,
                "created_at": datetime(2026, 9, 10, 17, 0, 0),
            },
        ]
    )
    payload = build_payload(
        export_df,
        assignments,
        generated_at="2026_09_11-03:00:00",
        export_path="export.csv",
        export_files=2,
        export_timestamp="2026_09_11-02:27:54",
        grace_minutes=20,
        cutoff=datetime(2026, 9, 11, 2, 7, 54),
    )
    assert payload["progress"]["completers"] == 2
    assert payload["progress"]["assigned_valid"] == 3
    assert payload["progress"]["missing_from_export"] == 1
    assert payload["export"]["path"] == "export.csv"
    assert payload["by_party"][PARTY_DEMOCRAT]["user_keep_rate"]["mean"] == 0.9
    assert payload["by_party"][PARTY_REPUBLICAN]["user_keep_rate"]["mean"] == 0.6
    assert payload["all"]["always_keep"] == 0
    assert payload["all"]["always_keep_passed"] == 0
    mix = {(row["party"], row["sample_toxicity_type"]): row["share"] for row in payload["toxicity_mix"]}
    assert abs(sum(v or 0 for (party, _), v in mix.items() if party == PARTY_DEMOCRAT) - 1.0) < 1e-6
    html = render_html(payload)
    assert "MirrorView September 2026 study progress" in html
    assert "Keep rate per user" in html
    assert "hour-label" in html
    assert fmt_pct(0.9) in html
    assert "d1" not in html
    assert "missing-d" not in html
    assert "—" not in html
    assert "–" not in html
    assert "/workspace" not in html


def test_write_dashboard_copies_to_vercel(tmp_path) -> None:
    rows = _person_trials("d1", PARTY_DEMOCRAT, n_keep=18, n_remove=2)
    export_df = pd.DataFrame(rows)
    assignments = pd.DataFrame(
        [
            {
                "user_id": "d1",
                "party": PARTY_DEMOCRAT,
                "created_at": datetime(2026, 9, 10, 18, 0, 0),
            }
        ]
    )
    payload = build_payload(
        export_df,
        assignments,
        generated_at="2026_09_11-03:00:00",
        export_path="export.csv",
        export_files=1,
        export_timestamp="2026_09_11-02:27:54",
        grace_minutes=20,
        cutoff=datetime(2026, 9, 11, 2, 7, 54),
    )
    vercel_path = tmp_path / "public" / "study-progress.html"
    html_path = write_dashboard(payload, tmp_path, vercel_paths=[vercel_path])
    assert html_path.read_text(encoding="utf-8") == vercel_path.read_text(encoding="utf-8")
    assert "MirrorView September 2026 study progress" in vercel_path.read_text(
        encoding="utf-8"
    )
