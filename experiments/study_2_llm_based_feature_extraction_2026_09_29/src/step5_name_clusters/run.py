"""Step 5 entrypoint: name clusters from the features closest to each center.

Run from the repo root::

    PYTHONPATH=. uv run python experiments/study_2_llm_based_feature_extraction_2026_09_29/src/step5_name_clusters/run.py --smoke
    PYTHONPATH=. uv run python experiments/study_2_llm_based_feature_extraction_2026_09_29/src/step5_name_clusters/run.py --full
    PYTHONPATH=. uv run python experiments/study_2_llm_based_feature_extraction_2026_09_29/src/step5_name_clusters/run.py --write-label-details
"""

from __future__ import annotations

import argparse
import json
import time

from experiments.compare_jev_human_uncertainty_2026_09_25.jev_labels import (
    use_lab_credentials,
)

use_lab_credentials()

import numpy as np
import pandas as pd

from experiments.study_2_llm_based_feature_extraction_2026_09_29.shared.constants import (
    ASSIGNMENTS_KEY,
    CLUSTER_NAMES_KEY,
    CLUSTER_NAMING_SAMPLE_SIZE,
    CLUSTER_SIZES_KEY,
    EMBEDDINGS_KEY,
    EXPECTED_BATCHES,
    EXPERIMENT_DIR,
    FEATURE_IDS_KEY,
    FEATURE_REVIEW_KEY,
    FEATURES_KEY,
    LLM_CONCURRENCY,
    LLM_USD_PER_MILLION_INPUT,
    LLM_USD_PER_MILLION_OUTPUT,
    NAMING_ESTIMATES_KEY,
    NAMING_SMOKE_KEY,
    SMOKE_QUERY_COUNT,
)
from experiments.study_2_llm_based_feature_extraction_2026_09_29.shared.estimates import (
    build_estimates,
    render_estimates_markdown,
    require_estimates,
    scaled_runtime_minutes,
    write_estimates,
)
from experiments.study_2_llm_based_feature_extraction_2026_09_29.shared.llm import run_concurrent
from experiments.study_2_llm_based_feature_extraction_2026_09_29.shared.storage import (
    download_artifact,
    local_path,
    upload_artifact,
)
from experiments.study_2_llm_based_feature_extraction_2026_09_29.src.step5_name_clusters.prompt import (
    SYSTEM_PROMPT,
    build_naming_tasks,
    sample_cluster_features,
)
from experiments.study_2_llm_based_feature_extraction_2026_09_29.src.step5_name_clusters.review import (
    build_feature_review,
    empty_cluster_keys,
    render_review_markdown,
)
from experiments.study_2_llm_based_feature_extraction_2026_09_29.src.step5_name_clusters.schemas import (
    ClusterName,
    ClusterNameRow,
)
from experiments.study_2_llm_based_feature_extraction_2026_09_29.src.step5_name_clusters.write_label_details import (
    build_label_to_detail,
    render_label_details_module,
    validate_label_to_detail,
)
from data_platform.generate_features.models import LabelTask

_LABEL_DETAILS_PATH = EXPERIMENT_DIR / "shared" / "label_to_detail.py"


def _load_inputs() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, np.ndarray, list[str]]:
    """Download step 3 and step 4 artifacts used to build naming prompts."""
    features = pd.read_parquet(download_artifact(FEATURES_KEY))
    sizes = pd.read_parquet(download_artifact(CLUSTER_SIZES_KEY))
    assignments = pd.read_parquet(download_artifact(ASSIGNMENTS_KEY))
    matrix = np.load(download_artifact(EMBEDDINGS_KEY))
    feature_ids = json.loads(download_artifact(FEATURE_IDS_KEY).read_text(encoding="utf-8"))
    return features, sizes, assignments, matrix, feature_ids


def _write_jsonl(relative_key: str, rows: list[dict]) -> None:
    """Write naming rows as JSON lines and upload them."""
    path = local_path(relative_key)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")
    upload_artifact(relative_key)


def _name_tasks(tasks: list[LabelTask]) -> list[dict]:
    """Name tasks, retrying once when a name or definition is empty."""
    first = run_concurrent(tasks, ClusterName, ClusterNameRow, SYSTEM_PROMPT, time.time)
    rows = list(first.rows)
    empty = empty_cluster_keys(rows)
    if not empty:
        return rows
    retry_tasks = [task for task in tasks if task.uri in set(empty)]
    second = run_concurrent(retry_tasks, ClusterName, ClusterNameRow, SYSTEM_PROMPT, time.time)
    by_id = {str(row["source_record_id"]): row for row in rows}
    for row in second.rows:
        by_id[str(row["source_record_id"])] = row
    ordered = [by_id[task.uri] for task in tasks]
    still_empty = empty_cluster_keys(ordered)
    if still_empty:
        raise ValueError(f"empty name or definition: {', '.join(still_empty)}")
    return ordered


def run_smoke() -> None:
    """Name the first five clusters and print the full-run estimate table."""
    features, sizes, assignments, matrix, feature_ids = _load_inputs()
    samples = sample_cluster_features(
        assignments,
        features,
        matrix,
        feature_ids,
        CLUSTER_NAMING_SAMPLE_SIZE,
    )
    tasks = build_naming_tasks(samples, sizes)
    smoke_tasks = tasks[:SMOKE_QUERY_COUNT]
    named = run_concurrent(
        smoke_tasks,
        ClusterName,
        ClusterNameRow,
        SYSTEM_PROMPT,
        time.time,
    )
    wall_seconds = named.wall_seconds
    _write_jsonl(NAMING_SMOKE_KEY, named.rows)
    runtime_minutes = scaled_runtime_minutes(
        wall_seconds / 60.0,
        len(smoke_tasks),
        len(tasks),
        LLM_CONCURRENCY,
    )
    estimate_rows = build_estimates(
        [usage.input_tokens for usage in named.usage],
        [usage.output_tokens for usage in named.usage],
        runtime_minutes,
        len(tasks),
        LLM_USD_PER_MILLION_INPUT,
        LLM_USD_PER_MILLION_OUTPUT,
    )
    write_estimates(estimate_rows, NAMING_ESTIMATES_KEY)
    upload_artifact(NAMING_ESTIMATES_KEY)
    print(render_estimates_markdown(estimate_rows))
    for row in named.rows:
        print(f"{row['source_record_id']}\t{row['name']}")


def run_full() -> None:
    """Name every cluster, retry empties once, and upload the review table."""
    require_estimates(NAMING_ESTIMATES_KEY)
    features, sizes, assignments, matrix, feature_ids = _load_inputs()
    samples = sample_cluster_features(
        assignments,
        features,
        matrix,
        feature_ids,
        CLUSTER_NAMING_SAMPLE_SIZE,
    )
    tasks = build_naming_tasks(samples, sizes)
    rows = _name_tasks(tasks)
    _write_jsonl(CLUSTER_NAMES_KEY, rows)
    review = build_feature_review(rows, sizes, EXPECTED_BATCHES)
    review_path = local_path(FEATURE_REVIEW_KEY)
    review_path.parent.mkdir(parents=True, exist_ok=True)
    review.to_csv(review_path, index=False)
    upload_artifact(FEATURE_REVIEW_KEY)
    print(render_review_markdown(review))


def write_label_details() -> None:
    """Write the draft feature module from the review table."""
    if _LABEL_DETAILS_PATH.exists():
        raise FileExistsError(f"{_LABEL_DETAILS_PATH} already exists")
    review = pd.read_csv(download_artifact(FEATURE_REVIEW_KEY))
    mapping = build_label_to_detail(review)
    validate_label_to_detail(mapping)
    _LABEL_DETAILS_PATH.write_text(render_label_details_module(mapping), encoding="utf-8")
    print(f"features={len(mapping)}")


def main() -> None:
    """Name clusters, or write the draft feature list from a finished review."""
    parser = argparse.ArgumentParser(description="Name Study 2 feature clusters.")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--smoke", action="store_true", help="Name five clusters and estimate the full run.")
    group.add_argument("--full", action="store_true", help="Name every cluster.")
    group.add_argument(
        "--write-label-details",
        action="store_true",
        help="Write shared/label_to_detail.py from the review table.",
    )
    args = parser.parse_args()
    if args.smoke:
        run_smoke()
    elif args.full:
        run_full()
    else:
        write_label_details()


if __name__ == "__main__":
    main()
