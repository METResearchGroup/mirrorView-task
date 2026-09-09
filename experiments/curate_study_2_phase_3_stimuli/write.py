"""Write the catalog CSV, upload it, and write RESULTS.md."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from data_platform.generate_features.s3_feature_campaign import (
    CampaignObjectStore,
    s3_uri,
)
from data_platform.utils.object_store import sha256_hex
from experiments.curate_study_2_phase_3_stimuli.sources import (
    CATALOG_COLUMNS,
    CSV_ENCODING,
    CSV_INDEX,
    CatalogRunResult,
    DATASET_FILENAME,
    EXPERIMENT_DIR,
    HIGH_TOXICITY,
    LEFT_STANCE,
    LOW_TOXICITY,
    MEDIUM_TOXICITY,
    OUTPUT_S3_BUCKET,
    OUTPUT_S3_KEY,
    RESULTS_FILENAME,
    RIGHT_STANCE,
    SAMPLE_TOXICITY_TYPE_COLUMN,
    SAMPLED_STANCE_COLUMN,
    STANCE_VALUES,
    TOXICITY_LABELS,
    TOXICITY_TIERS,
)
from lib.constants import REPO_ROOT

JSON_INDENT = 2
TOTAL_LABEL = "total"
RUN_COMMAND = """export AWS_ACCESS_KEY_ID="$LAB_AWS_ACCESS_KEY_ID"
export AWS_SECRET_ACCESS_KEY="$LAB_AWS_ACCESS_KEY_SECRET"

PYTHONPATH=. uv run python experiments/curate_study_2_phase_3_stimuli/run.py"""


def write_catalog(
    catalog: pd.DataFrame,
    available: dict[str, dict[str, int]],
    experiment_dir: Path | None = None,
    store: CampaignObjectStore | None = None,
) -> CatalogRunResult:
    """Write local CSV, upload with put_new, and write RESULTS.md."""
    resolved_dir = experiment_dir if experiment_dir is not None else EXPERIMENT_DIR
    resolved_store = store if store is not None else _default_store()
    local_path, body = _write_local_csv(catalog, resolved_dir)
    digest = _upload_csv(body, resolved_store)
    result = _success_result(catalog, available, local_path, digest)
    write_results_md(result, resolved_dir)
    return result


def write_pause_results(
    available: dict[str, dict[str, int]],
    experiment_dir: Path | None = None,
) -> CatalogRunResult:
    """Write RESULTS.md for a shortfall pause and do not upload CSV."""
    resolved_dir = experiment_dir if experiment_dir is not None else EXPERIMENT_DIR
    result = _empty_catalog_result(available)
    write_results_md(result, resolved_dir)
    return result


def write_results_md(result: CatalogRunResult, experiment_dir: Path) -> Path:
    """Write RESULTS.md with available counts and catalog status."""
    path = experiment_dir / RESULTS_FILENAME
    path.write_text(_results_markdown(result))
    return path


def print_run_summary(result: CatalogRunResult) -> None:
    """Print available counts and whether the catalog was written."""
    print("available_crosstab=")
    print(json.dumps(result.available, indent=JSON_INDENT))
    print(f"catalog_written={str(result.catalog_written).lower()}")
    if not result.catalog_written:
        return
    print(f"catalog_rows={result.catalog_rows}")
    print(f"left={result.left}")
    print(f"right={result.right}")
    print(f"low={result.low}")
    print(f"medium={result.medium}")
    print(f"high={result.high}")
    print(f"s3_uri={result.s3_uri}")
    print(f"csv_sha256={result.csv_sha256}")


def _write_local_csv(catalog: pd.DataFrame, experiment_dir: Path) -> tuple[Path, bytes]:
    ordered = catalog.loc[:, list(CATALOG_COLUMNS)]
    body = ordered.to_csv(index=CSV_INDEX).encode(CSV_ENCODING)
    path = experiment_dir / DATASET_FILENAME
    path.write_bytes(body)
    return path, body


def _upload_csv(body: bytes, store: CampaignObjectStore) -> str:
    store.put_new(OUTPUT_S3_KEY, body)
    return sha256_hex(body)


def _success_result(
    catalog: pd.DataFrame,
    available: dict[str, dict[str, int]],
    local_path: Path,
    digest: str,
) -> CatalogRunResult:
    return CatalogRunResult(
        available=available,
        catalog_written=True,
        catalog_rows=len(catalog),
        left=_stance_count(catalog, LEFT_STANCE),
        right=_stance_count(catalog, RIGHT_STANCE),
        low=_tier_count(catalog, LOW_TOXICITY),
        medium=_tier_count(catalog, MEDIUM_TOXICITY),
        high=_tier_count(catalog, HIGH_TOXICITY),
        local_path=str(local_path.relative_to(REPO_ROOT)),
        s3_uri=s3_uri(OUTPUT_S3_BUCKET, OUTPUT_S3_KEY),
        csv_sha256=digest,
    )


def _empty_catalog_result(available: dict[str, dict[str, int]]) -> CatalogRunResult:
    return CatalogRunResult(
        available=available,
        catalog_written=False,
        catalog_rows=0,
        left=0,
        right=0,
        low=0,
        medium=0,
        high=0,
        local_path="",
        s3_uri="",
        csv_sha256="",
    )


def _stance_count(catalog: pd.DataFrame, stance: str) -> int:
    return int((catalog[SAMPLED_STANCE_COLUMN] == stance).sum())


def _tier_count(catalog: pd.DataFrame, tier: str) -> int:
    return int((catalog[SAMPLE_TOXICITY_TYPE_COLUMN] == TOXICITY_LABELS[tier]).sum())


def _results_markdown(result: CatalogRunResult) -> str:
    return "\n".join(
        [
            "# Curate study 2 phase 3 stimuli, results",
            "",
            "## Command",
            "",
            "```bash",
            RUN_COMMAND,
            "```",
            "",
            "## Available posts with a flip",
            "",
            _stance_table_markdown(result.available),
            "",
            _catalog_status_sentence(result),
            "",
        ]
    )


def _catalog_status_sentence(result: CatalogRunResult) -> str:
    if not result.catalog_written:
        return "The catalog was not written, because at least one cell is short of its target."
    return (
        f"Catalog `{result.local_path}` SHA-256 `{result.csv_sha256}` has "
        f"{result.catalog_rows} rows. S3 object `{result.s3_uri}`."
    )


def _stance_table_markdown(counts: dict[str, dict[str, int]]) -> str:
    lines = [
        "| political_stance | low | medium | high | total |",
        "| ---------------- | --: | -----: | ---: | ----: |",
    ]
    grand = {tier: 0 for tier in TOXICITY_TIERS}
    for stance in STANCE_VALUES:
        cells = [int(counts.get(stance, {}).get(tier, 0)) for tier in TOXICITY_TIERS]
        for tier, value in zip(TOXICITY_TIERS, cells, strict=True):
            grand[tier] += value
        lines.append(_labeled_row(stance, cells))
    lines.append(_labeled_row(TOTAL_LABEL, [grand[tier] for tier in TOXICITY_TIERS]))
    return "\n".join(lines)


def _labeled_row(label: str, cells: list[int]) -> str:
    return f"| {label} | {cells[0]} | {cells[1]} | {cells[2]} | {sum(cells)} |"


def _default_store() -> CampaignObjectStore:
    return CampaignObjectStore(OUTPUT_S3_BUCKET)
