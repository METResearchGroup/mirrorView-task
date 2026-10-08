"""Read DynamoDB assignments and jsPsych CSVs for named Prolific ids."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from io import BytesIO
from typing import Any

import pandas as pd

from experiments.investigate_completion_code_participants_2026_09_11.constants import (
    ASSIGNED_POST_IDS_COLUMN,
    ASSIGNMENT_ID_COLUMN,
    AssignmentRecord,
    DATA_PREFIX_PROLIFIC,
    DATA_PREFIX_TEST,
    SessionFile,
    STUDY_BUCKET,
    STUDY_ID,
    STUDY_ITERATION_ID,
    USER_ASSIGNMENTS_TABLE,
)
from experiments.investigate_completion_code_participants_2026_09_11.parse import (
    parse_assignment_payload,
    parse_post_ids,
)
from experiments.investigate_completion_code_participants_2026_09_11.summarize import (
    prolific_id_in_frame,
)


def get_assignment_record(
    table: Any, prolific_id: str, *, study_iteration_id: str = STUDY_ITERATION_ID
) -> AssignmentRecord:
    """Return the user_assignments item for this study iteration, or a miss."""
    response = table.get_item(
        Key={
            "study_id": STUDY_ID,
            "iteration_user_key": f"{study_iteration_id}#{prolific_id}",
        }
    )
    item = response.get("Item")
    if not item:
        return AssignmentRecord(
            prolific_id=prolific_id,
            found=False,
            created_at=None,
            study_iteration_id=None,
            assignment_id=None,
            political_party=None,
            condition=None,
            assignment_s3_key=None,
        )
    parsed = parse_assignment_payload(str(item["payload"]))
    return AssignmentRecord(
        prolific_id=str(item.get("user_id", prolific_id)),
        found=True,
        created_at=_optional_str(item.get("created_at")),
        study_iteration_id=_optional_str(item.get("study_iteration_id")),
        assignment_id=parsed["assignment_id"],
        political_party=parsed["political_party"],
        condition=parsed["condition"],
        assignment_s3_key=parsed["s3_key"],
    )


def list_session_objects(s3_client: Any, *, bucket: str = STUDY_BUCKET) -> list[dict[str, Any]]:
    """List CSV objects under the prolific and test prefixes."""
    objects: list[dict[str, Any]] = []
    paginator = s3_client.get_paginator("list_objects_v2")
    for prefix in (DATA_PREFIX_PROLIFIC, DATA_PREFIX_TEST):
        for page in paginator.paginate(Bucket=bucket, Prefix=prefix):
            for item in page.get("Contents", []):
                objects.append(item)
    return objects


def find_session_files(
    s3_client: Any,
    prolific_ids: tuple[str, ...] | list[str],
    objects: list[dict[str, Any]],
    *,
    bucket: str = STUDY_BUCKET,
    max_workers: int = 32,
) -> dict[str, list[tuple[SessionFile, pd.DataFrame]]]:
    """Download session CSVs and return those that contain any requested id."""
    wanted = set(prolific_ids)
    hits: dict[str, list[tuple[SessionFile, pd.DataFrame]]] = {pid: [] for pid in prolific_ids}

    def check(item: dict[str, Any]) -> list[tuple[str, SessionFile, pd.DataFrame]]:
        key = item["Key"]
        body = s3_client.get_object(Bucket=bucket, Key=key)["Body"].read()
        text = body.decode("utf-8", errors="replace")
        matched = [pid for pid in wanted if pid in text]
        if not matched:
            return []
        frame = pd.read_csv(BytesIO(body))
        session = SessionFile(
            key=key,
            last_modified=str(item["LastModified"]),
            size=int(item["Size"]),
        )
        found: list[tuple[str, SessionFile, pd.DataFrame]] = []
        for pid in matched:
            if prolific_id_in_frame(frame, pid):
                found.append((pid, session, frame))
        return found

    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        futures = [pool.submit(check, item) for item in objects]
        for future in as_completed(futures):
            for pid, session, frame in future.result():
                hits[pid].append((session, frame))
    return hits


def load_assigned_post_ids(
    s3_client: Any,
    assignment: AssignmentRecord,
    *,
    bucket: str = STUDY_BUCKET,
    assignment_frames: dict[str, pd.DataFrame] | None = None,
) -> tuple[str, ...] | None:
    """Return assigned post ids for this assignment row, or None when missing."""
    if not assignment.assignment_s3_key or not assignment.assignment_id:
        return None
    cache = assignment_frames if assignment_frames is not None else {}
    frame = cache.get(assignment.assignment_s3_key)
    if frame is None:
        body = s3_client.get_object(
            Bucket=bucket, Key=assignment.assignment_s3_key
        )["Body"].read()
        frame = pd.read_csv(BytesIO(body))
        cache[assignment.assignment_s3_key] = frame
    matched = frame.loc[frame[ASSIGNMENT_ID_COLUMN] == assignment.assignment_id]
    if matched.empty:
        return None
    return tuple(parse_post_ids(str(matched.iloc[0][ASSIGNED_POST_IDS_COLUMN])))


def _optional_str(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None
