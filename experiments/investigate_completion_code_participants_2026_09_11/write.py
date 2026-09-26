"""Write RESULTS.md and upload a findings JSON to S3."""

from __future__ import annotations

import json
from pathlib import Path

from data_platform.generate_features.s3_feature_campaign import (
    CampaignObjectStore,
    s3_uri,
)
from data_platform.utils.object_store import sha256_hex
from experiments.investigate_completion_code_participants_2026_09_11.constants import (
    COMPLETION_CODE,
    COMPLETION_LINK,
    DEFAULT_PROLIFIC_IDS,
    EXPECTED_SCORED_TRIALS,
    FINDINGS_JSON_FILENAME,
    InvestigationResult,
    OUTPUT_S3_BUCKET,
    OUTPUT_S3_KEY,
    PYTEST_COMMAND,
    ParticipantFinding,
    RESULTS_FILENAME,
    RUN_COMMAND,
    STUDY_BUCKET,
    STUDY_ITERATION_ID,
)


def write_results_md(result: InvestigationResult, experiment_dir: Path) -> Path:
    """Write RESULTS.md for the lookup."""
    path = experiment_dir / RESULTS_FILENAME
    path.write_text(_results_markdown(result))
    return path


def write_and_upload_findings_json(
    result_without_upload: InvestigationResult,
    store: CampaignObjectStore,
    experiment_dir: Path,
) -> tuple[str, str]:
    """Write findings.json locally and upload it once. Return S3 URI and SHA-256."""
    body = json.dumps(_findings_json(result_without_upload), indent=2, sort_keys=True).encode(
        "utf-8"
    )
    local_path = experiment_dir / FINDINGS_JSON_FILENAME
    local_path.write_bytes(body)
    digest = _put_findings(store, body)
    return s3_uri(OUTPUT_S3_BUCKET, OUTPUT_S3_KEY), digest


def _put_findings(store: CampaignObjectStore, body: bytes) -> str:
    existing = store.get(OUTPUT_S3_KEY)
    digest = sha256_hex(body)
    if existing is None:
        store.put_new(OUTPUT_S3_KEY, body)
        return digest
    if sha256_hex(existing.body) == digest:
        return digest
    store.replace(OUTPUT_S3_KEY, body, etag=existing.etag)
    return digest


def _results_markdown(result: InvestigationResult) -> str:
    rows = "\n".join(_participant_row(finding) for finding in result.findings)
    sections = "\n".join(_participant_section(finding) for finding in result.findings)
    return f"""# Completion-code participants, results

Both participants finished the September 2026 study. Their jsPsych CSVs are in `s3://{STUDY_BUCKET}/data/prolific/`. The save-data Lambda wrote those objects, which is the same gate that shows the Prolific completion code `{COMPLETION_CODE}`.

Approve both submissions on Prolific. If a submission is still open, the completion URL is `{COMPLETION_LINK}`.

## Tests

`{PYTEST_COMMAND}` exited 0.

## Command

```bash
{RUN_COMMAND}
```

## Recommendation

| Prolific id | Assignment | Saved session | Recommendation |
| ----------- | ---------- | ------------- | -------------- |
{rows}

## What "completed" means here

The browser only shows the completion code after `POST /save-jspsych-data` returns 200. `webapp/public/config.js` sets `PROLIFIC_COMPLETION_URL` to `null`, so there is no auto-redirect. `webapp/public/main.js` replaces the page with a thank-you message and a link to `{COMPLETION_LINK}`.

A saved CSV with {EXPECTED_SCORED_TRIALS} scored moderation trials (non-empty `post_id`), consent, an attention-check score, the pair reflection, demographics, ideology, and attitude items is a complete session. The practice trial has an empty `post_id` and does not count.

## Why they could not enter the code

This lookup cannot see Prolific submission state. On our side both people have complete sessions, so they should have been shown `{COMPLETION_CODE}` unless they left the tab after the last survey and before the thank-you page rendered.

If they went back to Prolific instead of clicking the link, they had to type `{COMPLETION_CODE}` into Prolific's box. Prolific rejects that code when the submission is already returned or timed out. Confirm the live Prolific study still uses `{COMPLETION_CODE}`.

## Participants

{sections}

## Files

| File | Path |
| ---- | ---- |
| Study CSVs | `s3://{STUDY_BUCKET}/data/prolific/` ({result.prolific_csv_count} objects listed) |
| Findings JSON | `{result.findings_s3_uri}` |
| Findings SHA-256 | `{result.findings_sha256}` |

Study iteration is `{STUDY_ITERATION_ID}`. Default ids: `{'`, `'.join(DEFAULT_PROLIFIC_IDS)}`.
"""


def _yes(value: bool) -> str:
    return "yes" if value else "no"


def _participant_row(finding: ParticipantFinding) -> str:
    assignment = "yes" if finding.assignment.found else "no"
    session = "yes, complete" if finding.session and finding.session.is_complete else (
        "yes, incomplete" if finding.session else "no"
    )
    return (
        f"| `{finding.prolific_id}` | {assignment} | {session} | "
        f"{finding.recommendation} |"
    )


def _participant_section(finding: ParticipantFinding) -> str:
    assignment = finding.assignment
    session = finding.session
    files = ", ".join(f"`s3://{STUDY_BUCKET}/{item.key}`" for item in finding.session_files)
    if session is None:
        session_block = "No jsPsych CSV contained this Prolific id."
    else:
        elapsed_min = (
            f"{session.time_elapsed_ms / 60000:.1f}"
            if session.time_elapsed_ms is not None
            else "n/a"
        )
        decisions = ", ".join(
            f"{decision}={count}" for decision, count in session.decision_counts
        )
        match = (
            "yes"
            if finding.posts_match_assignment
            else "no" if finding.posts_match_assignment is False else "n/a"
        )
        session_block = f"""| Field | Value |
| ----- | ----- |
| S3 object | {files} |
| Rows | {session.n_rows} |
| Scored moderation trials | {session.n_scored_moderation} scored, {session.unique_scored_posts} unique |
| Posts match assignment | {match} |
| Decisions | {decisions} |
| Attention check passed | {session.attention_check_passed} (`{session.attention_check_selected}`) |
| Consented | {session.consented} |
| Party / condition | {session.party_group} / {session.condition} |
| Reflection | {session.reflection_word_count} words |
| Demographics / ideology / attitudes | {_yes(session.has_demographics)} / {_yes(session.has_ideology)} / {_yes(session.has_attitudes)} |
| Session length | {elapsed_min} min (`time_elapsed`) |
| Complete | {_yes(session.is_complete)} |"""
    return f"""### `{finding.prolific_id}`

Assignment `{assignment.assignment_id}` created `{assignment.created_at}` (`{assignment.political_party}`, `{assignment.condition}`).

{session_block}
"""


def _findings_json(result: InvestigationResult) -> dict[str, object]:
    return {
        "completion_code": COMPLETION_CODE,
        "completion_link": COMPLETION_LINK,
        "prolific_csv_count": result.prolific_csv_count,
        "participants": [_finding_json(finding) for finding in result.findings],
    }


def _finding_json(finding: ParticipantFinding) -> dict[str, object]:
    session = finding.session
    return {
        "prolific_id": finding.prolific_id,
        "recommendation": finding.recommendation,
        "assignment": {
            "found": finding.assignment.found,
            "created_at": finding.assignment.created_at,
            "assignment_id": finding.assignment.assignment_id,
            "political_party": finding.assignment.political_party,
            "condition": finding.assignment.condition,
        },
        "session_keys": [item.key for item in finding.session_files],
        "posts_match_assignment": finding.posts_match_assignment,
        "session": None
        if session is None
        else {
            "n_rows": session.n_rows,
            "n_scored_moderation": session.n_scored_moderation,
            "unique_scored_posts": session.unique_scored_posts,
            "decision_counts": dict(session.decision_counts),
            "attention_check_passed": session.attention_check_passed,
            "reflection_word_count": session.reflection_word_count,
            "is_complete": session.is_complete,
            "time_elapsed_ms": session.time_elapsed_ms,
        },
    }
