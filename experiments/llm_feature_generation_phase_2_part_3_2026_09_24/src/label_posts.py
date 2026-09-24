"""Label all posts via smoke (direct LLM) or production (OpenAI Batch).

Run from the repo root::

    PYTHONPATH=. uv run python -m experiments.llm_feature_generation_phase_2_part_3_2026_09_24.src.label_posts \\
      --codebook outputs/shared/codebook/approved_<ts>/codebook.json \\
      --text-surfaces original mirror --smoke --limit 20 --seed 42
"""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

from experiments.llm_feature_generation_phase_2_part_3_2026_09_24.src import (
    batch_client,
    constants,
    llm_client,
    paths,
)
from experiments.llm_feature_generation_phase_2_part_3_2026_09_24.src.prompts import (
    LABEL_OUTPUT_TOKENS_PER_REQUEST_ESTIMATE,
    build_labeling_prompt,
    estimate_labeling_prompt_tokens,
)
from experiments.llm_feature_generation_phase_2_part_3_2026_09_24.src.schemas import PostLabelResult

TEXT_SURFACE_ORIGINAL = "original"
TEXT_SURFACE_MIRROR = "mirror"
DEFAULT_TEXT_SURFACES = (TEXT_SURFACE_ORIGINAL, TEXT_SURFACE_MIRROR)
COHORT_ARM = "paired"
LABELS_FILENAME = "labels.jsonl"
LABELED_IDS_FILENAME = "labeled_ids.json"
BATCH_JOBS_FILENAME = "batch_jobs.json"
METADATA_FILENAME = "metadata.json"
BATCH_INPUTS_DIRNAME = "batch_inputs"
STAGE_LABEL = "label"
STAGE_LABEL_SMOKE = "label_smoke"


class ApprovalRequiredError(RuntimeError):
    """Raised when the codebook lacks an approved gate file."""


def require_approved_codebook(codebook_path: Path) -> Path:
    """Verify ``approval.json`` exists beside the approved codebook."""
    if not codebook_path.is_file():
        raise FileNotFoundError(codebook_path)
    approval_path = codebook_path.parent / constants.APPROVAL_JSON_FILENAME
    if not approval_path.is_file():
        raise ApprovalRequiredError(f"missing approval marker: {approval_path}")
    return approval_path


def load_codebook(codebook_path: Path) -> tuple[list[dict[str, Any]], str]:
    """Load codebook features and version string."""
    payload = json.loads(codebook_path.read_text(encoding="utf-8"))
    features = list(payload["features"])
    version = str(payload.get("version", codebook_path.parent.name))
    return features, version


def load_union_cohort() -> pd.DataFrame:
    """Load the union cohort parquet (all participant filter)."""
    cohort_dir = paths.latest_cohort_run_dir(COHORT_ARM, constants.PARTICIPANT_FILTER_ALL)
    return pd.read_parquet(cohort_dir / constants.COHORT_FILENAME)


def post_text_for_surface(row: pd.Series, text_surface: str) -> str:
    """Return post text for one labeling surface."""
    column = f"{text_surface}_text" if text_surface != TEXT_SURFACE_ORIGINAL else "original_text"
    if text_surface == TEXT_SURFACE_MIRROR:
        column = "mirror_text"
    return str(row[column])


def cohort_posts_frame(cohort: pd.DataFrame) -> list[dict[str, str]]:
    """Convert cohort rows to dicts for Batch JSONL building."""
    records: list[dict[str, str]] = []
    for _, row in cohort.iterrows():
        records.append(
            {
                "post_id": str(row["post_id"]),
                "original_text": str(row["original_text"]),
                "mirror_text": str(row["mirror_text"]),
                "split": str(row["split"]),
                "modal_decision": str(row["modal_decision"]),
            }
        )
    return records


def read_labeled_pairs(labels_path: Path) -> set[tuple[str, str]]:
    """Return labeled ``(post_id, text_surface)`` pairs from a shard file."""
    if not labels_path.is_file():
        return set()
    pairs: set[tuple[str, str]] = set()
    for line in labels_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        record = json.loads(line)
        pairs.add((record["post_id"], record["text_surface"]))
    return pairs


def write_labeled_ids(run_dir: Path, pairs: set[tuple[str, str]]) -> None:
    """Persist resume index ``labeled_ids.json``."""
    labeled = [{"post_id": pid, "text_surface": surface} for pid, surface in sorted(pairs)]
    path = run_dir / LABELED_IDS_FILENAME
    path.write_text(json.dumps({"labeled": labeled}, indent=2) + "\n", encoding="utf-8")


def assemble_label_matrix(
    labels_path: Path,
    cohort: pd.DataFrame,
    feature_ids: list[str],
    output_path: Path,
) -> pd.DataFrame:
    """Assemble wide parquet with one column per codebook feature."""
    rows = _load_label_rows(labels_path)
    frame = _labels_to_frame(rows, cohort, feature_ids)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_parquet(output_path, index=False)
    return frame


def run_smoke(
    codebook_path: Path,
    text_surfaces: tuple[str, ...],
    limit: int,
    seed: int,
) -> dict[str, Any]:
    """Label ``limit`` posts via direct ``llm_client`` calls."""
    approval = require_approved_codebook(codebook_path)
    features, version = load_codebook(codebook_path)
    cohort = load_union_cohort().sample(n=limit, random_state=seed)
    run_dir = paths.shared_label_dir() / f"smoke_{paths.make_run_timestamp()}"
    run_dir.mkdir(parents=True, exist_ok=True)
    call_count = _smoke_label_cohort(cohort, features, text_surfaces, run_dir)
    projection = _project_full_batch_cost(features, cohort_posts_frame(load_union_cohort()))
    smoke_stats = _summarize_smoke_run(run_dir, features)
    print(f"approval={approval}")
    print(
        f"smoke_posts={limit} surfaces={','.join(text_surfaces)} "
        f"direct_llm_calls={call_count}"
    )
    print(
        f"smoke_input_tokens_mean={smoke_stats['input_tokens_mean']:.0f} "
        f"per_feature_positive_rate={smoke_stats['positive_rates']}"
    )
    print(
        f"projected_batch_total_usd_no_cache={projection.projected_total_usd:.2f} "
        f"projected_batch_total_usd_cached={projection.cached_total_usd:.2f} "
        f"cap_usd={constants.SPEND_CAP_USD:.2f}"
    )
    return {"direct_llm_calls": call_count, "projection": projection, "smoke_stats": smoke_stats}


def run_production(
    codebook_path: Path,
    text_surfaces: tuple[str, ...],
    client: batch_client.OpenAIBatchClient | None = None,
    poll_timeout_seconds: float | None = None,
) -> dict[str, Any]:
    """Submit production labeling via Batch with resume and spend gate."""
    approval = require_approved_codebook(codebook_path)
    features, version = load_codebook(codebook_path)
    feature_ids = [feature["feature_id"] for feature in features]
    run_dir = _resolve_production_run_dir()
    labels_path = run_dir / LABELS_FILENAME
    labeled_pairs = read_labeled_pairs(labels_path)
    skip_ids = {batch_client.make_custom_id(pid, surf) for pid, surf in labeled_pairs}
    posts = cohort_posts_frame(load_union_cohort())
    batch_dir = run_dir / BATCH_INPUTS_DIRNAME
    jsonl_paths = batch_client.build_batch_jsonl(
        posts, features, text_surfaces, batch_dir, skip_custom_ids=skip_ids
    )
    estimate = batch_client.estimate_batch_cost(jsonl_paths, len(feature_ids))
    if estimate.projected_total_usd >= constants.SPEND_CAP_USD:
        raise SystemExit(
            f"projected spend {estimate.projected_total_usd:.2f} exceeds cap {constants.SPEND_CAP_USD:.2f}"
        )
    openai_client = client or batch_client.get_openai_client()
    batch_jobs: list[dict[str, Any]] = []
    if jsonl_paths:
        batch_jobs = _submit_all_batches(openai_client, jsonl_paths, run_dir)
    print(f"approval={approval}")
    print(f"batch_requests={estimate.n_requests} batch_jobs={len(batch_jobs)}")
    print(f"resumed_skipped={len(labeled_pairs)}")
    completed = _poll_and_persist_batches(
        openai_client,
        batch_jobs,
        labels_path,
        labeled_pairs,
        run_dir,
        poll_timeout_seconds,
    )
    matrix_path = paths.EXPERIMENT_ROOT / "outputs/shared/label_matrix.parquet"
    if completed:
        assemble_label_matrix(labels_path, load_union_cohort(), feature_ids, matrix_path)
        print(f"Wrote {matrix_path} rows={len(load_union_cohort()) * len(text_surfaces)}")
    print(f"Wrote {labels_path}")
    return {"batch_jobs": batch_jobs, "estimate": estimate, "completed": completed}


def main(argv: list[str] | None = None) -> None:
    """CLI entry for smoke, production, and matrix assembly."""
    args = _parse_args(argv)
    surfaces = tuple(args.text_surfaces)
    codebook_path = Path(args.codebook)
    if args.smoke:
        run_smoke(codebook_path, surfaces, args.limit, args.seed)
        return
    if args.production:
        run_production(codebook_path, surfaces, poll_timeout_seconds=args.poll_timeout_seconds)
        return
    if args.assemble_matrix:
        features, _ = load_codebook(codebook_path)
        feature_ids = [feature["feature_id"] for feature in features]
        run_dir = _latest_label_run_dir()
        labels_path = run_dir / LABELS_FILENAME
        matrix_path = paths.EXPERIMENT_ROOT / "outputs/shared/label_matrix.parquet"
        frame = assemble_label_matrix(labels_path, load_union_cohort(), feature_ids, matrix_path)
        print(f"Wrote {matrix_path} rows={len(frame)} features={len(feature_ids)}")
        return
    raise SystemExit("Specify --smoke, --production, or --assemble-matrix")


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Label posts with the approved codebook.")
    parser.add_argument("--codebook", required=True)
    parser.add_argument("--text-surfaces", nargs="+", default=list(DEFAULT_TEXT_SURFACES))
    parser.add_argument("--smoke", action="store_true")
    parser.add_argument("--production", action="store_true")
    parser.add_argument("--assemble-matrix", action="store_true")
    parser.add_argument("--limit", type=int, default=20)
    parser.add_argument("--seed", type=int, default=constants.DEFAULT_SEED)
    parser.add_argument("--poll-timeout-seconds", type=float, default=1200.0)
    return parser.parse_args(argv)


def _smoke_label_cohort(
    cohort: pd.DataFrame,
    features: list[dict[str, Any]],
    text_surfaces: tuple[str, ...],
    run_dir: Path,
) -> int:
    calls = 0
    output_dir = run_dir / "smoke_calls"
    metadata = {"model": constants.LLM_MODEL_ID, "reasoning_effort": constants.LLM_REASONING_EFFORT}
    response_model = batch_client.post_label_model_for_codebook(features)
    for _, row in cohort.iterrows():
        for surface in text_surfaces:
            text = post_text_for_surface(row, surface)
            messages = build_labeling_prompt(features, text, surface)
            llm_client.complete_structured(
                messages,
                response_model,
                stage=STAGE_LABEL_SMOKE,
                arm=None,
                call_index=calls,
                output_dir=output_dir,
                run_metadata=metadata,
            )
            calls += 1
    return calls


def _project_full_batch_cost(
    features: list[dict[str, Any]],
    posts: list[dict[str, str]],
) -> batch_client.BatchCostEstimate:
    import tempfile

    sample_posts = posts[: min(len(posts), 200)]
    with tempfile.TemporaryDirectory() as tmp:
        paths_list = batch_client.build_batch_jsonl(
            sample_posts, features, DEFAULT_TEXT_SURFACES, Path(tmp)
        )
        estimate = batch_client.estimate_batch_cost(paths_list, len(features))
        total_requests = len(posts) * len(DEFAULT_TEXT_SURFACES)
        scale = total_requests / max(estimate.n_requests, 1)
        estimate = batch_client.BatchCostEstimate(
            n_requests=total_requests,
            input_tokens=int(estimate.input_tokens * scale),
            output_tokens=int(estimate.output_tokens * scale),
            projected_batch_usd=estimate.projected_batch_usd * scale,
            cumulative_usd=estimate.cumulative_usd,
            projected_total_usd=estimate.cumulative_usd + estimate.projected_batch_usd * scale,
        )
    avg_user_chars = sum(len(post["original_text"]) + len(post["mirror_text"]) for post in posts) / (
        2 * max(len(posts), 1)
    )
    prefix_tokens, user_tokens = estimate_labeling_prompt_tokens(features, "x" * int(avg_user_chars))
    cached_batch = batch_client.compute_cached_batch_cost_usd(
        estimate.n_requests,
        prefix_tokens,
        user_tokens,
        LABEL_OUTPUT_TOKENS_PER_REQUEST_ESTIMATE,
    )
    cumulative = llm_client.read_cumulative_cost_usd()
    return batch_client.BatchCostEstimate(
        n_requests=estimate.n_requests,
        input_tokens=estimate.input_tokens,
        output_tokens=estimate.output_tokens,
        projected_batch_usd=estimate.projected_batch_usd,
        cumulative_usd=estimate.cumulative_usd,
        projected_total_usd=estimate.projected_total_usd,
        cached_total_usd=cumulative + cached_batch,
    )


def _summarize_smoke_run(run_dir: Path, features: list[dict[str, Any]]) -> dict[str, Any]:
    calls_dir = run_dir / "smoke_calls"
    usage_totals: list[int] = []
    positive_counts = {str(feature["feature_id"]): 0 for feature in features}
    n_labels = 0
    for artifact in sorted(calls_dir.glob("*.json")):
        payload = json.loads(artifact.read_text(encoding="utf-8"))
        usage_totals.append(int(payload.get("usage", {}).get("input_tokens", 0)))
        labels = payload.get("response", {}).get("parsed", {}).get("labels", {})
        if not labels:
            continue
        n_labels += 1
        for feature_id, present in labels.items():
            if present:
                positive_counts[str(feature_id)] = positive_counts.get(str(feature_id), 0) + 1
    rates = {
        feature_id: (positive_counts[feature_id] / n_labels if n_labels else 0.0)
        for feature_id in sorted(positive_counts)
    }
    mean_input = sum(usage_totals) / len(usage_totals) if usage_totals else 0.0
    return {"input_tokens_mean": mean_input, "positive_rates": rates, "n_label_rows": n_labels}


def _resolve_production_run_dir() -> Path:
    parent = paths.shared_label_dir()
    parent.mkdir(parents=True, exist_ok=True)
    run_dir_pattern = re.compile(r"^\d{4}-\d{2}-\d{2}T")
    existing = sorted(
        child
        for child in parent.iterdir()
        if child.is_dir() and run_dir_pattern.match(child.name)
    )
    if existing:
        return existing[-1]
    run_dir = parent / paths.make_run_timestamp()
    run_dir.mkdir(parents=True, exist_ok=True)
    return run_dir


def _latest_label_run_dir() -> Path:
    parent = paths.shared_label_dir()
    runs = sorted(child for child in parent.iterdir() if child.is_dir())
    if not runs:
        raise FileNotFoundError(f"No label runs under {parent}")
    return runs[-1]


def _submit_all_batches(
    client: batch_client.OpenAIBatchClient,
    jsonl_paths: list[Path],
    run_dir: Path,
) -> list[dict[str, Any]]:
    jobs: list[dict[str, Any]] = []
    for path in jsonl_paths:
        batch_id = batch_client.submit_batch(client, path)
        jobs.append({"batch_id": batch_id, "input_path": str(path), "status": "submitted"})
    jobs_path = run_dir / BATCH_JOBS_FILENAME
    jobs_path.write_text(json.dumps(jobs, indent=2) + "\n", encoding="utf-8")
    (run_dir / "batches.json").write_text(json.dumps(jobs, indent=2) + "\n", encoding="utf-8")
    return jobs


def _poll_and_persist_batches(
    client: batch_client.OpenAIBatchClient,
    batch_jobs: list[dict[str, Any]],
    labels_path: Path,
    labeled_pairs: set[tuple[str, str]],
    run_dir: Path,
    poll_timeout_seconds: float | None,
) -> bool:
    all_complete = True
    for job in batch_jobs:
        batch = batch_client.poll_batch(client, job["batch_id"], timeout_seconds=poll_timeout_seconds)
        job["status"] = batch.status
        if batch.status != "completed":
            all_complete = False
            continue
        output_lines, _ = batch_client.download_results(client, batch)
        rows = batch_client.parse_batch_output(output_lines)
        batch_client.write_label_shard_rows(labels_path, rows)
        for row in rows:
            labeled_pairs.add((row.post_id, row.text_surface))
        usage = batch_client.collect_usage_from_output_lines(output_lines)
        batch_client.append_batch_cost_log(stage=batch_client.STAGE_LABEL_BATCH, **usage)
    write_labeled_ids(run_dir, labeled_pairs)
    (run_dir / BATCH_JOBS_FILENAME).write_text(json.dumps(batch_jobs, indent=2) + "\n", encoding="utf-8")
    return all_complete


def _load_label_rows(labels_path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line in labels_path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def _labels_to_frame(
    rows: list[dict[str, Any]],
    cohort: pd.DataFrame,
    feature_ids: list[str],
) -> pd.DataFrame:
    cohort_index = cohort.set_index("post_id")
    records: list[dict[str, Any]] = []
    for row in rows:
        post_id = row["post_id"]
        meta = cohort_index.loc[post_id]
        record: dict[str, Any] = {
            "post_id": post_id,
            "text_surface": row["text_surface"],
            "split": str(meta["split"]),
            "modal_decision": str(meta["modal_decision"]),
        }
        labels = row["labels"]
        for feature_id in feature_ids:
            record[feature_id] = int(bool(labels.get(feature_id, False)))
        records.append(record)
    return pd.DataFrame(records)


if __name__ == "__main__":
    main()
