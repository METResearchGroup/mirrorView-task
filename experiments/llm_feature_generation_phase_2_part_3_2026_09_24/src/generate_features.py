"""CLI for discovery LLM feature generation (mixed and single-class).

Run from the repo root::

    PYTHONPATH=. uv run python -m experiments.llm_feature_generation_phase_2_part_3_2026_09_24.src.generate_features \\
      --arm original_only \\
      --batch-design mixed \\
      --smoke \\
      --seed 42
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from pydantic import BaseModel

from experiments.llm_feature_generation_phase_2_part_3_2026_09_24.src import constants, paths
from experiments.llm_feature_generation_phase_2_part_3_2026_09_24.src.batching import (
    form_mixed_batches,
    form_single_class_batches,
    load_discovery_cohort,
)
from experiments.llm_feature_generation_phase_2_part_3_2026_09_24.src.llm_client import (
    complete_structured,
    merge_discovery_row,
    write_run_metadata,
)
from experiments.llm_feature_generation_phase_2_part_3_2026_09_24.src.prompts import (
    build_feature_generation_messages,
)
from experiments.llm_feature_generation_phase_2_part_3_2026_09_24.src.schemas import (
    BatchFeatureGeneration,
    SingleClassBatchFeatureGeneration,
)

APPROVAL_PATH = paths.EXPERIMENT_ROOT / "outputs/shared/approval_step3_production.json"
SMOKE_BATCH_LIMIT = 1
make_run_timestamp = paths.make_run_timestamp


def build_mixed_discovery_row(
    batch: dict[str, Any],
    result: BatchFeatureGeneration,
) -> dict[str, Any]:
    """Map one mixed batch result to a discovery row payload."""
    return {
        "batch_id": batch["batch_id"],
        "arm": batch["arm"],
        "batch_design": batch["batch_design"],
        "message_ids": batch["message_ids"],
        "keep_feature_count": len(result.keep_features),
        "remove_feature_count": len(result.remove_features),
        "result": result.model_dump(),
    }


def build_single_class_discovery_row(
    batch: dict[str, Any],
    result: SingleClassBatchFeatureGeneration,
) -> dict[str, Any]:
    """Map one single-class batch result to a discovery row payload."""
    return {
        "batch_id": batch["batch_id"],
        "arm": batch["arm"],
        "batch_design": batch["batch_design"],
        "message_ids": batch["message_ids"],
        "label_class": batch["label_class"],
        "feature_count": len(result.features),
        "result": result.model_dump(),
    }


def main(argv: list[str] | None = None) -> None:
    """Parse CLI args and run smoke or production discovery generation."""
    args = _parse_args(argv)
    _validate_mode(args)
    if args.production and not APPROVAL_PATH.is_file():
        raise SystemExit("missing approval_step3_production.json")
    batches, response_model, row_builder = _prepare_batches(args)
    if args.smoke:
        batches = batches[:SMOKE_BATCH_LIMIT]
    output_dir = _run_batches(args, batches, response_model, row_builder)
    _print_summary(args, batches, output_dir)
    raise SystemExit(0)


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run discovery LLM feature generation.")
    parser.add_argument("--arm", choices=constants.TEXT_ARMS, required=True)
    parser.add_argument(
        "--batch-design",
        choices=(constants.BATCH_DESIGN_MIXED, constants.BATCH_DESIGN_SINGLE_CLASS),
        required=True,
    )
    parser.add_argument("--seed", type=int, default=constants.DEFAULT_SEED)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--smoke", action="store_true")
    mode.add_argument("--production", action="store_true")
    return parser.parse_args(argv)


def _validate_mode(args: argparse.Namespace) -> None:
    if args.smoke and args.batch_design != constants.BATCH_DESIGN_MIXED:
        raise SystemExit("smoke mode supports mixed batch design only")


def _prepare_batches(
    args: argparse.Namespace,
) -> tuple[list[dict[str, Any]], type[BaseModel], Any]:
    cohort = load_discovery_cohort(args.arm)
    if args.batch_design == constants.BATCH_DESIGN_MIXED:
        batches = form_mixed_batches(cohort)
        return batches, BatchFeatureGeneration, build_mixed_discovery_row
    batches = form_single_class_batches(cohort, seed=args.seed)
    return batches, SingleClassBatchFeatureGeneration, build_single_class_discovery_row


def _run_batches(
    args: argparse.Namespace,
    batches: list[dict[str, Any]],
    response_model: type[BaseModel],
    row_builder: Any,
) -> Path:
    output_dir = _resolve_output_dir(args)
    run_metadata = _build_run_metadata(args)
    for call_index, batch in enumerate(batches):
        _run_one_batch(
            args, batch, call_index, output_dir, run_metadata, response_model, row_builder
        )
    return output_dir


def _run_one_batch(
    args: argparse.Namespace,
    batch: dict[str, Any],
    call_index: int,
    output_dir: Path,
    run_metadata: dict[str, Any],
    response_model: type[BaseModel],
    row_builder: Any,
) -> None:
    if _batch_artifact_exists(output_dir, call_index):
        return
    print(f"batch_index={call_index} arm={args.arm}")
    batch["arm"] = args.arm
    batch["batch_design"] = args.batch_design
    messages = build_feature_generation_messages(batch, args.arm)
    try:
        result = complete_structured(
            messages,
            response_model,
            stage="discovery",
            arm=args.arm,
            call_index=call_index,
            output_dir=output_dir,
            run_metadata=run_metadata,
        )
    except Exception as exc:
        print(f"batch_index={call_index} error={exc}", file=sys.stderr)
        _write_batch_error(output_dir, call_index, exc)
        return
    artifact_paths = sorted(output_dir.glob(f"{call_index:05d}_*.json"))
    if artifact_paths:
        artifact_path = artifact_paths[-1]
        merge_discovery_row(artifact_path, row_builder(batch, result))
        write_run_metadata(output_dir, run_metadata, artifact_path)


def _resolve_output_dir(args: argparse.Namespace) -> Path:
    parent = paths.discovery_run_dir(args.arm)
    existing = _find_existing_run_dir(parent, args.arm, args.batch_design)
    if existing is not None:
        return existing
    return parent / paths.make_run_timestamp()


def _find_existing_run_dir(parent: Path, arm: str, batch_design: str) -> Path | None:
    if not parent.is_dir():
        return None
    for child in sorted(parent.iterdir(), key=lambda path: path.name, reverse=True):
        if not child.is_dir():
            continue
        metadata_path = child / "metadata.json"
        if not metadata_path.is_file():
            continue
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        run_meta = metadata.get("run_metadata", {})
        if run_meta.get("arm") == arm and run_meta.get("batch_design") == batch_design:
            return child
    return None


def _batch_artifact_exists(output_dir: Path, call_index: int) -> bool:
    return any(output_dir.glob(f"{call_index:05d}_*.json"))


def _write_batch_error(output_dir: Path, call_index: int, exc: BaseException) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    artifact_path = output_dir / f"{call_index:05d}_{make_run_timestamp()}.json"
    payload = {"error": True, "batch_index": call_index, "message": str(exc)}
    artifact_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def _build_run_metadata(args: argparse.Namespace) -> dict[str, Any]:
    return {
        "model": constants.LLM_MODEL_ID,
        "reasoning_effort": constants.LLM_REASONING_EFFORT,
        "arm": args.arm,
        "batch_design": args.batch_design,
        "seed": args.seed,
        "stage": "discovery",
        "max_keep_features_per_batch": constants.MAX_KEEP_FEATURES_PER_BATCH,
        "max_remove_features_per_batch": constants.MAX_REMOVE_FEATURES_PER_BATCH,
        "litellm_model": constants.LLM_LITELLM_MODEL_ID,
        "timestamp_format": constants.RUN_TIMESTAMP_FORMAT,
    }


def _print_summary(
    args: argparse.Namespace,
    batches: list[dict[str, Any]],
    output_dir: Path,
) -> None:
    print(
        f"arm={args.arm} batch_design={args.batch_design} batches={len(batches)} "
        f"model={constants.LLM_MODEL_ID} reasoning_effort={constants.LLM_REASONING_EFFORT}"
    )
    print(f"Wrote {output_dir.relative_to(paths.EXPERIMENT_ROOT)}/")
    print(f"metadata.run_metadata.reasoning_effort={constants.LLM_REASONING_EFFORT}")


if __name__ == "__main__":
    main(sys.argv[1:])
