"""Copy issue 326's prepared Study 2 input, and reject a mismatch in the digest, the row counts, or the post IDs.

Run from repo root::

    PYTHONPATH=. uv run python -m experiments.zero_shot_jev_inference_2026_10_01.src.step1_setup.prepare
"""

from __future__ import annotations

from data_platform.generate_features.s3_feature_campaign import CampaignObjectStore

from experiments.zero_shot_jev_inference_2026_10_01.shared.config import JevInferenceVariant
from experiments.zero_shot_jev_inference_2026_10_01.shared.constants import (
    EXPECTED_ALL,
    EXPECTED_SPLIT,
    EXPECTED_UNANIMOUS,
    INPUT_MANIFEST_KEY,
    INPUT_RECORDS_KEY,
    S3_BUCKET,
    SOURCE_INPUT_MANIFEST_KEY,
    SOURCE_INPUT_RECORDS_KEY,
)
from experiments.zero_shot_llm_inference_2026_09_30.shared.schemas import (
    InputManifest,
    Study2InputRecord,
)
from experiments.zero_shot_llm_inference_2026_09_30.shared.storage import (
    apply_lab_aws_credentials_when_unset,
    parse_study2_input_jsonl_bytes,
    serialize_json_document,
    sha256_hex,
)


def prepare_input(store: CampaignObjectStore) -> InputManifest:
    """Copy the source records and manifest after every check passes.

    Parameters
    ----------
    store
        Object store that can read the source prefix and create new keys.

    Returns
    -------
    InputManifest
        Parsed source manifest. The copied bytes are unchanged.

    Raises
    ------
    FileNotFoundError
        When either source object is missing.
    ValueError
        When the digest, counts, or post IDs do not match the contract.
    FileExistsError
        When a target key already exists. Existing bytes are left in place.
    """
    records_bytes = _read_required_object(store, SOURCE_INPUT_RECORDS_KEY)
    manifest_bytes = _read_required_object(store, SOURCE_INPUT_MANIFEST_KEY)
    manifest = InputManifest.model_validate_json(manifest_bytes)
    _reject_invalid_input(records_bytes, manifest)
    store.put_new(INPUT_RECORDS_KEY, records_bytes)
    store.put_new(INPUT_MANIFEST_KEY, manifest_bytes)
    return manifest


def copy_prepared_input(
    store: CampaignObjectStore,
    source: JevInferenceVariant,
    target: JevInferenceVariant,
) -> InputManifest:
    """Copy verified source records and write a target manifest for those bytes.

    Parameters
    ----------
    store
        Object store that can read ``source`` and create ``target`` keys.
    source
        Experiment whose records and manifest are copied.
    target
        Experiment that receives the same record bytes.

    Returns
    -------
    InputManifest
        Target manifest. Only ``records_s3_key`` differs from the source.

    Raises
    ------
    FileNotFoundError
        When either source object is missing.
    ValueError
        When the digest, counts, order, or endpoint post IDs do not match.
    FileExistsError
        When a target key already exists. Existing bytes are left in place.
    """
    records_bytes = _read_required_object(store, source.input_records_key)
    manifest = InputManifest.model_validate_json(
        _read_required_object(store, source.input_manifest_key)
    )
    _reject_invalid_input(records_bytes, manifest)
    records = parse_study2_input_jsonl_bytes(records_bytes)
    _reject_endpoint_mismatch(records, manifest)
    target_manifest = manifest.model_copy(update={"records_s3_key": target.input_records_key})
    _write_copied_input(store, target, records_bytes, target_manifest)
    return target_manifest


def main() -> None:
    """Copy the prepared input and print one summary line."""
    apply_lab_aws_credentials_when_unset()
    store = CampaignObjectStore(S3_BUCKET)
    manifest = prepare_input(store)
    records = parse_study2_input_jsonl_bytes(_read_required_object(store, INPUT_RECORDS_KEY))
    print(_summary_line(manifest, records))


def _read_required_object(store: CampaignObjectStore, key: str) -> bytes:
    stored = store.get(key)
    if stored is None:
        raise FileNotFoundError(key)
    return stored.body


def _reject_invalid_input(records_bytes: bytes, manifest: InputManifest) -> None:
    digest = sha256_hex(records_bytes)
    if digest != manifest.records_sha256:
        raise ValueError("prepared input records digest mismatch")
    _reject_manifest_counts(manifest)
    records = parse_study2_input_jsonl_bytes(records_bytes)
    _reject_post_id_order(records)


def _reject_manifest_counts(manifest: InputManifest) -> None:
    if manifest.total_record_count != EXPECTED_ALL:
        raise ValueError("total record count mismatch")
    if manifest.unanimous_record_count != EXPECTED_UNANIMOUS:
        raise ValueError("unanimous record count mismatch")
    if manifest.split_record_count != EXPECTED_SPLIT:
        raise ValueError("split record count mismatch")


def _reject_endpoint_mismatch(
    records: list[Study2InputRecord],
    manifest: InputManifest,
) -> None:
    if records[0].post_id != manifest.first_post_id:
        raise ValueError("first post id mismatch")
    if records[-1].post_id != manifest.last_post_id:
        raise ValueError("last post id mismatch")


def _write_copied_input(
    store: CampaignObjectStore,
    target: JevInferenceVariant,
    records_bytes: bytes,
    manifest: InputManifest,
) -> None:
    store.put_new(target.input_records_key, records_bytes)
    body = serialize_json_document(manifest.model_dump(mode="json"))
    store.put_new(target.input_manifest_key, body)


def _reject_post_id_order(records: list[Study2InputRecord]) -> None:
    post_ids = [record.post_id for record in records]
    if len(post_ids) != EXPECTED_ALL:
        raise ValueError("parsed record count mismatch")
    if len(set(post_ids)) != EXPECTED_ALL:
        raise ValueError("duplicate prepared post_id")
    if post_ids != sorted(post_ids):
        raise ValueError("post_id values are not in ascending order")


def _summary_line(manifest: InputManifest, records: list[Study2InputRecord]) -> str:
    unique_count = len({record.post_id for record in records})
    return (
        f"records_key={INPUT_RECORDS_KEY} manifest_key={INPUT_MANIFEST_KEY} "
        f"rows={manifest.total_record_count} unique_post_ids={unique_count} "
        f"unanimous_rows={manifest.unanimous_record_count} "
        f"split_rows={manifest.split_record_count} sha256_matches_source=true"
    )


if __name__ == "__main__":
    main()
