"""Step 2 entrypoint: mine candidate features via concurrent chat completions.

Run from the repo root::

    PYTHONPATH=. uv run python experiments/study_2_llm_based_feature_extraction_2026_09_29/src/step2_mine_candidate_features/run.py --smoke
    PYTHONPATH=. uv run python experiments/study_2_llm_based_feature_extraction_2026_09_29/src/step2_mine_candidate_features/run.py --full

Verification (given / when / then):

given cohort.parquet and batches.jsonl from step 1
when main runs with --smoke
then the first five batches are labeled, smoke_candidate_features.jsonl and estimates.json upload,
and a four-row estimate table prints to stdout

when main runs with --full without estimates.json
then FileNotFoundError is raised

when main runs with --full after smoke
then 320 rows are mined, candidate_features.jsonl uploads,
and stdout prints mined_batches=320 candidate_features=N
"""

from __future__ import annotations

import argparse
import json
import time

import pandas as pd

from experiments.study_2_llm_based_feature_extraction_2026_09_29.shared.constants import (
    BATCHES_KEY,
    CANDIDATE_FEATURES_KEY,
    COHORT_KEY,
    EXPECTED_BATCHES,
    LLM_CONCURRENCY,
    LLM_USD_PER_MILLION_INPUT,
    LLM_USD_PER_MILLION_OUTPUT,
    MINING_ESTIMATES_KEY,
    MINING_SMOKE_KEY,
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
from experiments.study_2_llm_based_feature_extraction_2026_09_29.src.step2_mine_candidate_features.prompt import (
    SYSTEM_PROMPT,
    build_mining_tasks,
)
from experiments.study_2_llm_based_feature_extraction_2026_09_29.src.step2_mine_candidate_features.schemas import (
    CandidateFeatureRow,
    CandidateFeatures,
)


def _load_batches() -> list[dict]:
    path = download_artifact(BATCHES_KEY)
    batches = [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
    return batches


def _load_cohort() -> pd.DataFrame:
    path = download_artifact(COHORT_KEY)
    return pd.read_parquet(path)


def _write_jsonl_rows(relative_key: str, rows: list[dict]) -> None:
    path = local_path(relative_key)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def _count_feature_strings(rows: list[dict]) -> int:
    total = 0
    for row in rows:
        for side in ("features_from_kept_posts", "features_from_removed_posts"):
            categories = row[side]
            for category in categories.values():
                total += len(category)
    return total


def run_smoke() -> None:
    batches = _load_batches()
    cohort = _load_cohort()
    all_tasks = build_mining_tasks(batches, cohort)
    tasks = all_tasks[:SMOKE_QUERY_COUNT]
    concurrent_run = run_concurrent(
        tasks,
        CandidateFeatures,
        CandidateFeatureRow,
        SYSTEM_PROMPT,
        time.time,
    )
    _write_jsonl_rows(MINING_SMOKE_KEY, concurrent_run.rows)
    upload_artifact(MINING_SMOKE_KEY)
    input_tokens = [usage.input_tokens for usage in concurrent_run.usage]
    output_tokens = [usage.output_tokens for usage in concurrent_run.usage]
    smoke_wall_minutes = concurrent_run.wall_seconds / 60.0
    runtime_minutes = scaled_runtime_minutes(
        smoke_wall_minutes,
        len(tasks),
        EXPECTED_BATCHES,
        LLM_CONCURRENCY,
    )
    estimate_rows = build_estimates(
        input_tokens,
        output_tokens,
        runtime_minutes,
        EXPECTED_BATCHES,
        LLM_USD_PER_MILLION_INPUT,
        LLM_USD_PER_MILLION_OUTPUT,
    )
    write_estimates(estimate_rows, MINING_ESTIMATES_KEY)
    upload_artifact(MINING_ESTIMATES_KEY)
    print(render_estimates_markdown(estimate_rows))


def run_full() -> None:
    require_estimates(MINING_ESTIMATES_KEY)
    batches = _load_batches()
    cohort = _load_cohort()
    tasks = build_mining_tasks(batches, cohort)
    concurrent_run = run_concurrent(
        tasks,
        CandidateFeatures,
        CandidateFeatureRow,
        SYSTEM_PROMPT,
        time.time,
    )
    rows = concurrent_run.rows
    if len(rows) != EXPECTED_BATCHES:
        raise ValueError(f"expected {EXPECTED_BATCHES} mined rows, found {len(rows)}")
    _write_jsonl_rows(CANDIDATE_FEATURES_KEY, rows)
    upload_artifact(CANDIDATE_FEATURES_KEY)
    feature_count = _count_feature_strings(rows)
    print(f"mined_batches={len(rows)} candidate_features={feature_count}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Mine candidate features for Study 2.")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--smoke", action="store_true", help="Run five-batch smoke and estimates.")
    group.add_argument("--full", action="store_true", help="Run all mining batches.")
    args = parser.parse_args()
    if args.smoke:
        run_smoke()
    else:
        run_full()


if __name__ == "__main__":
    main()
