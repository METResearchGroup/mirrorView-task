"""Confirm the issue 329 prompt, Weave, and one Bedrock DSPy contract.

Run from the repo root::

    PYTHONPATH=. uv run python experiments/dspy_gepa_optimization_2026_09_30/src/step1_setup/main.py --contract-only
"""

from __future__ import annotations

import argparse
from importlib.metadata import version

import weave

from experiments.dspy_gepa_optimization_2026_09_30.shared.artifacts import (
    MANIFEST_KEY,
    upload_inputs,
)
from experiments.dspy_gepa_optimization_2026_09_30.shared.config import (
    BEDROCK_MODEL_ID,
    S3_BUCKET,
    SPLIT_NAMES,
    SPLIT_REMOVE_COUNTS,
    SPLIT_ROW_COUNTS,
    WANDB_PROJECT_PATH,
)
from experiments.dspy_gepa_optimization_2026_09_30.shared.data import (
    EXCLUDELIST_POST_IDS,
    build_splits,
    load_unanimous_labels,
)
from experiments.dspy_gepa_optimization_2026_09_30.shared.program import (
    build_reflection_model,
    build_seed_program,
    configure_task_model,
    reflection_text,
    seed_instruction,
    validate_remove_output,
)
from experiments.dspy_gepa_optimization_2026_09_30.shared.telemetry import (
    apply_lab_aws_credentials,
    call_url,
    initialize_weave,
    record_local_marker,
    trace_attributes,
)

CONTRACT_POST_1 = (
    "I'm a bleeding-heart liberal, and I think the issue of abortion is "
    "obviously about protecting women's rights!"
)
CONTRACT_POST_2 = (
    "I'm a staunch conservative, and abortion is fully about the sanctity "
    "of human life before birth!"
)
PAID_CALL_COUNT = 2


def main() -> None:
    """Run the contract check or the later dataset setup path."""
    args = _parse_args()
    if args.contract_only:
        run_contract()
        return
    run_setup()


def run_setup() -> None:
    """Validate the unanimous dataset and write the pilot splits to S3."""
    bundle = build_splits(load_unanimous_labels())
    hashes = upload_inputs(bundle)
    print("source_rows", bundle.source_count)
    print("excluded_examples", len(EXCLUDELIST_POST_IDS))
    print("eligible_rows", len(bundle.eligible))
    print("cohort_rows", len(bundle.cohort_ids))
    for name in SPLIT_NAMES:
        print(
            "split",
            name,
            "rows",
            SPLIT_ROW_COUNTS[name],
            "remove",
            SPLIT_REMOVE_COUNTS[name],
        )
    print("manifest_uri", f"s3://{S3_BUCKET}/{MANIFEST_KEY}")
    for key, digest in hashes.items():
        print("sha256", digest, key)


def run_contract() -> None:
    """Upload one local trace, one task prediction, and one reflection."""
    apply_lab_aws_credentials()
    client = initialize_weave()
    metadata = {
        "stage": "contract",
        "model_id": BEDROCK_MODEL_ID,
        "mode": "contract",
    }
    with trace_attributes(metadata):
        local_call = record_local_marker("contract")
        task_call, reflection_call = _paid_contract_calls()
    client.finish()
    _print_contract_summary(local_call, task_call, reflection_call)


def _paid_contract_calls() -> tuple[object, object]:
    with weave.attributes({"stage": "task", "model_id": BEDROCK_MODEL_ID}):
        task_call = _traced_task()
    with weave.attributes({"stage": "reflection", "model_id": BEDROCK_MODEL_ID}):
        reflection_call = _traced_reflection()
    return task_call, reflection_call


@weave.op
def _traced_task() -> dict[str, object]:
    configure_task_model()
    prediction = build_seed_program()(
        post_1_text=CONTRACT_POST_1,
        post_2_text=CONTRACT_POST_2,
    )
    validate_remove_output(bool(prediction.is_remove), float(prediction.p_remove))
    return {
        "is_remove": bool(prediction.is_remove),
        "p_remove": float(prediction.p_remove),
        "model_id": BEDROCK_MODEL_ID,
        "trace_url": _current_trace_url(),
    }


@weave.op
def _traced_reflection() -> dict[str, str]:
    revised = reflection_text(build_reflection_model(), seed_instruction())
    if not revised.strip():
        raise ValueError("reflection returned empty text")
    return {
        "model_id": BEDROCK_MODEL_ID,
        "reflection_characters": str(len(revised)),
        "trace_url": _current_trace_url(),
    }


def _current_trace_url() -> str:
    call = weave.get_current_call()
    if call is None:
        raise RuntimeError("Weave did not record the current call")
    return call_url(call)


def _print_contract_summary(
    local_call: dict[str, str],
    task_call: dict[str, object],
    reflection_call: dict[str, str],
) -> None:
    print("versions", version("dspy"), version("gepa"), version("weave"))
    print("model_id", BEDROCK_MODEL_ID)
    print("wandb_project", WANDB_PROJECT_PATH)
    print("paid_calls", PAID_CALL_COUNT)
    print("local_trace", local_call["trace_url"])
    print("task_trace", task_call["trace_url"])
    print("reflection_trace", reflection_call["trace_url"])
    print("task_result", {key: value for key, value in task_call.items() if key != "trace_url"})
    print("reflection_result", {key: value for key, value in reflection_call.items() if key != "trace_url"})


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Prepare the DSPy GEPA experiment.")
    parser.add_argument("--contract-only", action="store_true")
    return parser.parse_args()


if __name__ == "__main__":
    main()
