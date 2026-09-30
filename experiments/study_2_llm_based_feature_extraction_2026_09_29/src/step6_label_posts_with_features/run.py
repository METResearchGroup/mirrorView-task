"""Step 6 entrypoint: label Study 2 pairs with Jev.

Run from the repo root::

    PYTHONPATH=. uv run --with typesafe-sdk==0.7.1 python experiments/study_2_llm_based_feature_extraction_2026_09_29/src/step6_label_posts_with_features/run.py --smoke
    PYTHONPATH=. uv run --with typesafe-sdk==0.7.1 python experiments/study_2_llm_based_feature_extraction_2026_09_29/src/step6_label_posts_with_features/run.py --full
"""

from __future__ import annotations

import argparse
import statistics
import time

from experiments.compare_jev_human_uncertainty_2026_09_25.jev_labels import (
    use_lab_credentials,
)

use_lab_credentials()

import pandas as pd

from experiments.study_2_llm_based_feature_extraction_2026_09_29.shared.constants import (
    EXPECTED_STIMULUS_PAIRS,
    JEV_DEADLETTER_KEY,
    JEV_MAX_REQUESTS_PER_MINUTE,
    JEV_MAX_WORKERS,
    JEV_PREDICTIONS_KEY,
    JEV_PROBABILITIES_KEY,
    JEV_USD_PER_MILLION_INPUT,
    JEV_USD_PER_MILLION_OUTPUT,
    LABEL_TO_DETAIL,
    LABELING_ESTIMATES_KEY,
    LABELING_SMOKE_KEY,
    MAX_FEATURES_PER_JEV_REQUEST,
    POST_FEATURE_LABELS_KEY,
    SMOKE_QUERY_COUNT,
)
from experiments.study_2_llm_based_feature_extraction_2026_09_29.shared.estimates import (
    build_estimates,
    render_estimates_markdown,
    require_estimates,
    write_estimates,
)
from experiments.study_2_llm_based_feature_extraction_2026_09_29.shared.jev import (
    RequestStartLimiter,
    build_jev_scorer,
)
from experiments.study_2_llm_based_feature_extraction_2026_09_29.shared.secrets import (
    get_jev_api_key,
)
from experiments.study_2_llm_based_feature_extraction_2026_09_29.shared.storage import (
    local_path,
    upload_artifact,
)
from experiments.study_2_llm_based_feature_extraction_2026_09_29.src.step5_name_clusters.write_label_details import (
    validate_label_to_detail,
)
from experiments.study_2_llm_based_feature_extraction_2026_09_29.src.step6_label_posts_with_features.label import (
    chunk_feature_keys,
    features_sha256,
    run_labeling,
)
from experiments.study_2_llm_based_feature_extraction_2026_09_29.src.step6_label_posts_with_features.prompt import (
    render_feature_instruction,
    render_pair_state,
)
from experiments.study_2_llm_based_feature_extraction_2026_09_29.src.step6_label_posts_with_features.threshold import (
    apply_threshold,
    build_label_table,
    probabilities_frame,
)
from shared.data.dataloader import load_dataset


def load_pairs() -> pd.DataFrame:
    """Load all 20,000 stimulus pairs sorted by post id.

    Returns
    -------
    pandas.DataFrame
        Columns ``post_id``, ``original_text``, and ``mirror_text``.
    """
    stimuli = load_dataset("STUDY_2_STIMULI")
    pairs = pd.DataFrame(
        {
            "post_id": stimuli["post_primary_key"].astype(str),
            "original_text": stimuli["original_text"].astype(str),
            "mirror_text": stimuli["mirrored_text"].astype(str),
        }
    )
    return pairs.sort_values("post_id").reset_index(drop=True)


def _print_request_shape(pair: pd.Series) -> None:
    """Print the Jev call shape for the first smoke pair, without the API key."""
    state = render_pair_state(str(pair["original_text"]), str(pair["mirror_text"]))
    first_key = sorted(LABEL_TO_DETAIL)[0]
    instruction = render_feature_instruction(LABEL_TO_DETAIL[first_key])
    n_questions = len(chunk_feature_keys(sorted(LABEL_TO_DETAIL), MAX_FEATURES_PER_JEV_REQUEST)[0])
    print("api_call=client.system_one(state=state, questions=questions, model='jev-1.13.0')")
    print(f"state_keys={list(state)} n_questions={n_questions} question_id_example={first_key}")
    print("--- pair state ---")
    print(state["pair"][:500])
    print("--- first question instruction ---")
    print(instruction)


def _estimate_runtime_minutes(latency_ms: list[float], total_requests: int) -> float:
    """Return the full-run runtime estimate in minutes."""
    median_seconds = statistics.median(latency_ms) / 1000.0
    from_latency = (median_seconds * total_requests / JEV_MAX_WORKERS) / 60.0
    from_cap = total_requests / JEV_MAX_REQUESTS_PER_MINUTE
    return max(from_latency, from_cap)


def run_smoke() -> None:
    """Label the first five pairs and print the full-run estimate."""
    validate_label_to_detail(LABEL_TO_DETAIL)
    pairs = load_pairs()
    smoke_pairs = pairs.iloc[:SMOKE_QUERY_COUNT]
    _print_request_shape(smoke_pairs.iloc[0])
    api_key = get_jev_api_key()
    limiter = RequestStartLimiter(JEV_MAX_REQUESTS_PER_MINUTE, time.monotonic, time.sleep)
    predictions_path = local_path(LABELING_SMOKE_KEY)
    deadletter_path = local_path(LABELING_SMOKE_KEY + ".deadletter.jsonl")
    if predictions_path.exists():
        predictions_path.unlink()
    results = run_labeling(
        smoke_pairs,
        lambda: build_jev_scorer(api_key),
        LABEL_TO_DETAIL,
        predictions_path,
        deadletter_path,
        limiter,
        time.sleep,
        JEV_MAX_WORKERS,
    )
    if len(results) != SMOKE_QUERY_COUNT:
        raise ValueError(f"expected {SMOKE_QUERY_COUNT} smoke labels, found {len(results)}")
    upload_artifact(LABELING_SMOKE_KEY)
    requests_per_pair = len(chunk_feature_keys(sorted(LABEL_TO_DETAIL), MAX_FEATURES_PER_JEV_REQUEST))
    total_requests = EXPECTED_STIMULUS_PAIRS * requests_per_pair
    runtime_minutes = _estimate_runtime_minutes(
        [result.latency_ms for result in results],
        total_requests,
    )
    rows = build_estimates(
        [result.input_tokens for result in results],
        [result.output_tokens for result in results],
        runtime_minutes,
        total_requests,
        JEV_USD_PER_MILLION_INPUT,
        JEV_USD_PER_MILLION_OUTPUT,
    )
    write_estimates(rows, LABELING_ESTIMATES_KEY)
    upload_artifact(LABELING_ESTIMATES_KEY)
    print(render_estimates_markdown(rows))
    print(f"smoke_pairs={len(results)} features={len(LABEL_TO_DETAIL)} requests_per_pair={requests_per_pair}")


def run_full() -> None:
    """Label all 20,000 pairs. Not used until the smoke test is approved."""
    require_estimates(LABELING_ESTIMATES_KEY)
    validate_label_to_detail(LABEL_TO_DETAIL)
    pairs = load_pairs()
    api_key = get_jev_api_key()
    limiter = RequestStartLimiter(JEV_MAX_REQUESTS_PER_MINUTE, time.monotonic, time.sleep)
    predictions_path = local_path(JEV_PREDICTIONS_KEY)
    deadletter_path = local_path(JEV_DEADLETTER_KEY)
    results = run_labeling(
        pairs,
        lambda: build_jev_scorer(api_key),
        LABEL_TO_DETAIL,
        predictions_path,
        deadletter_path,
        limiter,
        time.sleep,
        JEV_MAX_WORKERS,
    )
    upload_artifact(JEV_PREDICTIONS_KEY)
    if deadletter_path.exists() and deadletter_path.read_text(encoding="utf-8").strip():
        upload_artifact(JEV_DEADLETTER_KEY)
        raise ValueError("deadletter file is not empty")
    sha = features_sha256(LABEL_TO_DETAIL)
    labeled = probabilities_frame(predictions_path, sha, sorted(LABEL_TO_DETAIL))
    if len(labeled) < EXPECTED_STIMULUS_PAIRS:
        raise ValueError(f"expected {EXPECTED_STIMULUS_PAIRS} labeled pairs, found {len(labeled)}")
    from experiments.study_2_llm_based_feature_extraction_2026_09_29.shared.constants import (
        FEATURE_PRESENT_THRESHOLD,
    )

    thresholded = apply_threshold(labeled, FEATURE_PRESENT_THRESHOLD)
    table = build_label_table(thresholded, pairs)
    probabilities_path = local_path(JEV_PROBABILITIES_KEY)
    labels_path = local_path(POST_FEATURE_LABELS_KEY)
    labeled.to_parquet(probabilities_path, index=False)
    table.to_parquet(labels_path, index=False)
    upload_artifact(JEV_PROBABILITIES_KEY)
    upload_artifact(POST_FEATURE_LABELS_KEY)
    request_count = int(sum(result.n_requests for result in results))
    print(
        f"labeled_pairs={len(table)} features={len(LABEL_TO_DETAIL)} "
        f"requests={request_count} deadletters=0"
    )


def main() -> None:
    """Label a smoke sample or the full stimulus file."""
    parser = argparse.ArgumentParser(description="Label Study 2 pairs with Jev.")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--smoke", action="store_true")
    group.add_argument("--full", action="store_true")
    args = parser.parse_args()
    if args.smoke:
        run_smoke()
    else:
        run_full()


if __name__ == "__main__":
    main()
