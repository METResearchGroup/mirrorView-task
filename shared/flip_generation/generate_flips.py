"""Generate politically mirrored posts and write immutable S3 parquet parts.

Run from the repo root:

    PYTHONPATH=. uv run python -c "from shared.flip_generation.generate_flips import BATCH_SIZE, generate_flips; print(BATCH_SIZE)"

Smoke (manual, not pytest):

    given a two-row posts frame with required columns and a fake Converse client
    and an in-memory store
    when generate_flips is called with BATCH_SIZE, MAX_CONCURRENCY, MAX_TOKENS, and DEFAULT_BEDROCK_SONNET_MODEL
    then one part object exists
    and flips.parquet exists
    and FlipRunResult.row_count is 2
    and FlipRunResult.wrote_final is true

    given the same store and run_prefix
    when generate_flips is called again
    then the fake client is not called
    and FlipRunResult.row_count is 2
"""

from __future__ import annotations

import json

import pandas as pd

from data_platform.generate_features.engines.base import RecordLabelFailure, batched
from data_platform.generate_features.engines.bedrock_engine import (
    BedrockRuntimeClient,
    label_tasks_collecting_failures,
)
from data_platform.generate_features.models import LabelTask
from data_platform.generate_features.s3_feature_batches import parquet_rows, rows_to_parquet_bytes
from data_platform.generate_features.s3_feature_campaign import (
    CampaignObjectStore,
    INTERMEDIATE_ARTIFACT_TAG,
)
from lib.timestamp_utils import get_current_timestamp

from shared.flip_generation.models import FLIP_PARQUET_COLUMNS, FlipRow, FlipRunResult
from shared.flip_generation.prompts import USER_MESSAGE_TEMPLATE, flip_feature_spec
from shared.flip_generation.s3_parts import BATCHES_DIRNAME, errors_key, final_key, part_key

BATCH_SIZE = 25
MAX_CONCURRENCY = 10
MAX_TOKENS = 2048
FEATURE_NAME = "flip"
RECORD_ID_COLUMN = "record_id"
TEXT_COLUMN = "text"
STANCE_COLUMN = "political_stance"
TOXICITY_COLUMN = "llm_toxicity_tier"
SORT_KIND = "mergesort"
LEFT_STANCE = "left"
RIGHT_STANCE = "right"
REQUIRED_COLUMNS = (
    RECORD_ID_COLUMN,
    TEXT_COLUMN,
    STANCE_COLUMN,
    TOXICITY_COLUMN,
)
TARGET_GROUP_BY_STANCE = {
    LEFT_STANCE: RIGHT_STANCE,
    RIGHT_STANCE: LEFT_STANCE,
}


def _validate_posts(posts: pd.DataFrame) -> pd.DataFrame:
    """Validate required columns and stances, then sort by record id.

    Parameters
    ----------
    posts
        Input table with record id, text, stance, and toxicity tier.

    Returns
    -------
    pd.DataFrame
        Copy of ``posts`` sorted by ``RECORD_ID_COLUMN``.

    Raises
    ------
    ValueError
        When a required column is missing, ``record_id`` is duplicated,
        ``political_stance`` is not ``left`` or ``right``, or
        ``llm_toxicity_tier`` is missing or empty.
    """
    missing_columns = [
        column_name
        for column_name in REQUIRED_COLUMNS
        if column_name not in posts.columns
    ]
    if missing_columns:
        raise ValueError(f"posts is missing required columns: {missing_columns}")
    if posts[RECORD_ID_COLUMN].duplicated().any():
        raise ValueError("duplicate record_id values")
    validated_posts = posts.copy()
    for row_index, stance_value in validated_posts[STANCE_COLUMN].items():
        stance_text = str(stance_value)
        if stance_text not in (LEFT_STANCE, RIGHT_STANCE):
            raise ValueError(f"invalid political_stance: {stance_text!r}")
    for row_index, toxicity_value in validated_posts[TOXICITY_COLUMN].items():
        if pd.isna(toxicity_value):
            raise ValueError(f"missing llm_toxicity_tier for record_id={validated_posts.at[row_index, RECORD_ID_COLUMN]!r}")
        toxicity_text = str(toxicity_value)
        if not toxicity_text:
            raise ValueError(f"missing llm_toxicity_tier for record_id={validated_posts.at[row_index, RECORD_ID_COLUMN]!r}")
        validated_posts.at[row_index, TOXICITY_COLUMN] = toxicity_text
    return validated_posts.sort_values(RECORD_ID_COLUMN, kind=SORT_KIND)


def _build_label_tasks(posts: pd.DataFrame) -> list[LabelTask]:
    """Build LabelTask rows from validated posts.

    Parameters
    ----------
    posts
        Validated posts sorted by record id.

    Returns
    -------
    list[LabelTask]
        One task per row with opposite-stance target group in the user message.
    """
    label_tasks: list[LabelTask] = []
    for _, post_row in posts.iterrows():
        stance_text = str(post_row[STANCE_COLUMN])
        target_group = TARGET_GROUP_BY_STANCE[stance_text]
        label_tasks.append(
            LabelTask(
                uri=str(post_row[RECORD_ID_COLUMN]),
                text=USER_MESSAGE_TEMPLATE.format(
                    target_group=target_group,
                    original_text=str(post_row[TEXT_COLUMN]),
                ),
            )
        )
    return label_tasks


def _batches_prefix(run_prefix: str) -> str:
    return f"{run_prefix}{BATCHES_DIRNAME}/"


def _load_seen_ids(store: CampaignObjectStore, run_prefix: str) -> set[str]:
    """Return record ids already present in batch parts or the errors log."""
    seen_ids: set[str] = set()
    for object_key in store.list_keys(_batches_prefix(run_prefix)):
        if not object_key.endswith(".parquet"):
            continue
        stored_part = store.get(object_key)
        if stored_part is None:
            continue
        part_frame = parquet_rows(stored_part.body)
        seen_ids.update(part_frame[RECORD_ID_COLUMN].astype(str).tolist())
    stored_errors = store.get(errors_key(run_prefix))
    if stored_errors is not None:
        for line in stored_errors.body.decode("utf-8").splitlines():
            if not line.strip():
                continue
            error_record = json.loads(line)
            seen_ids.add(str(error_record["source_record_id"]))
    return seen_ids


def _join_flip_rows(posts: pd.DataFrame, engine_rows: list[dict]) -> list[FlipRow]:
    """Join Bedrock engine rows to the input table and validate as FlipRow."""
    posts_by_id = posts.set_index(RECORD_ID_COLUMN, drop=False)
    flip_rows: list[FlipRow] = []
    for engine_row in engine_rows:
        record_id = str(engine_row["source_record_id"])
        post_row = posts_by_id.loc[record_id]
        if isinstance(post_row, pd.DataFrame):
            post_row = post_row.iloc[0]
        flip_rows.append(
            FlipRow(
                record_id=record_id,
                original_text=str(post_row[TEXT_COLUMN]),
                llm_toxicity_tier=str(post_row[TOXICITY_COLUMN]),
                political_stance=str(post_row[STANCE_COLUMN]),
                mirrored_text=engine_row["flipped_text"],
                explanation=engine_row["explanation"],
                label_timestamp=engine_row["label_timestamp"],
            )
        )
    return flip_rows


def _write_flip_part(
    store: CampaignObjectStore,
    object_key: str,
    flip_rows: list[FlipRow],
) -> None:
    """Write one immutable parquet part with the intermediate artifact tag."""
    row_dicts = [flip_row.model_dump() for flip_row in flip_rows]
    parquet_bytes = rows_to_parquet_bytes(row_dicts, FLIP_PARQUET_COLUMNS)
    store.put_new(object_key, parquet_bytes, tags=INTERMEDIATE_ARTIFACT_TAG)


def _failure_records(
    failures: list[RecordLabelFailure],
    part_index: int,
) -> list[dict[str, object]]:
    """Build JSONL error records for one batch."""
    return [
        {
            "source_record_id": failure.source_record_id,
            "error": failure.error,
            "attempts": failure.attempts,
            "part_index": part_index,
        }
        for failure in failures
    ]


def _part_object_exists(store: CampaignObjectStore, object_key: str) -> bool:
    return store.get(object_key) is not None


def _label_and_write_parts(
    posts: pd.DataFrame,
    tasks: list[LabelTask],
    store: CampaignObjectStore,
    run_prefix: str,
    client: BedrockRuntimeClient,
    batch_size: int,
    max_concurrency: int,
    max_tokens: int,
    model_id: str,
) -> None:
    """Label pending batches and write parquet parts plus errors.

    Parameters
    ----------
    posts
        Validated input table.
    tasks
        Label tasks in record-id order.
    store
        Campaign object store for the run prefix.
    run_prefix
        S3 key prefix ending in ``/``.
    client
        Bedrock runtime client.
    batch_size
        Rows per immutable part.
    max_concurrency
        Thread pool size for Bedrock calls.
    max_tokens
        Converse ``maxTokens`` for each flip.
    model_id
        Bedrock model id.
    """
    feature_spec = flip_feature_spec()
    seen_ids = _load_seen_ids(store, run_prefix)
    for part_index, task_chunk in enumerate(batched(tasks, batch_size)):
        pending_tasks = [task for task in task_chunk if task.uri not in seen_ids]
        if not pending_tasks:
            continue
        part_object_key = part_key(run_prefix, part_index)
        if _part_object_exists(store, part_object_key):
            continue
        label_timestamp = get_current_timestamp()
        outcome = label_tasks_collecting_failures(
            client,
            model_id,
            feature_spec,
            pending_tasks,
            max_concurrency,
            label_timestamp,
            max_tokens=max_tokens,
        )
        flip_rows = _join_flip_rows(posts, outcome.rows)
        batch_failures = outcome.content_filter_failures + outcome.other_failures
        if batch_failures:
            store.append_jsonl(
                errors_key(run_prefix),
                _failure_records(batch_failures, part_index),
            )
            seen_ids.update(failure.source_record_id for failure in batch_failures)
        if flip_rows:
            _write_flip_part(store, part_object_key, flip_rows)
            seen_ids.update(flip_row.record_id for flip_row in flip_rows)


def _list_part_keys(store: CampaignObjectStore, run_prefix: str) -> list[str]:
    return [
        object_key
        for object_key in store.list_keys(_batches_prefix(run_prefix))
        if object_key.endswith(".parquet")
    ]


def _count_failed_ids(store: CampaignObjectStore, run_prefix: str) -> int:
    stored_errors = store.get(errors_key(run_prefix))
    if stored_errors is None:
        return 0
    failed_ids: set[str] = set()
    for line in stored_errors.body.decode("utf-8").splitlines():
        if not line.strip():
            continue
        error_record = json.loads(line)
        failed_ids.add(str(error_record["source_record_id"]))
    return len(failed_ids)


def _maybe_write_final_parquet(
    posts: pd.DataFrame,
    store: CampaignObjectStore,
    run_prefix: str,
    part_keys: list[str],
) -> bool:
    """Concatenate parts into ``flips.parquet`` when every input id is accounted for."""
    final_object_key = final_key(run_prefix)
    if store.get(final_object_key) is not None:
        return True
    all_input_ids = set(posts[RECORD_ID_COLUMN].astype(str))
    seen_ids = _load_seen_ids(store, run_prefix)
    if not all_input_ids <= seen_ids:
        return False
    part_frames: list[pd.DataFrame] = []
    for object_key in sorted(part_keys):
        stored_part = store.get(object_key)
        if stored_part is None:
            continue
        part_frames.append(parquet_rows(stored_part.body))
    if not part_frames:
        return False
    final_frame = pd.concat(part_frames, ignore_index=True)
    final_bytes = rows_to_parquet_bytes(
        final_frame.to_dict(orient="records"),
        FLIP_PARQUET_COLUMNS,
    )
    store.put_new(final_object_key, final_bytes)
    return True


def _build_flip_run_result(
    posts: pd.DataFrame,
    store: CampaignObjectStore,
    run_prefix: str,
) -> FlipRunResult:
    """Collect part and error counts and finalize ``flips.parquet`` when complete."""
    part_keys = _list_part_keys(store, run_prefix)
    row_count = 0
    for object_key in part_keys:
        stored_part = store.get(object_key)
        if stored_part is None:
            continue
        row_count += len(parquet_rows(stored_part.body))
    wrote_final = _maybe_write_final_parquet(posts, store, run_prefix, part_keys)
    final_object_key = final_key(run_prefix)
    if store.get(final_object_key) is not None:
        wrote_final = True
    return FlipRunResult(
        run_prefix=run_prefix,
        part_count=len(part_keys),
        row_count=row_count,
        failed_count=_count_failed_ids(store, run_prefix),
        final_key=final_object_key,
        wrote_final=wrote_final,
    )


def generate_flips(
    posts: pd.DataFrame,
    store: CampaignObjectStore,
    run_prefix: str,
    client: BedrockRuntimeClient,
    batch_size: int,
    max_concurrency: int,
    max_tokens: int,
    model_id: str,
) -> FlipRunResult:
    """Generate mirrored posts and write resumable S3 artifacts.

    Parameters
    ----------
    posts
        Input table with ``record_id``, ``text``, ``political_stance``, and
        ``llm_toxicity_tier``.
    store
        Campaign object store for the run prefix.
    run_prefix
        S3 key prefix ending in ``/``.
    client
        Bedrock runtime client.
    batch_size
        Rows per immutable part.
    max_concurrency
        Thread pool size for Bedrock calls.
    max_tokens
        Converse ``maxTokens`` for each flip.
    model_id
        Bedrock model id.

    Returns
    -------
    FlipRunResult
        Run summary with part counts and whether ``flips.parquet`` exists.
    """
    validated_posts = _validate_posts(posts)
    errors_key(run_prefix)
    tasks = _build_label_tasks(validated_posts)
    _label_and_write_parts(
        validated_posts,
        tasks,
        store,
        run_prefix,
        client,
        batch_size,
        max_concurrency,
        max_tokens,
        model_id,
    )
    return _build_flip_run_result(validated_posts, store, run_prefix)
