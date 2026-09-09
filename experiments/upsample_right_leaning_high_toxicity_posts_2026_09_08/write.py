"""Write the 300 row parquet, the unified 2,300 post parquet, and RESULTS.md."""

from __future__ import annotations

from pathlib import Path

from data_platform.generate_features.s3_feature_campaign import CampaignObjectStore
from experiments.upsample_right_leaning_high_toxicity_posts_2026_09_08.sources import (
    CandidateBuildResult,
    PromotionResult,
    UnifiedUpsampleRunResult,
)


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
    raise NotImplementedError


def print_run_summary(result: UnifiedUpsampleRunResult) -> None:
    """Print candidate, promotion, and unified counts."""
    raise NotImplementedError
