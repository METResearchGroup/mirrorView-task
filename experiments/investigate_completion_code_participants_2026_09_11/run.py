"""Look up Prolific participants who said they finished but could not enter the completion code.

Run from the repo root:

    export AWS_ACCESS_KEY_ID="$LAB_AWS_ACCESS_KEY_ID"
    export AWS_SECRET_ACCESS_KEY="$LAB_AWS_ACCESS_KEY_SECRET"

    PYTHONPATH=. uv run python experiments/investigate_completion_code_participants_2026_09_11/run.py
"""

from __future__ import annotations

import argparse

import boto3
import pandas as pd

from data_platform.generate_features.s3_feature_campaign import CampaignObjectStore
from experiments.investigate_completion_code_participants_2026_09_11.constants import (
    AWS_REGION,
    DATA_PREFIX_PROLIFIC,
    DEFAULT_PROLIFIC_IDS,
    EXPERIMENT_DIR,
    InvestigationResult,
    OUTPUT_S3_BUCKET,
    ParticipantFinding,
    STUDY_BUCKET,
    USER_ASSIGNMENTS_TABLE,
)
from experiments.investigate_completion_code_participants_2026_09_11.lookup import (
    find_session_files,
    get_assignment_record,
    list_session_objects,
    load_assigned_post_ids,
)
from experiments.investigate_completion_code_participants_2026_09_11.parse import (
    posts_match_assignment,
)
from experiments.investigate_completion_code_participants_2026_09_11.summarize import (
    recommendation_for,
    summarize_session,
)
from experiments.investigate_completion_code_participants_2026_09_11.write import (
    write_and_upload_findings_json,
    write_results_md,
)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse CLI args."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--prolific-id",
        action="append",
        dest="prolific_ids",
        help="Prolific id to look up. Repeatable. Default: the two ids in the request.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> InvestigationResult:
    """Look up assignments and saved sessions, then write RESULTS.md."""
    args = parse_args(argv)
    prolific_ids = tuple(args.prolific_ids) if args.prolific_ids else DEFAULT_PROLIFIC_IDS
    dynamodb = boto3.resource("dynamodb", region_name=AWS_REGION)
    table = dynamodb.Table(USER_ASSIGNMENTS_TABLE)
    s3_client = boto3.client("s3", region_name=AWS_REGION)
    objects = list_session_objects(s3_client)
    prolific_csv_count = sum(
        1 for item in objects if str(item["Key"]).startswith(DATA_PREFIX_PROLIFIC)
    )
    sessions_by_id = find_session_files(s3_client, prolific_ids, objects)
    findings: list[ParticipantFinding] = []
    assignment_frames: dict[str, pd.DataFrame] = {}
    for prolific_id in prolific_ids:
        assignment = get_assignment_record(table, prolific_id)
        session_hits = sorted(
            sessions_by_id.get(prolific_id, []),
            key=lambda item: item[0].last_modified,
        )
        session_files = tuple(item for item, _frame in session_hits)
        session = (
            summarize_session(session_hits[-1][1], prolific_id) if session_hits else None
        )
        assigned_post_ids = load_assigned_post_ids(
            s3_client, assignment, assignment_frames=assignment_frames
        )
        match = (
            posts_match_assignment(session.scored_post_ids, assigned_post_ids)
            if session is not None and assigned_post_ids is not None
            else None
        )
        findings.append(
            ParticipantFinding(
                prolific_id=prolific_id,
                assignment=assignment,
                session_files=session_files,
                session=session,
                assigned_post_ids=assigned_post_ids,
                posts_match_assignment=match,
                recommendation=recommendation_for(
                    assignment_found=assignment.found,
                    session=session,
                    posts_match=match,
                ),
            )
        )
    result = InvestigationResult(
        findings=tuple(findings),
        prolific_csv_count=prolific_csv_count,
        findings_s3_uri="",
        findings_sha256="",
        results_path=EXPERIMENT_DIR / "RESULTS.md",
    )
    store = CampaignObjectStore(OUTPUT_S3_BUCKET)
    findings_s3_uri, findings_sha256 = write_and_upload_findings_json(
        result, store, EXPERIMENT_DIR
    )
    result = InvestigationResult(
        findings=result.findings,
        prolific_csv_count=prolific_csv_count,
        findings_s3_uri=findings_s3_uri,
        findings_sha256=findings_sha256,
        results_path=EXPERIMENT_DIR / "RESULTS.md",
    )
    results_path = write_results_md(result, EXPERIMENT_DIR)
    for finding in result.findings:
        print(
            f"{finding.prolific_id} recommendation={finding.recommendation} "
            f"assignment={finding.assignment.assignment_id} "
            f"complete={None if finding.session is None else finding.session.is_complete}"
        )
    print(f"prolific_csv_count={prolific_csv_count}")
    print(f"findings_s3_uri={findings_s3_uri}")
    print(f"findings_sha256={findings_sha256}")
    print(f"results_path={results_path}")
    return result


if __name__ == "__main__":
    main()
