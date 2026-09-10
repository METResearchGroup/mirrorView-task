"""Write party assignment files, batch config, catalog, and verification JSON.

Run from the repo root:

    PYTHONPATH=. uv run python experiments/load_study_assignments_2026_09_09/run.py
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from data_platform.utils.object_store import sha256_hex
from experiments.load_study_assignments_2026_09_09.catalog import (
    collect_assigned_ids,
    stance_by_id,
)
from experiments.load_study_assignments_2026_09_09.constants import (
    ASSIGNMENT_COLUMNS,
    ASSIGNMENT_PREFIX,
    ASSIGNMENTS_FILENAME,
    AssignmentRow,
    BATCH_DIRNAME,
    CATALOG_COLUMNS,
    CATALOG_FILENAME,
    CONDITION,
    CONFIG_FILENAME,
    CSV_ENCODING,
    CSV_INDEX,
    DEMOCRAT_LEFT_ONLY_COUNT,
    DEMOCRAT_ROW_COUNT,
    EXPERIMENT_DIRNAME,
    FIRST_ASSIGNMENT_INDEX,
    LoadRunResult,
    LocalFileWrite,
    MIRROR_TEXT_COLUMN,
    ORIGINAL_TEXT_COLUMN,
    PARTY_DEMOCRAT,
    PARTY_REPUBLICAN,
    POST_ID_COLUMN,
    REPUBLICAN_LEFT_ONLY_COUNT,
    REPUBLICAN_ROW_COUNT,
    STANCE_COLUMN,
    STUDY_BUCKET,
    STUDY_NAME,
    VERIFICATION_FILENAME,
    format_assignment_id,
)
from experiments.load_study_assignments_2026_09_09.split import (
    FeedKind,
    count_kind,
    feed_kind,
    parse_post_ids,
)
from lib.constants import REPO_ROOT

INPUT_POSTS_PATH = (
    f"experiments/{EXPERIMENT_DIRNAME}/{BATCH_DIRNAME}/{CATALOG_FILENAME}"
)
LOCAL_DATA_DIR = f"experiments/{EXPERIMENT_DIRNAME}/{BATCH_DIRNAME}"
CONFIG_YAML = f"""name: {STUDY_NAME}
input_posts_path: {INPUT_POSTS_PATH}
local_data_dir: {LOCAL_DATA_DIR}
s3:
  bucket: {STUDY_BUCKET}
  prefix: {ASSIGNMENT_PREFIX}
cells:
  - political_party: {PARTY_DEMOCRAT}
    condition: {CONDITION}
    count: {DEMOCRAT_ROW_COUNT}
  - political_party: {PARTY_REPUBLICAN}
    condition: {CONDITION}
    count: {REPUBLICAN_ROW_COUNT}
"""


def write_batch(
    democrat: list[AssignmentRow],
    republican: list[AssignmentRow],
    catalog: pd.DataFrame,
    experiment_dir: Path,
) -> LoadRunResult:
    """Write config, party CSVs, catalog, and verification JSON under ``batch/``."""
    batch_dir = experiment_dir / BATCH_DIRNAME
    _write_config(batch_dir)
    _write_assignments(democrat, _party_csv_path(batch_dir, PARTY_DEMOCRAT))
    _write_assignments(republican, _party_csv_path(batch_dir, PARTY_REPUBLICAN))
    catalog_write = _write_catalog(catalog, batch_dir / CATALOG_FILENAME)
    _write_verification(democrat, republican, catalog, experiment_dir)
    return _run_result(democrat, republican, catalog, batch_dir, catalog_write.body)


def print_run_summary(result: LoadRunResult) -> None:
    """Print party counts, catalog size, and the local batch path."""
    print(f"democrat_rows={result.democrat_rows}")
    print(f"republican_rows={result.republican_rows}")
    print(f"catalog_rows={result.catalog_rows}")
    print(f"local_path={result.local_path}")


def _write_config(batch_dir: Path) -> Path:
    path = batch_dir / CONFIG_FILENAME
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(CONFIG_YAML)
    return path


def _write_assignments(rows: list[AssignmentRow], path: Path) -> LocalFileWrite:
    frame = pd.DataFrame([row.__dict__ for row in rows]).loc[:, list(ASSIGNMENT_COLUMNS)]
    body = frame.to_csv(index=CSV_INDEX).encode(CSV_ENCODING)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(body)
    return LocalFileWrite(path=path, body=body)


def _write_catalog(catalog: pd.DataFrame, path: Path) -> LocalFileWrite:
    ordered = catalog.loc[:, list(CATALOG_COLUMNS)]
    body = ordered.to_csv(index=CSV_INDEX).encode(CSV_ENCODING)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(body)
    return LocalFileWrite(path=path, body=body)


def _party_csv_path(batch_dir: Path, party: str) -> Path:
    return batch_dir / party / CONDITION / ASSIGNMENTS_FILENAME


def _run_result(
    democrat: list[AssignmentRow],
    republican: list[AssignmentRow],
    catalog: pd.DataFrame,
    batch_dir: Path,
    catalog_body: bytes,
) -> LoadRunResult:
    return LoadRunResult(
        democrat_rows=len(democrat),
        republican_rows=len(republican),
        catalog_rows=len(catalog),
        local_path=str(batch_dir.relative_to(REPO_ROOT)),
        catalog_sha256=sha256_hex(catalog_body),
    )


def _write_verification(
    democrat: list[AssignmentRow],
    republican: list[AssignmentRow],
    catalog: pd.DataFrame,
    experiment_dir: Path,
) -> Path:
    payload = _verification_payload(democrat, republican, catalog)
    path = experiment_dir / VERIFICATION_FILENAME
    path.write_text(json.dumps(payload, separators=(",", ":")))
    return path


def _verification_payload(
    democrat: list[AssignmentRow],
    republican: list[AssignmentRow],
    catalog: pd.DataFrame,
) -> dict[str, object]:
    posts = _verification_posts(catalog)
    index_by_id = {post[0]: index for index, post in enumerate(posts)}
    stance_lookup = stance_by_id(catalog)
    feeds = _verification_feeds(democrat + republican, index_by_id, stance_lookup)
    return {
        "meta": _verification_meta(democrat, republican, catalog, stance_lookup),
        "posts": posts,
        "feeds": feeds,
        "checks": _verification_checks(democrat, republican, catalog, stance_lookup),
    }


def _verification_posts(catalog: pd.DataFrame) -> list[list[str]]:
    ids = catalog[POST_ID_COLUMN].astype(str).tolist()
    stances = catalog[STANCE_COLUMN].astype(str).tolist()
    originals = catalog[ORIGINAL_TEXT_COLUMN].astype(str).tolist()
    mirrors = catalog[MIRROR_TEXT_COLUMN].astype(str).tolist()
    return [
        [post_id, stance, original, mirror]
        for post_id, stance, original, mirror in zip(
            ids, stances, originals, mirrors
        )
    ]


def _verification_feeds(
    rows: list[AssignmentRow],
    index_by_id: dict[str, int],
    stance_lookup: dict[str, str],
) -> list[list[object]]:
    return [
        _verification_feed(row, index_by_id, stance_lookup) for row in rows
    ]


def _verification_feed(
    row: AssignmentRow,
    index_by_id: dict[str, int],
    stance_lookup: dict[str, str],
) -> list[object]:
    post_ids = parse_post_ids(row.assigned_post_ids)
    kind = feed_kind(post_ids, stance_lookup).value
    indexes = [index_by_id[post_id] for post_id in post_ids]
    return [row.id, row.political_party, kind, indexes]


def _verification_meta(
    democrat: list[AssignmentRow],
    republican: list[AssignmentRow],
    catalog: pd.DataFrame,
    stance_lookup: dict[str, str],
) -> dict[str, object]:
    return {
        "democrat_rows": len(democrat),
        "republican_rows": len(republican),
        **_kind_counts(democrat, republican, stance_lookup),
        "catalog_rows": len(catalog),
        "assigned_post_ids": len(collect_assigned_ids(democrat + republican)),
        **_first_last_ids(democrat, republican),
    }


def _kind_counts(
    democrat: list[AssignmentRow],
    republican: list[AssignmentRow],
    stance_lookup: dict[str, str],
) -> dict[str, int]:
    return {
        "democrat_ten_ten": count_kind(democrat, stance_lookup, FeedKind.TEN_TEN),
        "republican_ten_ten": count_kind(republican, stance_lookup, FeedKind.TEN_TEN),
        "democrat_left_only": count_kind(democrat, stance_lookup, FeedKind.LEFT_ONLY),
        "republican_left_only": count_kind(
            republican, stance_lookup, FeedKind.LEFT_ONLY
        ),
    }


def _first_last_ids(
    democrat: list[AssignmentRow], republican: list[AssignmentRow]
) -> dict[str, str]:
    return {
        "first_democrat_id": democrat[0].id,
        "last_democrat_id": democrat[-1].id,
        "first_republican_id": republican[0].id,
        "last_republican_id": republican[-1].id,
    }


def _verification_checks(
    democrat: list[AssignmentRow],
    republican: list[AssignmentRow],
    catalog: pd.DataFrame,
    stance_lookup: dict[str, str],
) -> list[dict[str, object]]:
    return [
        *_count_checks(democrat, republican, stance_lookup),
        *_coverage_checks(democrat, republican, catalog),
    ]


def _count_checks(
    democrat: list[AssignmentRow],
    republican: list[AssignmentRow],
    stance_lookup: dict[str, str],
) -> list[dict[str, object]]:
    democrat_left = count_kind(democrat, stance_lookup, FeedKind.LEFT_ONLY)
    republican_left = count_kind(republican, stance_lookup, FeedKind.LEFT_ONLY)
    return [
        _check("democrat_rows", len(democrat) == DEMOCRAT_ROW_COUNT, len(democrat)),
        _check("republican_rows", len(republican) == REPUBLICAN_ROW_COUNT, len(republican)),
        _check("democrat_left_only", democrat_left == DEMOCRAT_LEFT_ONLY_COUNT, democrat_left),
        _check(
            "republican_left_only",
            republican_left == REPUBLICAN_LEFT_ONLY_COUNT,
            republican_left,
        ),
    ]


def _coverage_checks(
    democrat: list[AssignmentRow],
    republican: list[AssignmentRow],
    catalog: pd.DataFrame,
) -> list[dict[str, object]]:
    assigned_ids = collect_assigned_ids(democrat + republican)
    catalog_ids = set(catalog[POST_ID_COLUMN].astype(str))
    disjoint = _assigned_json_disjoint(democrat, republican)
    return [
        _check("disjoint_feeds", disjoint, disjoint),
        _check("catalog_covers_assignments", assigned_ids <= catalog_ids, len(assigned_ids)),
        *_contiguous_id_checks(democrat, republican),
    ]


def _contiguous_id_checks(
    democrat: list[AssignmentRow], republican: list[AssignmentRow]
) -> list[dict[str, object]]:
    return [
        _check(
            "democrat_ids_contiguous",
            _ids_are_contiguous(democrat, PARTY_DEMOCRAT, DEMOCRAT_ROW_COUNT),
            democrat[0].id,
        ),
        _check(
            "republican_ids_contiguous",
            _ids_are_contiguous(republican, PARTY_REPUBLICAN, REPUBLICAN_ROW_COUNT),
            republican[0].id,
        ),
    ]


def _check(check_id: str, ok: bool, detail: object) -> dict[str, object]:
    return {"id": check_id, "ok": ok, "detail": detail}


def _assigned_json_disjoint(
    democrat: list[AssignmentRow], republican: list[AssignmentRow]
) -> bool:
    democrat_json = {row.assigned_post_ids for row in democrat}
    republican_json = {row.assigned_post_ids for row in republican}
    return democrat_json.isdisjoint(republican_json)


def _ids_are_contiguous(rows: list[AssignmentRow], party: str, count: int) -> bool:
    last_index = FIRST_ASSIGNMENT_INDEX + count
    expected = [
        format_assignment_id(party, index)
        for index in range(FIRST_ASSIGNMENT_INDEX, last_index)
    ]
    return [row.id for row in rows] == expected
