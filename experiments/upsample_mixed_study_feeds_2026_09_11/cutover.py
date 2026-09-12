"""In-place live cutover of September study assignment CSVs on the pinned prefix.

Run from the repo root:

    export AWS_ACCESS_KEY_ID="$LAB_AWS_ACCESS_KEY_ID"
    export AWS_SECRET_ACCESS_KEY="$LAB_AWS_ACCESS_KEY_SECRET"
    PYTHONPATH=. uv run python experiments/upsample_mixed_study_feeds_2026_09_11/cutover.py
"""

from __future__ import annotations

import io
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

import boto3
import pandas as pd
import yaml

from data_platform.generate_features.s3_feature_campaign import (
    CampaignObjectStore,
    StoredObject,
    s3_uri,
)
from data_platform.utils.object_store import sha256_hex
from experiments.load_study_assignments_2026_09_09.constants import (
    ASSIGNMENT_COLUMNS,
    ASSIGNMENT_ID_COLUMN,
    ASSIGNED_POST_IDS_COLUMN,
    ASSIGNMENTS_FILENAME,
    AssignmentRow,
    CONDITION,
    CONDITION_COLUMN,
    CONFIG_FILENAME,
    CREATED_AT_COLUMN,
    EMPTY_POLITICAL_PARTY,
    NAN_CELL,
    PARTY_DEMOCRAT,
    PARTY_REPUBLICAN,
    POLITICAL_PARTY_COLUMN,
)
from experiments.load_study_assignments_2026_09_09.constants import ASSIGNMENT_PREFIX
from experiments.upsample_mixed_study_feeds_2026_09_11.constants import (
    ASSIGNMENTS_ORIGINAL_FILENAME,
    ASSIGNMENTS_OVERPROVISIONED_FILENAME,
    BATCH_DIRNAME,
    CONFIG_ORIGINAL_FILENAME,
    CUTOVER_VERIFY_LOG_PATH,
    DEMOCRAT_FIRST_ASSIGNMENT_ID,
    DEMOCRAT_FIRST_EXTRA_ASSIGNMENT_ID,
    DEMOCRAT_ITERATION_ASSIGNMENT_KEY,
    DEMOCRAT_LAST_ASSIGNMENT_ID,
    DEMOCRAT_MANUAL_TEST_ITERATION_USER_KEY,
    DEMOCRAT_ROW_COUNT,
    DYNAMODB_REGION,
    LIVE_BATCH_TIMESTAMP,
    LIVE_S3_PREFIX,
    ORIGINAL_DEMOCRAT_COUNT,
    ORIGINAL_REPUBLICAN_COUNT,
    PRE_CUTOVER_CONFIG_SHA256,
    PRE_CUTOVER_DEMOCRAT_CSV_SHA256,
    PRE_CUTOVER_REPUBLICAN_CSV_SHA256,
    REPUBLICAN_FIRST_ASSIGNMENT_ID,
    REPUBLICAN_FIRST_EXTRA_ASSIGNMENT_ID,
    REPUBLICAN_ITERATION_ASSIGNMENT_KEY,
    REPUBLICAN_LAST_ASSIGNMENT_ID,
    REPUBLICAN_MANUAL_TEST_ITERATION_USER_KEY,
    REPUBLICAN_ROW_COUNT,
    STUDY_ASSIGNMENT_COUNTER_TABLE,
    STUDY_ID,
    STUDY_S3_BUCKET,
    USER_ASSIGNMENTS_TABLE,
    experiment_dir,
)
from experiments.upsample_mixed_study_feeds_2026_09_11.split_batch import (
    require_original_party_prefix,
)
from lib.constants import REPO_ROOT


class ObjectStore(Protocol):
    """Minimal S3 object store surface used by the cutover helpers."""

    def get(self, key: str) -> StoredObject | None: ...

    def put_new(self, key: str, body: bytes) -> Any: ...

    def replace(self, key: str, body: bytes, *, etag: str | None) -> Any: ...


@dataclass(frozen=True)
class LiveObjectSnapshot:
    """Pre-cutover bytes, etag, and SHA-256 for one live key."""

    key: str
    body: bytes
    etag: str
    sha256: str


@dataclass(frozen=True)
class PreCutoverSnapshot:
    """Live objects and DynamoDB counters captured before any write."""

    democrat_csv: LiveObjectSnapshot
    republican_csv: LiveObjectSnapshot
    config: LiveObjectSnapshot
    democrat_counter: int
    republican_counter: int


@dataclass(frozen=True)
class CutoverResult:
    """Evidence collected after a successful cutover."""

    snapshot: PreCutoverSnapshot
    democrat_overprovisioned_sha256: str
    republican_overprovisioned_sha256: str
    post_config_sha256: str
    returning_user_checks: tuple[str, ...]


def main() -> int:
    """Run the ordered live cutover and print verification evidence."""
    store = CampaignObjectStore(STUDY_S3_BUCKET, region_name=DYNAMODB_REGION)
    snapshot = snapshot_pre_cutover(store, _dynamodb_client())
    overprovisioned = _load_local_overprovisioned_bytes(REPO_ROOT)
    identity_democrat, identity_republican = _identity_reference_bodies(store, snapshot)
    require_prefix_identity(
        overprovisioned[PARTY_DEMOCRAT],
        overprovisioned[PARTY_REPUBLICAN],
        identity_democrat,
        identity_republican,
    )
    if not _originals_present(store):
        backup_live_objects(store, snapshot)
    else:
        _require_original_backups(store, snapshot)
    if not _live_csv_matches_overprovisioned(store, overprovisioned):
        replace_live_objects(store, snapshot, overprovisioned)
    patched_config = patch_config_counts(snapshot.config.body)
    _replace_live_config(store, patched_config, snapshot.config.etag)
    verify_cutover(
        store,
        snapshot,
        overprovisioned,
        patched_config,
    )
    returning_checks = verify_returning_users(
        store,
        _dynamodb_client(),
        overprovisioned,
        snapshot,
    )
    extra_row_checks = verify_extra_rows(store)
    result = CutoverResult(
        snapshot=snapshot,
        democrat_overprovisioned_sha256=sha256_hex(overprovisioned[PARTY_DEMOCRAT]),
        republican_overprovisioned_sha256=sha256_hex(overprovisioned[PARTY_REPUBLICAN]),
        post_config_sha256=sha256_hex(patched_config),
        returning_user_checks=returning_checks + extra_row_checks,
    )
    _print_cutover_summary(result)
    _write_verify_log(result)
    return 0


def original_assignments_key(party: str) -> str:
    """Return the ``_original`` sibling key for one party assignments CSV."""
    return f"{live_assignments_key(party).removesuffix(ASSIGNMENTS_FILENAME)}{ASSIGNMENTS_ORIGINAL_FILENAME}"


def original_config_key() -> str:
    """Return the ``config_original.yaml`` sibling key."""
    return f"{LIVE_S3_PREFIX}/{CONFIG_ORIGINAL_FILENAME}"


def live_assignments_key(party: str) -> str:
    """Return the live ``assignments.csv`` key for one party."""
    return f"{LIVE_S3_PREFIX}/{party}/{CONDITION}/{ASSIGNMENTS_FILENAME}"


def live_config_key() -> str:
    """Return the live ``config.yaml`` key."""
    return f"{LIVE_S3_PREFIX}/{CONFIG_FILENAME}"


def local_overprovisioned_path(repo_root: Path, party: str) -> Path:
    """Return the local overprovisioned party CSV path."""
    return (
        experiment_dir(repo_root)
        / BATCH_DIRNAME
        / party
        / CONDITION
        / ASSIGNMENTS_OVERPROVISIONED_FILENAME
    )


def patch_config_counts(config_body: bytes) -> bytes:
    """Return live config bytes with updated counts and a timestamped ``s3.prefix``."""
    document = yaml.safe_load(config_body)
    if not isinstance(document, dict):
        raise ValueError("config.yaml must be a mapping")
    s3_section = document.get("s3")
    if not isinstance(s3_section, dict):
        raise ValueError("config.yaml s3 must be a mapping")
    prefix = str(s3_section.get("prefix", ""))
    if LIVE_BATCH_TIMESTAMP not in prefix:
        s3_section["prefix"] = f"{ASSIGNMENT_PREFIX}/{LIVE_BATCH_TIMESTAMP}"
    cells = document.get("cells")
    if not isinstance(cells, list):
        raise ValueError("config.yaml cells must be a list")
    for cell in cells:
        if not isinstance(cell, dict):
            raise ValueError("config.yaml cell must be a mapping")
        party = str(cell.get("political_party", ""))
        condition = str(cell.get("condition", ""))
        if party == PARTY_DEMOCRAT and condition == CONDITION:
            cell["count"] = DEMOCRAT_ROW_COUNT
        elif party == PARTY_REPUBLICAN and condition == CONDITION:
            cell["count"] = REPUBLICAN_ROW_COUNT
    patched = yaml.safe_dump(document, sort_keys=False)
    return patched.encode("utf-8")


def rows_from_csv_bytes(body: bytes) -> list[AssignmentRow]:
    """Parse one assignments CSV body into ``AssignmentRow`` objects."""
    frame = pd.read_csv(io.BytesIO(body))
    missing = [name for name in ASSIGNMENT_COLUMNS if name not in frame.columns]
    if missing:
        raise ValueError(f"missing column {missing[0]}")
    return [_assignment_from_mapping(record) for record in frame.to_dict("records")]


def require_prefix_identity(
    overprovisioned_democrat: bytes,
    overprovisioned_republican: bytes,
    live_democrat: bytes,
    live_republican: bytes,
) -> None:
    """Abort when the overprovisioned prefix does not match live party CSVs."""
    live_d_rows = rows_from_csv_bytes(live_democrat)
    live_r_rows = rows_from_csv_bytes(live_republican)
    over_d_rows = rows_from_csv_bytes(overprovisioned_democrat)
    over_r_rows = rows_from_csv_bytes(overprovisioned_republican)
    require_original_party_prefix(
        over_d_rows,
        over_r_rows,
        live_d_rows[:ORIGINAL_DEMOCRAT_COUNT],
        live_r_rows[:ORIGINAL_REPUBLICAN_COUNT],
    )


def snapshot_pre_cutover(
    store: ObjectStore, dynamodb: Any
) -> PreCutoverSnapshot:
    """Read live or ``_original`` objects and DynamoDB counters without writing."""
    democrat_counter = _read_assignment_counter(
        dynamodb, DEMOCRAT_ITERATION_ASSIGNMENT_KEY
    )
    republican_counter = _read_assignment_counter(
        dynamodb, REPUBLICAN_ITERATION_ASSIGNMENT_KEY
    )
    if democrat_counter > ORIGINAL_DEMOCRAT_COUNT:
        raise ValueError(
            f"democrat_counter={democrat_counter} exceeds {ORIGINAL_DEMOCRAT_COUNT}"
        )
    if republican_counter > ORIGINAL_REPUBLICAN_COUNT:
        raise ValueError(
            f"republican_counter={republican_counter} exceeds {ORIGINAL_REPUBLICAN_COUNT}"
        )
    if _originals_present(store):
        democrat_csv = _snapshot_live_object(
            store, original_assignments_key(PARTY_DEMOCRAT)
        )
        republican_csv = _snapshot_live_object(
            store, original_assignments_key(PARTY_REPUBLICAN)
        )
        config = _snapshot_live_object(store, original_config_key())
    else:
        democrat_csv = _snapshot_live_object(store, live_assignments_key(PARTY_DEMOCRAT))
        republican_csv = _snapshot_live_object(
            store, live_assignments_key(PARTY_REPUBLICAN)
        )
        config = _snapshot_live_object(store, live_config_key())
    return PreCutoverSnapshot(
        democrat_csv=democrat_csv,
        republican_csv=republican_csv,
        config=config,
        democrat_counter=democrat_counter,
        republican_counter=republican_counter,
    )


def backup_live_objects(store: ObjectStore, snapshot: PreCutoverSnapshot) -> None:
    """Write ``_original`` siblings with ``put_new`` before replacing live keys."""
    store.put_new(
        original_assignments_key(PARTY_DEMOCRAT),
        snapshot.democrat_csv.body,
    )
    store.put_new(
        original_assignments_key(PARTY_REPUBLICAN),
        snapshot.republican_csv.body,
    )
    store.put_new(original_config_key(), snapshot.config.body)


def replace_live_objects(
    store: ObjectStore,
    snapshot: PreCutoverSnapshot,
    overprovisioned: dict[str, bytes],
) -> None:
    """Replace live party CSVs with overprovisioned bytes using captured etags."""
    store.replace(
        live_assignments_key(PARTY_DEMOCRAT),
        overprovisioned[PARTY_DEMOCRAT],
        etag=snapshot.democrat_csv.etag,
    )
    store.replace(
        live_assignments_key(PARTY_REPUBLICAN),
        overprovisioned[PARTY_REPUBLICAN],
        etag=snapshot.republican_csv.etag,
    )


def verify_cutover(
    store: ObjectStore,
    snapshot: PreCutoverSnapshot,
    overprovisioned: dict[str, bytes],
    patched_config: bytes,
) -> None:
    """Re-read all six keys and assert post-cutover invariants."""
    live_d = _require_object(store, live_assignments_key(PARTY_DEMOCRAT))
    live_r = _require_object(store, live_assignments_key(PARTY_REPUBLICAN))
    live_config = _require_object(store, live_config_key())
    orig_d = _require_object(store, original_assignments_key(PARTY_DEMOCRAT))
    orig_r = _require_object(store, original_assignments_key(PARTY_REPUBLICAN))
    orig_config = _require_object(store, original_config_key())

    _require_sha(live_d.body, overprovisioned[PARTY_DEMOCRAT], "live democrat csv")
    _require_sha(live_r.body, overprovisioned[PARTY_REPUBLICAN], "live republican csv")
    _require_row_count(live_d.body, DEMOCRAT_ROW_COUNT, "democrat")
    _require_row_count(live_r.body, REPUBLICAN_ROW_COUNT, "republican")

    _require_sha(orig_d.body, snapshot.democrat_csv.body, "original democrat csv")
    _require_sha(orig_r.body, snapshot.republican_csv.body, "original republican csv")
    _require_sha(orig_config.body, snapshot.config.body, "original config")

    require_prefix_identity(live_d.body, live_r.body, orig_d.body, orig_r.body)

    document = yaml.safe_load(live_config.body)
    _require_config_counts(document)
    if LIVE_BATCH_TIMESTAMP not in str(document.get("s3", {}).get("prefix", "")):
        raise ValueError("live config prefix lost timestamp")
    _require_sha(live_config.body, patched_config, "patched live config")


def verify_returning_users(
    store: ObjectStore,
    dynamodb: Any,
    overprovisioned: dict[str, bytes],
    snapshot: PreCutoverSnapshot,
) -> tuple[str, ...]:
    """Confirm stored ``s3_key`` rows still resolve to the new overprovisioned CSV."""
    checks: list[str] = []
    for party, iteration_user_key, first_id, over_bytes, orig_body in (
        (
            PARTY_DEMOCRAT,
            DEMOCRAT_MANUAL_TEST_ITERATION_USER_KEY,
            DEMOCRAT_FIRST_ASSIGNMENT_ID,
            overprovisioned[PARTY_DEMOCRAT],
            snapshot.democrat_csv.body,
        ),
        (
            PARTY_REPUBLICAN,
            REPUBLICAN_MANUAL_TEST_ITERATION_USER_KEY,
            REPUBLICAN_FIRST_ASSIGNMENT_ID,
            overprovisioned[PARTY_REPUBLICAN],
            snapshot.republican_csv.body,
        ),
    ):
        item = _get_user_assignment_item(dynamodb, iteration_user_key)
        if item is None:
            checks.append(f"{iteration_user_key}=missing")
            continue
        s3_key = _extract_s3_key(item)
        stored = _require_object(store, s3_key)
        _require_sha(stored.body, over_bytes, f"returning user {party} csv")
        live_first = _row_by_id(stored.body, first_id)
        orig_first = _row_by_id(orig_body, first_id)
        if live_first.assigned_post_ids != orig_first.assigned_post_ids:
            raise ValueError(f"{first_id} assigned_post_ids changed for {party}")
        checks.append(
            f"{iteration_user_key} s3_key={s3_key} sha256={sha256_hex(stored.body)} "
            f"{first_id}_assigned_post_ids_ok"
        )
    return tuple(checks)


def verify_extra_rows(store: ObjectStore) -> tuple[str, ...]:
    """Confirm the new extra assignment ids exist at the end of each live CSV."""
    live_d = _require_object(store, live_assignments_key(PARTY_DEMOCRAT))
    live_r = _require_object(store, live_assignments_key(PARTY_REPUBLICAN))
    d_frame = pd.read_csv(io.BytesIO(live_d.body))
    r_frame = pd.read_csv(io.BytesIO(live_r.body))
    d_ids = set(d_frame[ASSIGNMENT_ID_COLUMN].astype(str))
    r_ids = set(r_frame[ASSIGNMENT_ID_COLUMN].astype(str))
    required_d = {DEMOCRAT_FIRST_EXTRA_ASSIGNMENT_ID, DEMOCRAT_LAST_ASSIGNMENT_ID}
    required_r = {
        REPUBLICAN_FIRST_EXTRA_ASSIGNMENT_ID,
        REPUBLICAN_LAST_ASSIGNMENT_ID,
    }
    if not required_d.issubset(d_ids):
        raise ValueError(f"missing democrat extra ids: {required_d - d_ids}")
    if not required_r.issubset(r_ids):
        raise ValueError(f"missing republican extra ids: {required_r - r_ids}")
    return (
        f"extra_rows democrat={sorted(required_d)}",
        f"extra_rows republican={sorted(required_r)}",
    )


def _originals_present(store: ObjectStore) -> bool:
    return all(
        store.get(key) is not None
        for key in (
            original_assignments_key(PARTY_DEMOCRAT),
            original_assignments_key(PARTY_REPUBLICAN),
            original_config_key(),
        )
    )


def _require_original_backups(
    store: ObjectStore, snapshot: PreCutoverSnapshot
) -> None:
    for key, expected in (
        (original_assignments_key(PARTY_DEMOCRAT), snapshot.democrat_csv.body),
        (original_assignments_key(PARTY_REPUBLICAN), snapshot.republican_csv.body),
        (original_config_key(), snapshot.config.body),
    ):
        stored = _require_object(store, key)
        _require_sha(stored.body, expected, key)


def _identity_reference_bodies(
    store: ObjectStore, snapshot: PreCutoverSnapshot
) -> tuple[bytes, bytes]:
    if _originals_present(store):
        democrat = _require_object(store, original_assignments_key(PARTY_DEMOCRAT)).body
        republican = _require_object(
            store, original_assignments_key(PARTY_REPUBLICAN)
        ).body
        return democrat, republican
    return snapshot.democrat_csv.body, snapshot.republican_csv.body


def _live_csv_matches_overprovisioned(
    store: ObjectStore, overprovisioned: dict[str, bytes]
) -> bool:
    live_d = store.get(live_assignments_key(PARTY_DEMOCRAT))
    live_r = store.get(live_assignments_key(PARTY_REPUBLICAN))
    if live_d is None or live_r is None:
        return False
    return (
        sha256_hex(live_d.body) == sha256_hex(overprovisioned[PARTY_DEMOCRAT])
        and sha256_hex(live_r.body) == sha256_hex(overprovisioned[PARTY_REPUBLICAN])
    )


def _replace_live_config(
    store: ObjectStore, patched_config: bytes, fallback_etag: str
) -> None:
    current = store.get(live_config_key())
    if current is not None and sha256_hex(current.body) == sha256_hex(patched_config):
        return
    etag = current.etag if current is not None else fallback_etag
    store.replace(live_config_key(), patched_config, etag=etag)


def _load_local_overprovisioned_bytes(repo_root: Path) -> dict[str, bytes]:
    overprovisioned: dict[str, bytes] = {}
    for party in (PARTY_DEMOCRAT, PARTY_REPUBLICAN):
        path = local_overprovisioned_path(repo_root, party)
        if not path.is_file():
            raise FileNotFoundError(path)
        overprovisioned[party] = path.read_bytes()
    return overprovisioned


def _snapshot_live_object(store: ObjectStore, key: str) -> LiveObjectSnapshot:
    stored = _require_object(store, key)
    return LiveObjectSnapshot(
        key=key,
        body=stored.body,
        etag=stored.etag,
        sha256=sha256_hex(stored.body),
    )


def _require_object(store: ObjectStore, key: str) -> StoredObject:
    stored = store.get(key)
    if stored is None:
        raise FileNotFoundError(s3_uri(STUDY_S3_BUCKET, key))
    return stored


def _require_sha(actual: bytes, expected: bytes, label: str) -> None:
    actual_sha = sha256_hex(actual)
    expected_sha = sha256_hex(expected)
    if actual_sha != expected_sha:
        raise ValueError(f"{label} sha256={actual_sha} expected={expected_sha}")


def _require_row_count(body: bytes, expected: int, label: str) -> None:
    frame = pd.read_csv(io.BytesIO(body))
    actual = len(frame)
    if actual != expected:
        raise ValueError(f"{label} rows={actual} expected={expected}")


def _require_config_counts(document: dict[str, Any]) -> None:
    counts = {
        (str(cell["political_party"]), str(cell["condition"])): int(cell["count"])
        for cell in document["cells"]
    }
    if counts[(PARTY_DEMOCRAT, CONDITION)] != DEMOCRAT_ROW_COUNT:
        raise ValueError("democrat config count mismatch")
    if counts[(PARTY_REPUBLICAN, CONDITION)] != REPUBLICAN_ROW_COUNT:
        raise ValueError("republican config count mismatch")


def _assignment_from_mapping(record: dict[str, object]) -> AssignmentRow:
    return AssignmentRow(
        id=str(record[ASSIGNMENT_ID_COLUMN]),
        assigned_post_ids=str(record[ASSIGNED_POST_IDS_COLUMN]),
        political_party=_party_cell(record[POLITICAL_PARTY_COLUMN]),
        condition=str(record[CONDITION_COLUMN]),
        created_at=str(record[CREATED_AT_COLUMN]),
    )


def _party_cell(value: object) -> str:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return EMPTY_POLITICAL_PARTY
    text = str(value).strip()
    if text.lower() == NAN_CELL:
        return EMPTY_POLITICAL_PARTY
    return text


def _row_by_id(body: bytes, assignment_id: str) -> AssignmentRow:
    for row in rows_from_csv_bytes(body):
        if row.id == assignment_id:
            return row
    raise ValueError(f"missing assignment id {assignment_id}")


def _dynamodb_client() -> Any:
    return boto3.client("dynamodb", region_name=DYNAMODB_REGION)


def _read_assignment_counter(dynamodb: Any, iteration_assignment_key: str) -> int:
    response = dynamodb.get_item(
        TableName=STUDY_ASSIGNMENT_COUNTER_TABLE,
        Key={
            "study_id": {"S": STUDY_ID},
            "iteration_assignment_key": {"S": iteration_assignment_key},
        },
    )
    item = response.get("Item")
    if not item:
        return 0
    for name in (
        "counter",
        "assignment_counter",
        "next_index",
        "next_assignment_index",
        "assignment_index",
    ):
        if name in item and "N" in item[name]:
            return int(item[name]["N"])
    raise ValueError(
        f"unknown counter fields for {iteration_assignment_key}: {sorted(item)}"
    )


def _get_user_assignment_item(
    dynamodb: Any, iteration_user_key: str
) -> dict[str, Any] | None:
    response = dynamodb.get_item(
        TableName=USER_ASSIGNMENTS_TABLE,
        Key={
            "study_id": {"S": STUDY_ID},
            "iteration_user_key": {"S": iteration_user_key},
        },
    )
    return response.get("Item")


def _extract_s3_key(item: dict[str, Any]) -> str:
    for name in ("s3_key", "assignment_s3_key", "csv_s3_key"):
        if name in item and "S" in item[name]:
            return str(item[name]["S"])
    payload = item.get("payload", {})
    if isinstance(payload, dict) and "M" in payload:
        mapping = payload["M"]
        for name in ("s3_key", "assignment_s3_key", "csv_s3_key"):
            if name in mapping and "S" in mapping[name]:
                return str(mapping[name]["S"])
    raise ValueError(f"s3_key missing from user assignment item: {sorted(item)}")


def _print_cutover_summary(result: CutoverResult) -> None:
    snapshot = result.snapshot
    print(f"democrat_counter={snapshot.democrat_counter}")
    print(f"republican_counter={snapshot.republican_counter}")
    print(
        "pre_cutover_config_sha256="
        f"{snapshot.config.sha256} hint={PRE_CUTOVER_CONFIG_SHA256}"
    )
    print(
        "pre_cutover_democrat_csv_sha256="
        f"{snapshot.democrat_csv.sha256} hint={PRE_CUTOVER_DEMOCRAT_CSV_SHA256}"
    )
    print(
        "pre_cutover_republican_csv_sha256="
        f"{snapshot.republican_csv.sha256} hint={PRE_CUTOVER_REPUBLICAN_CSV_SHA256}"
    )
    print(f"original_democrat_uri={s3_uri(STUDY_S3_BUCKET, original_assignments_key(PARTY_DEMOCRAT))}")
    print(f"original_republican_uri={s3_uri(STUDY_S3_BUCKET, original_assignments_key(PARTY_REPUBLICAN))}")
    print(f"original_config_uri={s3_uri(STUDY_S3_BUCKET, original_config_key())}")
    print(f"live_democrat_uri={s3_uri(STUDY_S3_BUCKET, live_assignments_key(PARTY_DEMOCRAT))}")
    print(f"live_republican_uri={s3_uri(STUDY_S3_BUCKET, live_assignments_key(PARTY_REPUBLICAN))}")
    print(f"live_config_uri={s3_uri(STUDY_S3_BUCKET, live_config_key())}")
    print(f"live_democrat_sha256={result.democrat_overprovisioned_sha256}")
    print(f"live_republican_sha256={result.republican_overprovisioned_sha256}")
    print(f"live_config_sha256={result.post_config_sha256}")
    print(f"democrat_rows={DEMOCRAT_ROW_COUNT}")
    print(f"republican_rows={REPUBLICAN_ROW_COUNT}")
    for line in result.returning_user_checks:
        print(line)


def _write_verify_log(result: CutoverResult) -> None:
    path = Path(CUTOVER_VERIFY_LOG_PATH)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(_summary_lines(result)) + "\n")


def _summary_lines(result: CutoverResult) -> list[str]:
    snapshot = result.snapshot
    lines = [
        f"democrat_counter={snapshot.democrat_counter}",
        f"republican_counter={snapshot.republican_counter}",
        f"pre_cutover_config_sha256={snapshot.config.sha256}",
        f"pre_cutover_democrat_csv_sha256={snapshot.democrat_csv.sha256}",
        f"pre_cutover_republican_csv_sha256={snapshot.republican_csv.sha256}",
        f"original_democrat_uri={s3_uri(STUDY_S3_BUCKET, original_assignments_key(PARTY_DEMOCRAT))}",
        f"original_republican_uri={s3_uri(STUDY_S3_BUCKET, original_assignments_key(PARTY_REPUBLICAN))}",
        f"original_config_uri={s3_uri(STUDY_S3_BUCKET, original_config_key())}",
        f"live_democrat_uri={s3_uri(STUDY_S3_BUCKET, live_assignments_key(PARTY_DEMOCRAT))}",
        f"live_republican_uri={s3_uri(STUDY_S3_BUCKET, live_assignments_key(PARTY_REPUBLICAN))}",
        f"live_config_uri={s3_uri(STUDY_S3_BUCKET, live_config_key())}",
        f"live_democrat_sha256={result.democrat_overprovisioned_sha256}",
        f"live_republican_sha256={result.republican_overprovisioned_sha256}",
        f"live_config_sha256={result.post_config_sha256}",
        f"democrat_rows={DEMOCRAT_ROW_COUNT}",
        f"republican_rows={REPUBLICAN_ROW_COUNT}",
    ]
    lines.extend(result.returning_user_checks)
    return lines


if __name__ == "__main__":
    sys.exit(main())
