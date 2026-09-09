"""Write the 300 row parquet, the unified 2,300 post parquet, and RESULTS.md."""

from __future__ import annotations

import io
import json
from pathlib import Path

import pandas as pd

from data_platform.generate_features.s3_feature_campaign import (
    CampaignObjectStore,
    s3_uri,
)
from data_platform.utils.object_store import sha256_hex
from experiments.upsample_right_leaning_high_toxicity_posts_2026_09_08.sources import (
    CandidateBuildResult,
    EXPERIMENT_DIR,
    HIGH_TOXICITY,
    JSON_INDENT,
    LEFT_STANCE,
    MEDIUM_TOXICITY,
    OUTPUT_S3_BUCKET,
    PROMOTED_FILENAME,
    PROMOTED_S3_KEY,
    PromotionResult,
    RESULTS_FILENAME,
    RIGHT_STANCE,
    STANCE_COLUMN,
    TOXICITY_COLUMN,
    UNIFIED_FILENAME,
    UNIFIED_S3_KEY,
    UnifiedUpsampleRunResult,
    promotion_ids_path,
)
from lib.constants import REPO_ROOT

RUN_COMMAND = """export AWS_ACCESS_KEY_ID="$LAB_AWS_ACCESS_KEY_ID"
export AWS_SECRET_ACCESS_KEY="$LAB_AWS_ACCESS_KEY_SECRET"

PYTHONPATH=. uv run python experiments/upsample_right_leaning_high_toxicity_posts_2026_09_08/run.py"""


def require_output_keys_absent(store: CampaignObjectStore) -> None:
    """Raise FileExistsError if the 300-row or unified S3 key already exists.

    Raises
    ------
    FileExistsError
        When either destination S3 key already exists.
    """
    _require_key_absent(store, PROMOTED_S3_KEY)
    _require_key_absent(store, UNIFIED_S3_KEY)


def write_unified_upsample(
    candidates: CandidateBuildResult,
    promotion: PromotionResult,
    experiment_dir: Path | None = None,
    store: CampaignObjectStore | None = None,
) -> UnifiedUpsampleRunResult:
    """Write local parquets, upload both with put_new, and write RESULTS.md.

    Parameters
    ----------
    candidates
        Candidate rows and drop counts.
    promotion
        Promoted rows and the unified table.
    experiment_dir
        Folder that receives local parquet, JSON, and RESULTS.md.
    store
        Object store used only with ``put_new``.

    Returns
    -------
    UnifiedUpsampleRunResult
        Counts, URIs, and SHA-256 values.

    Raises
    ------
    FileExistsError
        When either destination S3 key already exists.
    """
    resolved_dir = experiment_dir if experiment_dir is not None else EXPERIMENT_DIR
    resolved_store = store if store is not None else _default_store()
    require_output_keys_absent(resolved_store)
    promoted_path, promoted_body = _write_local_parquet(
        promotion.promoted, resolved_dir / PROMOTED_FILENAME
    )
    unified_path, unified_body = _write_local_parquet(
        promotion.unified, resolved_dir / UNIFIED_FILENAME
    )
    promoted_digest = _upload(PROMOTED_S3_KEY, promoted_body, resolved_store)
    unified_digest = _upload(UNIFIED_S3_KEY, unified_body, resolved_store)
    _write_promotion_ids(promotion.promotion_ids)
    result = _run_result(
        candidates, promotion, promoted_path, promoted_digest, unified_path, unified_digest
    )
    write_results_md(result, resolved_dir)
    return result


def write_results_md(result: UnifiedUpsampleRunResult, experiment_dir: Path) -> Path:
    """Write RESULTS.md with candidate, promotion, and unified counts."""
    path = experiment_dir / RESULTS_FILENAME
    path.write_text(_results_markdown(result))
    return path


def print_run_summary(result: UnifiedUpsampleRunResult) -> None:
    """Print candidate, promotion, and unified counts."""
    print(f"candidate_rows={result.candidate_rows}")
    print(f"leftover_right_medium_after_upsample={result.leftover_right_medium_after_upsample}")
    print(f"pr260_ids_dropped={result.pr260_ids_dropped}")
    print(f"promotions={result.promotions}")
    print(f"unified_rows={result.unified_rows}")
    print(f"unified_medium={result.unified_medium}")
    print(f"unified_high={result.unified_high}")
    print(f"promoted_s3_uri={result.promoted_s3_uri}")
    print(f"promoted_sha256={result.promoted_sha256}")
    print(f"unified_s3_uri={result.unified_s3_uri}")
    print(f"unified_sha256={result.unified_sha256}")


def _require_key_absent(store: CampaignObjectStore, key: str) -> None:
    if store.get(key) is not None:
        raise FileExistsError(f"Object already exists: {s3_uri(OUTPUT_S3_BUCKET, key)}")


def _write_local_parquet(frame: pd.DataFrame, path: Path) -> tuple[Path, bytes]:
    body = _parquet_bytes(frame)
    path.write_bytes(body)
    return path, body


def _upload(key: str, body: bytes, store: CampaignObjectStore) -> str:
    store.put_new(key, body)
    return sha256_hex(body)


def _write_promotion_ids(promotion_ids: list[str]) -> None:
    path = promotion_ids_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(promotion_ids, indent=JSON_INDENT) + "\n")


def _run_result(
    candidates: CandidateBuildResult,
    promotion: PromotionResult,
    promoted_path: Path,
    promoted_digest: str,
    unified_path: Path,
    unified_digest: str,
) -> UnifiedUpsampleRunResult:
    unified = promotion.unified
    return UnifiedUpsampleRunResult(
        candidate_rows=len(candidates.rows),
        leftover_right_medium_after_upsample=candidates.leftover_right_medium_after_upsample,
        pr260_ids_dropped=candidates.pr260_ids_dropped,
        promotions=len(promotion.promoted),
        unified_rows=len(unified),
        unified_medium=_count(unified, TOXICITY_COLUMN, MEDIUM_TOXICITY),
        unified_high=_count(unified, TOXICITY_COLUMN, HIGH_TOXICITY),
        unified_left=_count(unified, STANCE_COLUMN, LEFT_STANCE),
        unified_right=_count(unified, STANCE_COLUMN, RIGHT_STANCE),
        promoted_local_path=str(promoted_path.relative_to(REPO_ROOT)),
        promoted_s3_uri=s3_uri(OUTPUT_S3_BUCKET, PROMOTED_S3_KEY),
        promoted_sha256=promoted_digest,
        unified_local_path=str(unified_path.relative_to(REPO_ROOT)),
        unified_s3_uri=s3_uri(OUTPUT_S3_BUCKET, UNIFIED_S3_KEY),
        unified_sha256=unified_digest,
    )


def _count(frame: pd.DataFrame, column: str, value: str) -> int:
    return int((frame[column] == value).sum())


def _results_markdown(result: UnifiedUpsampleRunResult) -> str:
    return "\n".join(
        [
            "# Upsample right-leaning high toxicity posts, results",
            "",
            "## Command",
            "",
            "```bash",
            RUN_COMMAND,
            "```",
            "",
            "## Candidates",
            "",
            _counts_table_markdown(result),
            "",
            "## Parquet files",
            "",
            _parquet_table_markdown(result),
            "",
            "## Unified political stance by toxicity",
            "",
            (
                f"The unified table has {result.unified_left} left posts and "
                f"{result.unified_right} right posts. It has {result.unified_medium} "
                f"medium posts and {result.unified_high} high posts."
            ),
            "",
        ]
    )


def _counts_table_markdown(result: UnifiedUpsampleRunResult) -> str:
    return "\n".join(
        [
            "| Field | Count |",
            "| ----- | ----: |",
            f"| Candidate rows | {result.candidate_rows} |",
            f"| Leftover right medium after 2000 upsample | {result.leftover_right_medium_after_upsample} |",
            f"| Pull request 260 ids dropped | {result.pr260_ids_dropped} |",
            f"| Promotions | {result.promotions} |",
            f"| Unified rows | {result.unified_rows} |",
            f"| Unified medium | {result.unified_medium} |",
            f"| Unified high | {result.unified_high} |",
        ]
    )


def _parquet_table_markdown(result: UnifiedUpsampleRunResult) -> str:
    return "\n".join(
        [
            "| File | Path | SHA-256 |",
            "| ---- | ---- | ------- |",
            f"| Local 300 row parquet | `{result.promoted_local_path}` | `{result.promoted_sha256}` |",
            f"| S3 300 row parquet | `{result.promoted_s3_uri}` | `{result.promoted_sha256}` |",
            f"| Local unified parquet | `{result.unified_local_path}` | `{result.unified_sha256}` |",
            f"| S3 unified parquet | `{result.unified_s3_uri}` | `{result.unified_sha256}` |",
        ]
    )


def _parquet_bytes(frame: pd.DataFrame) -> bytes:
    buffer = io.BytesIO()
    frame.to_parquet(buffer, index=False)
    return buffer.getvalue()


def _default_store() -> CampaignObjectStore:
    return CampaignObjectStore(OUTPUT_S3_BUCKET)
