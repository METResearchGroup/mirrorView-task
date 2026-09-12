"""Tests for live cutover helpers using an in-memory object store."""

from __future__ import annotations

import json
from dataclasses import dataclass, field

import pytest
import yaml

from data_platform.generate_features.s3_feature_campaign import (
    ConditionalWriteConflict,
    WriteResult,
)
from data_platform.utils.object_store import sha256_hex
from experiments.load_study_assignments_2026_09_09.constants import (
    ASSIGNMENT_COLUMNS,
    CONDITION,
    PARTY_DEMOCRAT,
    PARTY_REPUBLICAN,
)
from experiments.upsample_mixed_study_feeds_2026_09_11.constants import (
    DEMOCRAT_ROW_COUNT,
    LIVE_BATCH_TIMESTAMP,
    ORIGINAL_DEMOCRAT_COUNT,
    ORIGINAL_REPUBLICAN_COUNT,
    REPUBLICAN_ROW_COUNT,
)
from experiments.upsample_mixed_study_feeds_2026_09_11.cutover import (
    PreCutoverSnapshot,
    backup_live_objects,
    live_assignments_key,
    live_config_key,
    original_assignments_key,
    original_config_key,
    patch_config_counts,
    replace_live_objects,
    require_prefix_identity,
    verify_cutover,
)
from experiments.upsample_mixed_study_feeds_2026_09_11.tests.conftest import source_row


@dataclass
class FakeStore:
    """Dict-backed store matching ``CampaignObjectStore`` write semantics."""

    objects: dict[str, tuple[bytes, str]] = field(default_factory=dict)
    operations: list[tuple[str, str]] = field(default_factory=list)
    _etag_counter: int = 0

    def get(self, key: str):
        stored = self.objects.get(key)
        if stored is None:
            return None
        from data_platform.generate_features.s3_feature_campaign import StoredObject

        body, etag = stored
        return StoredObject(body=body, etag=etag)

    def put_new(self, key: str, body: bytes) -> WriteResult:
        if key in self.objects:
            raise FileExistsError(f"Object already exists: {key}")
        self._etag_counter += 1
        etag = f'"etag-{self._etag_counter}"'
        self.objects[key] = (body, etag)
        self.operations.append(("put_new", key))
        return WriteResult(sha256=sha256_hex(body), etag=etag)

    def replace(self, key: str, body: bytes, *, etag: str | None) -> WriteResult:
        if etag is None:
            if key in self.objects:
                raise ConditionalWriteConflict(f"exists without IfMatch: {key}")
        else:
            stored = self.objects.get(key)
            if stored is None or stored[1] != etag:
                raise ConditionalWriteConflict(f"etag mismatch for {key}")
        self._etag_counter += 1
        new_etag = f'"etag-{self._etag_counter}"'
        self.objects[key] = (body, new_etag)
        self.operations.append(("replace", key))
        return WriteResult(sha256=sha256_hex(body), etag=new_etag)


def _csv_bytes(rows: list) -> bytes:
    import pandas as pd

    from experiments.load_study_assignments_2026_09_09.constants import CSV_ENCODING, CSV_INDEX

    frame = pd.DataFrame([row.__dict__ for row in rows]).loc[:, list(ASSIGNMENT_COLUMNS)]
    return frame.to_csv(index=CSV_INDEX).encode(CSV_ENCODING)


def _party_rows(party: str, count: int, start_index: int = 1) -> list:
    from experiments.load_study_assignments_2026_09_09.constants import AssignmentRow

    prefix = f"{party}-training_assisted"
    rows: list[AssignmentRow] = []
    for index in range(start_index, start_index + count):
        post_ids = [f"{party}-{index}-{slot}" for slot in range(20)]
        rows.append(
            AssignmentRow(
                id=f"{prefix}-{index:04d}",
                assigned_post_ids=json.dumps(post_ids),
                political_party=party,
                condition=CONDITION,
                created_at=source_row(index, post_ids).created_at,
            )
        )
    return rows


def _live_config_bytes() -> bytes:
    document = {
        "name": "mirrorview_2026_09_09",
        "s3": {
            "bucket": "jspsych-mirror-view-2026-09-09",
            "prefix": f"precomputed_assignments/{LIVE_BATCH_TIMESTAMP}",
        },
        "cells": [
            {"political_party": PARTY_DEMOCRAT, "condition": CONDITION, "count": 1940},
            {"political_party": PARTY_REPUBLICAN, "condition": CONDITION, "count": 1939},
        ],
    }
    return yaml.safe_dump(document, sort_keys=False).encode("utf-8")


def _snapshot_from_store(store: FakeStore) -> PreCutoverSnapshot:
    from experiments.upsample_mixed_study_feeds_2026_09_11.cutover import LiveObjectSnapshot

    def snap(key: str) -> LiveObjectSnapshot:
        body, etag = store.objects[key]
        return LiveObjectSnapshot(key=key, body=body, etag=etag, sha256=sha256_hex(body))

    return PreCutoverSnapshot(
        democrat_csv=snap(live_assignments_key(PARTY_DEMOCRAT)),
        republican_csv=snap(live_assignments_key(PARTY_REPUBLICAN)),
        config=snap(live_config_key()),
        democrat_counter=1,
        republican_counter=1,
    )


class TestCutoverHelpers:
    """Cutover ordering, config patch, and verification behavior."""

    def test_backup_writes_originals_before_replace(self) -> None:
        """Verifies ``put_new`` on ``_original`` keys happens before live ``replace``."""
        store = FakeStore()
        live_d = _party_rows(PARTY_DEMOCRAT, ORIGINAL_DEMOCRAT_COUNT)
        live_r = _party_rows(PARTY_REPUBLICAN, ORIGINAL_REPUBLICAN_COUNT)
        store.put_new(live_assignments_key(PARTY_DEMOCRAT), _csv_bytes(live_d))
        store.put_new(live_assignments_key(PARTY_REPUBLICAN), _csv_bytes(live_r))
        store.put_new(live_config_key(), _live_config_bytes())
        store.operations.clear()

        snapshot = _snapshot_from_store(store)
        overprovisioned = {
            PARTY_DEMOCRAT: _csv_bytes(
                live_d + _party_rows(PARTY_DEMOCRAT, 500, ORIGINAL_DEMOCRAT_COUNT + 1)
            ),
            PARTY_REPUBLICAN: _csv_bytes(
                live_r
                + _party_rows(PARTY_REPUBLICAN, 500, ORIGINAL_REPUBLICAN_COUNT + 1)
            ),
        }

        backup_live_objects(store, snapshot)
        replace_live_objects(store, snapshot, overprovisioned)

        backup_ops = [op for op in store.operations if op[0] == "put_new"]
        replace_ops = [op for op in store.operations if op[0] == "replace"]
        assert [key for _, key in backup_ops] == [
            original_assignments_key(PARTY_DEMOCRAT),
            original_assignments_key(PARTY_REPUBLICAN),
            original_config_key(),
        ]
        assert backup_ops[-1][1] == original_config_key()
        assert replace_ops[0][1] == live_assignments_key(PARTY_DEMOCRAT)
        assert all(
            store.operations.index(backup_op) < store.operations.index(replace_ops[0])
            for backup_op in backup_ops
        )

    def test_second_backup_raises_file_exists_error(self) -> None:
        """Verifies a second cutover aborts on existing ``_original`` keys."""
        store = FakeStore()
        live_d = _party_rows(PARTY_DEMOCRAT, ORIGINAL_DEMOCRAT_COUNT)
        live_r = _party_rows(PARTY_REPUBLICAN, ORIGINAL_REPUBLICAN_COUNT)
        store.put_new(live_assignments_key(PARTY_DEMOCRAT), _csv_bytes(live_d))
        store.put_new(live_assignments_key(PARTY_REPUBLICAN), _csv_bytes(live_r))
        store.put_new(live_config_key(), _live_config_bytes())
        snapshot = _snapshot_from_store(store)
        overprovisioned = {
            PARTY_DEMOCRAT: _csv_bytes(
                live_d + _party_rows(PARTY_DEMOCRAT, 500, ORIGINAL_DEMOCRAT_COUNT + 1)
            ),
            PARTY_REPUBLICAN: _csv_bytes(
                live_r
                + _party_rows(PARTY_REPUBLICAN, 500, ORIGINAL_REPUBLICAN_COUNT + 1)
            ),
        }
        backup_live_objects(store, snapshot)
        replace_live_objects(store, snapshot, overprovisioned)

        with pytest.raises(FileExistsError):
            backup_live_objects(store, snapshot)

        assert sha256_hex(store.objects[live_assignments_key(PARTY_DEMOCRAT)][0]) == sha256_hex(
            overprovisioned[PARTY_DEMOCRAT]
        )

    def test_replace_uses_etag_from_get(self) -> None:
        """Verifies ``replace`` fails when the live etag no longer matches."""
        from experiments.upsample_mixed_study_feeds_2026_09_11.cutover import LiveObjectSnapshot

        store = FakeStore()
        live_d = _party_rows(PARTY_DEMOCRAT, ORIGINAL_DEMOCRAT_COUNT)
        live_d_body = _csv_bytes(live_d)
        store.put_new(live_assignments_key(PARTY_DEMOCRAT), live_d_body)
        body, etag = store.objects[live_assignments_key(PARTY_DEMOCRAT)]
        stale_snapshot = PreCutoverSnapshot(
            democrat_csv=LiveObjectSnapshot(
                key=live_assignments_key(PARTY_DEMOCRAT),
                body=body,
                etag='"stale-etag"',
                sha256=sha256_hex(body),
            ),
            republican_csv=LiveObjectSnapshot(
                key=live_assignments_key(PARTY_REPUBLICAN),
                body=b"",
                etag='"unused"',
                sha256=sha256_hex(b""),
            ),
            config=LiveObjectSnapshot(
                key=live_config_key(),
                body=b"",
                etag='"unused"',
                sha256=sha256_hex(b""),
            ),
            democrat_counter=1,
            republican_counter=1,
        )
        overprovisioned = {
            PARTY_DEMOCRAT: _csv_bytes(
                live_d + _party_rows(PARTY_DEMOCRAT, 500, ORIGINAL_DEMOCRAT_COUNT + 1)
            ),
            PARTY_REPUBLICAN: _csv_bytes(_party_rows(PARTY_REPUBLICAN, ORIGINAL_REPUBLICAN_COUNT)),
        }

        with pytest.raises(ConditionalWriteConflict):
            replace_live_objects(store, stale_snapshot, overprovisioned)

    def test_patch_config_counts_only_changes_counts_and_keeps_prefix(self) -> None:
        """Verifies config patch updates counts and keeps the timestamp prefix."""
        patched = patch_config_counts(_live_config_bytes())
        document = yaml.safe_load(patched)
        counts = {
            (cell["political_party"], cell["condition"]): cell["count"]
            for cell in document["cells"]
        }
        assert counts[(PARTY_DEMOCRAT, CONDITION)] == DEMOCRAT_ROW_COUNT
        assert counts[(PARTY_REPUBLICAN, CONDITION)] == REPUBLICAN_ROW_COUNT
        assert LIVE_BATCH_TIMESTAMP in document["s3"]["prefix"]

    def test_verify_cutover_fails_when_live_sha_differs(self) -> None:
        """Verifies post-cutover verification fails on SHA mismatch."""
        store = FakeStore()
        live_d = _party_rows(PARTY_DEMOCRAT, ORIGINAL_DEMOCRAT_COUNT)
        live_r = _party_rows(PARTY_REPUBLICAN, ORIGINAL_REPUBLICAN_COUNT)
        over_d = live_d + _party_rows(PARTY_DEMOCRAT, 500, ORIGINAL_DEMOCRAT_COUNT + 1)
        over_r = live_r + _party_rows(PARTY_REPUBLICAN, 500, ORIGINAL_REPUBLICAN_COUNT + 1)
        store.put_new(live_assignments_key(PARTY_DEMOCRAT), _csv_bytes(over_d))
        store.put_new(live_assignments_key(PARTY_REPUBLICAN), _csv_bytes(over_r))
        store.put_new(live_config_key(), patch_config_counts(_live_config_bytes()))
        store.put_new(original_assignments_key(PARTY_DEMOCRAT), _csv_bytes(live_d))
        store.put_new(original_assignments_key(PARTY_REPUBLICAN), _csv_bytes(live_r))
        store.put_new(original_config_key(), _live_config_bytes())
        snapshot = PreCutoverSnapshot(
            democrat_csv=_snapshot_from_store(store).democrat_csv.__class__(
                key=live_assignments_key(PARTY_DEMOCRAT),
                body=_csv_bytes(live_d),
                etag=store.objects[live_assignments_key(PARTY_DEMOCRAT)][1],
                sha256=sha256_hex(_csv_bytes(live_d)),
            ),
            republican_csv=_snapshot_from_store(store).republican_csv.__class__(
                key=live_assignments_key(PARTY_REPUBLICAN),
                body=_csv_bytes(live_r),
                etag=store.objects[live_assignments_key(PARTY_REPUBLICAN)][1],
                sha256=sha256_hex(_csv_bytes(live_r)),
            ),
            config=_snapshot_from_store(store).config,
            democrat_counter=1,
            republican_counter=1,
        )
        wrong_overprovisioned = {
            PARTY_DEMOCRAT: _csv_bytes(_party_rows(PARTY_DEMOCRAT, DEMOCRAT_ROW_COUNT, 99)),
            PARTY_REPUBLICAN: _csv_bytes(over_r),
        }

        with pytest.raises(ValueError, match="live democrat csv"):
            verify_cutover(
                store,
                snapshot,
                wrong_overprovisioned,
                patch_config_counts(_live_config_bytes()),
            )

    def test_require_prefix_identity_raises_on_mismatch(self) -> None:
        """Verifies the identity gate fails when prefixes diverge."""
        live_d = _csv_bytes(_party_rows(PARTY_DEMOCRAT, ORIGINAL_DEMOCRAT_COUNT))
        live_r = _csv_bytes(_party_rows(PARTY_REPUBLICAN, ORIGINAL_REPUBLICAN_COUNT))
        over_d = _csv_bytes(_party_rows(PARTY_DEMOCRAT, DEMOCRAT_ROW_COUNT, 99))

        with pytest.raises(ValueError):
            require_prefix_identity(over_d, live_r, live_d, live_r)
