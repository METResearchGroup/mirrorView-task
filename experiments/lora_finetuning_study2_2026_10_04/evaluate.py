"""Launch or run Study 2 LoRA keep/remove evaluation on Hugging Face Jobs.

From the repo root, submit one eval job for an ablation (builds
``HF_EVAL_IMAGE``, waits for completion, downloads ``metrics.jsonl`` locally):

    HF_EVAL_IMAGE=docker.io/<namespace>/lora-finetuning-study2-2026-10-04-eval:latest \\
        PYTHONPATH=. uv run python experiments/lora_finetuning_study2_2026_10_04/evaluate.py \\
        --ablation unanimous

Inside the job (``--in-job``), downloads the adapter from S3, rewrites keys for
vLLM, scores ``STUDY_2_KEEP_REMOVE_LABELS`` once with thinking off, and writes
unanimous / split / all metrics from that single pass. Uploads ``preds.jsonl``
and ``metrics.jsonl``.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Sequence

from huggingface_hub import JobInfo, inspect_job
from huggingface_hub._jobs_api import JobStage
from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score

from lib.aws.s3 import DEFAULT_REGION_NAME, S3
from lib.load_env_vars import EnvVarsContainer
from shared.data.dataloader import load_dataset
from shared.data.registry import (
    STUDY_2_KEEP_REMOVE_LABELS,
    STUDY_2_KEEP_REMOVE_SPLIT_LABELS,
    STUDY_2_KEEP_REMOVE_UNANIMOUS_LABELS,
)
from shared.models.llm.infra.upload_to_hf_jobs import (
    HuggingFaceJobConfig,
    upload_to_hf_jobs,
)
from experiments.lora_finetuning_study2_2026_10_04.constants import (
    ADAPTER_S3_PREFIX,
    ARTIFACTS_BUCKET,
    LORA_RANK,
    LORA_TARGET_MODULES,
    MAX_LENGTH,
    MODEL_NAME,
    build_adapter_s3_uri,
    parse_s3_uri,
)
EXPERIMENT_DIR = Path(__file__).resolve().parent
REPO_ROOT = EXPERIMENT_DIR.parents[1]
DOCKERFILE_EVAL = EXPERIMENT_DIR / "Dockerfile.eval"
EVAL_COMMAND = (
    "python3",
    "experiments/lora_finetuning_study2_2026_10_04/evaluate.py",
)
RESULTS_S3_PREFIX = "experiments/lora_finetuning_study2_2026_10_04/results"
POSITIVE_CLASS = "remove"
MAX_NEW_TOKENS = 8
FULL_TABLE_N = 20_000
EVAL_FLAVOR = "l4x1"
EVAL_TIMEOUT = "8h"
VLLM_GPU_MEMORY_UTILIZATION = 0.90
VLLM_MAX_LORAS = 1
CHAT_TEMPLATE_KWARGS = {"enable_thinking": False}
FIVE_LABELER_COUNT = 5
ABLATION_CHOICES = ("unanimous", "split", "all")
FLAVOR_CHOICES = ("l4x1", "a100-large")

EVAL_DATASETS: tuple[str, ...] = (
    STUDY_2_KEEP_REMOVE_UNANIMOUS_LABELS,
    STUDY_2_KEEP_REMOVE_SPLIT_LABELS,
    STUDY_2_KEEP_REMOVE_LABELS,
)

_SPACE_IMAGE_PREFIXES = (
    "hf.co/spaces/",
    "huggingface.co/spaces/",
    "https://hf.co/spaces/",
    "https://huggingface.co/spaces/",
)

_REQUIRED_ROW_COLUMNS = {
    "post_id",
    "original_text",
    "mirror_text",
    "decision",
    "n_raters",
    "n_remove",
}

_LORA_IGNORE_MARKERS = (
    "will be ignored",
    "does not support it",
    "No LoRA weights found for module",
    "could not be wrapped by any LoRA layer",
)


def eval_groups_for_row(n_raters: object, n_remove: object) -> list[str]:
    """Return the metric tables one modal row belongs to.

    Every row is in the all-label table. Five-labeler rows with 0 or 5 remove
    votes are also unanimous. Five-labeler rows with 1 to 4 remove votes are
    also split. Other labeler counts stay in the all table only. This matches
    ``split_keep_remove_labels``.
    """
    groups = [STUDY_2_KEEP_REMOVE_LABELS]
    raters = int(n_raters)
    removes = int(n_remove)
    if raters != FIVE_LABELER_COUNT:
        return groups
    if removes in (0, FIVE_LABELER_COUNT):
        groups.append(STUDY_2_KEEP_REMOVE_UNANIMOUS_LABELS)
    elif 1 <= removes < FIVE_LABELER_COUNT:
        groups.append(STUDY_2_KEEP_REMOVE_SPLIT_LABELS)
    return groups


def parse_generation(raw_generation: str) -> str | None:
    """Return ``keep``, ``remove``, or ``None`` when the first token is invalid."""
    token = str(raw_generation).strip().split()
    if not token:
        return None
    first = token[0].strip().lower().strip(".,:;!?\"'`")
    if first in {"keep", "remove"}:
        return first
    return None


def decision_to_label(decision: str) -> int:
    """Map ``keep`` / ``remove`` to 0 / 1 (positive class = remove)."""
    normalized = str(decision).lower().strip()
    if normalized == "remove":
        return 1
    if normalized == "keep":
        return 0
    raise ValueError(f"Unexpected decision: {decision!r}")


def effective_pred_label(gold_label: int, predicted_decision: str | None) -> int:
    """Score invalid predictions as wrong (opposite of gold)."""
    if predicted_decision is None:
        return 1 - gold_label
    return decision_to_label(predicted_decision)


def compute_classification_metrics(
    gold_decisions: Sequence[str],
    predicted_decisions: Sequence[str | None],
) -> dict[str, float | int]:
    """Return accuracy, precision, recall, f1, n, and n_invalid."""
    if len(gold_decisions) != len(predicted_decisions):
        raise ValueError("gold and predicted sequences must have the same length")
    y_true = [decision_to_label(d) for d in gold_decisions]
    y_pred = [
        effective_pred_label(gold, pred)
        for gold, pred in zip(y_true, predicted_decisions, strict=True)
    ]
    n_invalid = sum(1 for pred in predicted_decisions if pred is None)
    return {
        "n": len(y_true),
        "n_invalid": n_invalid,
        "accuracy": float(accuracy_score(y_true, y_pred)),
        "precision": float(precision_score(y_true, y_pred, pos_label=1, zero_division=0)),
        "recall": float(recall_score(y_true, y_pred, pos_label=1, zero_division=0)),
        "f1": float(f1_score(y_true, y_pred, pos_label=1, zero_division=0)),
    }


def build_results_s3_uri(ablation: str, run_name: str, filename: str) -> str:
    """Return the S3 URI for one eval artifact."""
    key = f"{RESULTS_S3_PREFIX}/{ablation}/{run_name}/{filename}"
    return f"s3://{ARTIFACTS_BUCKET}/{key}"


def build_results_s3_key(ablation: str, run_name: str, filename: str) -> str:
    """Return the object key for one eval artifact."""
    return f"{RESULTS_S3_PREFIX}/{ablation}/{run_name}/{filename}"


def local_metrics_path(ablation: str, run_name: str) -> Path:
    """Return the local path where the launcher saves ``metrics.jsonl``."""
    return EXPERIMENT_DIR / "results" / ablation / run_name / "metrics.jsonl"


def rewrite_adapter_key_for_vllm(saved_key: str) -> str:
    """Normalize one PEFT LoRA key for vLLM offline loading.

    vLLM's ``parse_fine_tuned_lora_name`` accepts ``lora_A.weight`` /
    ``lora_B.weight``. Nested PEFT keys (``lora_A.default.weight``) are
    flattened. The ``language_model`` segment stays: Qwen3.5's multimodal
    weights mapper maps ``model.language_model.`` onto
    ``language_model.model.``.
    """
    key = saved_key
    for part in ("lora_A", "lora_B"):
        nested = f".{part}.default.weight"
        flat = f".{part}.weight"
        if key.endswith(nested):
            key = key[: -len(nested)] + flat
    return key


def adapter_prefix_for_ablation(ablation: str) -> str:
    """Return the S3 key prefix listing adapters for one ablation."""
    return f"{ADAPTER_S3_PREFIX}/{ablation}/"


def list_adapter_run_names(ablation: str) -> list[str]:
    """List run folder names under the adapter prefix for ``ablation``."""
    s3 = S3(ARTIFACTS_BUCKET, region_name=DEFAULT_REGION_NAME)
    prefix = adapter_prefix_for_ablation(ablation)
    run_names: set[str] = set()
    for key in s3.list_keys_ordered(prefix):
        if not key.startswith(prefix):
            continue
        remainder = key[len(prefix) :]
        if not remainder:
            continue
        segment = remainder.split("/", 1)[0]
        if segment:
            run_names.add(segment)
    return sorted(run_names)


def resolve_run_name(ablation: str, run_name: str | None) -> str:
    """Return ``run_name`` or the latest adapter folder for ``ablation``."""
    if run_name is not None and run_name.strip():
        return run_name.strip()
    names = list_adapter_run_names(ablation)
    if not names:
        raise FileNotFoundError(
            f"No adapter runs found under s3://{ARTIFACTS_BUCKET}/"
            f"{adapter_prefix_for_ablation(ablation)}. Train an adapter first or "
            "pass --run-name."
        )
    return names[-1]


def resolve_eval_image() -> str:
    """Return the registry tag from ``HF_EVAL_IMAGE``."""
    image = os.environ.get("HF_EVAL_IMAGE", "").strip()
    if not image:
        raise ValueError(
            "Set HF_EVAL_IMAGE to the registry tag to build, push, and run. "
            "Example: docker.io/<namespace>/"
            "lora-finetuning-study2-2026-10-04-eval:latest"
        )
    return image


def image_requires_push(image: str) -> bool:
    """Return whether the launcher should ``docker push`` before submitting."""
    reference = image.strip()
    return not reference.startswith(_SPACE_IMAGE_PREFIXES)


def docker_build_eval_command(image: str) -> list[str]:
    """Return the ``docker build`` command for the eval image."""
    return [
        "docker",
        "build",
        "-f",
        str(DOCKERFILE_EVAL),
        "-t",
        image,
        str(REPO_ROOT),
    ]


def build_eval_image(image: str) -> None:
    """Build ``image`` from ``Dockerfile.eval``."""
    subprocess.run(docker_build_eval_command(image), check=True)


def ensure_eval_image(image: str) -> None:
    """Build ``HF_EVAL_IMAGE`` so the job includes this ``evaluate.py``."""
    build_eval_image(image)


def eval_job_command(
    ablation: str,
    run_name: str,
    *,
    limit: int | None = None,
) -> tuple[str, ...]:
    """Return the in-container command for one eval run."""
    command = (
        *EVAL_COMMAND,
        "--ablation",
        ablation,
        "--run-name",
        run_name,
        "--in-job",
    )
    if limit is not None:
        command = (*command, "--limit", str(limit))
    return command


def eval_job_config(
    ablation: str,
    run_name: str,
    *,
    limit: int | None = None,
    flavor: str = EVAL_FLAVOR,
) -> HuggingFaceJobConfig:
    """Return Hugging Face Jobs settings for one vLLM eval run."""
    if flavor not in FLAVOR_CHOICES:
        raise ValueError(f"flavor must be one of {FLAVOR_CHOICES}, got {flavor!r}")
    return HuggingFaceJobConfig(
        command=eval_job_command(ablation, run_name, limit=limit),
        flavor=flavor,
        timeout=EVAL_TIMEOUT,
        env={
            "PYTHONPATH": "/app",
            "PYTHONUNBUFFERED": "1",
            "AWS_DEFAULT_REGION": DEFAULT_REGION_NAME,
            "AWS_REGION": DEFAULT_REGION_NAME,
        },
        secrets={
            "HF_TOKEN": EnvVarsContainer.get_env_var("HF_TOKEN", required=True),
            "AWS_ACCESS_KEY_ID": EnvVarsContainer.get_env_var(
                "AWS_ACCESS_KEY", required=True
            ),
            "AWS_SECRET_ACCESS_KEY": EnvVarsContainer.get_env_var(
                "AWS_ACCESS_KEY_SECRET", required=True
            ),
        },
        labels={
            "experiment": "lora_finetuning_study2_2026_10_04",
            "ablation": ablation,
            "role": "eval",
        },
    )


def wait_for_job(job_id: str, poll_interval_seconds: float = 30.0) -> JobInfo:
    """Poll until the job reaches a terminal stage."""
    terminal = {
        JobStage.COMPLETED,
        JobStage.ERROR,
        JobStage.CANCELED,
        JobStage.DELETED,
    }
    while True:
        info = inspect_job(job_id=job_id)
        stage = info.status.stage
        if stage in terminal:
            if stage != JobStage.COMPLETED:
                raise RuntimeError(
                    f"Job {job_id} finished with status {stage.value}: "
                    f"{info.status.message or 'no message'}"
                )
            return info
        time.sleep(poll_interval_seconds)


def download_s3_object(s3_uri: str, dest_path: Path) -> None:
    """Download one S3 object to ``dest_path``."""
    bucket, key = parse_s3_uri(s3_uri)
    if not key:
        raise ValueError(f"S3 URI must include an object key: {s3_uri}")
    s3 = S3(bucket, region_name=DEFAULT_REGION_NAME)
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    dest_path.write_bytes(s3.get_bytes(key))


def download_s3_prefix(s3_uri: str, local_dir: Path) -> None:
    """Download every object under ``s3_uri`` into ``local_dir``."""
    bucket, prefix = parse_s3_uri(s3_uri)
    s3 = S3(bucket, region_name=DEFAULT_REGION_NAME)
    local_dir.mkdir(parents=True, exist_ok=True)
    keys = s3.list_keys_ordered(f"{prefix}/" if prefix else "")
    if not keys:
        raise FileNotFoundError(f"No objects found at {s3_uri}")
    for key in keys:
        if prefix and not key.startswith(f"{prefix}/") and key != prefix:
            continue
        relative = key[len(prefix) :].lstrip("/") if prefix else key
        if not relative:
            continue
        dest = local_dir / relative
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(s3.get_bytes(key))


def upload_file_to_s3(local_path: Path, s3_uri: str) -> str:
    """Upload ``local_path`` to the object named by ``s3_uri``."""
    bucket, key = parse_s3_uri(s3_uri)
    if not key:
        raise ValueError(f"S3 URI must include an object key: {s3_uri}")
    s3 = S3(bucket, region_name=DEFAULT_REGION_NAME)
    try:
        s3.upload_file(local_path, key, content_type="application/jsonl")
    except Exception as exc:
        raise RuntimeError(f"Failed to upload {local_path} to {s3_uri}") from exc
    print(s3_uri)
    return s3_uri


def _require_hf_token() -> str:
    token = os.environ.get("HF_TOKEN", "").strip()
    if not token:
        raise SystemExit("HF_TOKEN is required but missing or empty.")
    return token


def _rows_from_dataset(dataset_name: str, limit: int | None = None) -> list[dict[str, Any]]:
    frame = load_dataset(dataset_name)
    missing = _REQUIRED_ROW_COLUMNS - set(frame.columns)
    if missing:
        raise KeyError(f"{dataset_name} missing columns: {sorted(missing)}")
    rows = frame.to_dict(orient="records")
    if limit is not None:
        if limit < 1:
            raise ValueError(f"--limit must be >= 1, got {limit}")
        rows = rows[:limit]
    return rows


def target_modules_in_adapter_keys(keys: Sequence[str]) -> set[str]:
    """Return which trained target module names appear in adapter keys."""
    present: set[str] = set()
    for key in keys:
        for target in LORA_TARGET_MODULES:
            needle = f".{target}."
            if needle in key:
                present.add(target)
                break
    return present


def rewrite_adapter_for_vllm(src_dir: Path, dest_dir: Path) -> Path:
    """Copy ``src_dir`` and rewrite LoRA tensor names for vLLM.

    Leaves the S3 adapter bytes unchanged. Fails if any trained target module
    is missing from the rewritten keys.
    """
    from safetensors.torch import load_file, save_file

    if dest_dir.exists():
        shutil.rmtree(dest_dir)
    shutil.copytree(src_dir, dest_dir)

    weights_path = dest_dir / "adapter_model.safetensors"
    if not weights_path.is_file():
        raise FileNotFoundError(f"Missing adapter weights at {weights_path}")

    saved = load_file(weights_path)
    remapped: dict[str, Any] = {}
    for key, tensor in saved.items():
        remapped[rewrite_adapter_key_for_vllm(key)] = tensor

    present = target_modules_in_adapter_keys(list(remapped))
    missing = sorted(set(LORA_TARGET_MODULES) - present)
    if missing:
        raise RuntimeError(
            "Rewritten adapter is missing trained LoRA targets: "
            f"{missing}. Refusing to score."
        )
    print(
        f"ADAPTER_TARGETS_OK {sorted(present)}",
        flush=True,
    )
    save_file(remapped, weights_path)
    return dest_dir


class _LoraIgnoreCapture(logging.Handler):
    """Collect vLLM log lines that mean a LoRA module was dropped."""

    def __init__(self) -> None:
        super().__init__(level=logging.WARNING)
        self.messages: list[str] = []

    def emit(self, record: logging.LogRecord) -> None:
        message = record.getMessage()
        if any(marker in message for marker in _LORA_IGNORE_MARKERS):
            self.messages.append(message)


def _load_vllm_engine() -> Any:
    """Construct the offline vLLM engine for Study 2 eval."""
    from vllm import LLM

    kwargs: dict[str, Any] = {
        "model": MODEL_NAME,
        "dtype": "bfloat16",
        "max_model_len": MAX_LENGTH,
        "language_model_only": True,
        "enable_lora": True,
        "max_lora_rank": LORA_RANK,
        "max_loras": VLLM_MAX_LORAS,
        "enable_prefix_caching": True,
        "gpu_memory_utilization": VLLM_GPU_MEMORY_UTILIZATION,
        "trust_remote_code": True,
    }
    try:
        return LLM(**kwargs)
    except TypeError:
        # Older images may reject language_model_only; retry without it.
        kwargs.pop("language_model_only", None)
        return LLM(**kwargs)


def _chat_generations(
    llm: Any,
    message_lists: Sequence[list[dict[str, str]]],
    adapter_dir: Path,
) -> list[str]:
    """Generate keep/remove completions with thinking off and the LoRA applied."""
    from vllm import SamplingParams
    from vllm.lora.request import LoRARequest

    sampling = SamplingParams(
        temperature=0.0,
        max_tokens=MAX_NEW_TOKENS,
    )
    lora_request = LoRARequest("study2", 1, str(adapter_dir))
    ignore_capture = _LoraIgnoreCapture()
    root_logger = logging.getLogger()
    root_logger.addHandler(ignore_capture)
    try:
        outputs = llm.chat(
            list(message_lists),
            sampling_params=sampling,
            lora_request=lora_request,
            chat_template_kwargs=dict(CHAT_TEMPLATE_KWARGS),
            use_tqdm=True,
        )
    finally:
        root_logger.removeHandler(ignore_capture)

    if ignore_capture.messages:
        joined = " | ".join(ignore_capture.messages[:5])
        raise RuntimeError(
            "vLLM ignored one or more LoRA modules while loading the adapter. "
            f"Refusing to score. First messages: {joined}"
        )

    generations: list[str] = []
    for output in outputs:
        generations.append(output.outputs[0].text)
    return generations


def score_label_table(
    llm: Any,
    rows: list[dict[str, Any]],
    adapter_dir: Path,
) -> list[dict[str, Any]]:
    """Generate one keep/remove decision per row with vLLM."""
    from experiments.lora_finetuning_study2_2026_10_04.dataloader import (
        row_to_prompt_completion,
    )

    message_lists = [row_to_prompt_completion(row)["prompt"] for row in rows]
    started = time.perf_counter()
    generations = _chat_generations(llm, message_lists, adapter_dir)
    elapsed = time.perf_counter() - started
    print(f"generated {len(generations)}/{len(message_lists)}", flush=True)
    print(f"GENERATE_SECONDS {elapsed:.3f}", flush=True)
    if generations:
        per_row = elapsed / len(generations)
        extrapolated = per_row * FULL_TABLE_N
        print(
            f"EXTRAPOLATED_FULL_TABLE_SECONDS {extrapolated:.1f} "
            f"({extrapolated / 3600:.2f} h)",
            flush=True,
        )

    pred_rows: list[dict[str, Any]] = []
    for row, raw_generation in zip(rows, generations, strict=True):
        gold = str(row["decision"]).lower().strip()
        predicted = parse_generation(raw_generation)
        pred_rows.append(
            {
                "post_id": row["post_id"],
                "decision": gold,
                "predicted_decision": predicted,
                "raw_generation": raw_generation,
                "n_raters": int(row["n_raters"]),
                "n_remove": int(row["n_remove"]),
                "eval_groups": eval_groups_for_row(row["n_raters"], row["n_remove"]),
            }
        )
    return pred_rows


def _assert_smoke_format(pred_rows: Sequence[dict[str, Any]]) -> None:
    """Fail the job when generations look like open thinking or fail to parse."""
    n_invalid = sum(1 for row in pred_rows if row["predicted_decision"] is None)
    thinkingish = [
        row
        for row in pred_rows
        if "<think>" in str(row["raw_generation"])
        and "</think>" not in str(row["raw_generation"])
    ]
    samples = [str(row["raw_generation"])[:80] for row in pred_rows[:5]]
    print(f"SMOKE_SAMPLES {samples!r}", flush=True)
    if thinkingish:
        raise RuntimeError(
            f"{len(thinkingish)} generations look like an open think block. "
            "Pass enable_thinking=False and rebuild the eval image."
        )
    if n_invalid:
        raise RuntimeError(
            f"{n_invalid}/{len(pred_rows)} generations did not parse as "
            "keep/remove. Refusing to treat this run as a valid eval."
        )
    print("SMOKE_FORMAT_OK", flush=True)


def run_in_job(ablation: str, run_name: str, *, limit: int | None = None) -> None:
    """Load adapter, score with vLLM, and upload artifacts (runs inside the job)."""
    _require_hf_token()
    adapter_uri = build_adapter_s3_uri(ablation, run_name)
    raw_adapter_dir = Path("/tmp") / "adapter_raw" / run_name
    vllm_adapter_dir = Path("/tmp") / "adapter_vllm" / run_name
    download_s3_prefix(adapter_uri, raw_adapter_dir)
    rewrite_adapter_for_vllm(raw_adapter_dir, vllm_adapter_dir)

    llm = _load_vllm_engine()
    rows = _rows_from_dataset(STUDY_2_KEEP_REMOVE_LABELS, limit=limit)
    all_preds = score_label_table(llm, rows, vllm_adapter_dir)
    if limit is not None:
        _assert_smoke_format(all_preds)

    metric_rows: list[dict[str, Any]] = []
    for dataset_name in EVAL_DATASETS:
        group_rows = [row for row in all_preds if dataset_name in row["eval_groups"]]
        metrics = compute_classification_metrics(
            [row["decision"] for row in group_rows],
            [row["predicted_decision"] for row in group_rows],
        )
        metric_rows.append(
            {
                "dataset": dataset_name,
                "ablation": ablation,
                "run_name": run_name,
                "positive_class": POSITIVE_CLASS,
                "engine": "vllm",
                "limit": limit,
                **metrics,
            }
        )

    work_dir = Path("/tmp") / "eval_results" / run_name
    work_dir.mkdir(parents=True, exist_ok=True)
    preds_path = work_dir / "preds.jsonl"
    metrics_path = work_dir / "metrics.jsonl"
    _write_jsonl(preds_path, all_preds)
    _write_jsonl(metrics_path, metric_rows)

    preds_uri = build_results_s3_uri(ablation, run_name, "preds.jsonl")
    metrics_uri = build_results_s3_uri(ablation, run_name, "metrics.jsonl")
    upload_file_to_s3(preds_path, preds_uri)
    upload_file_to_s3(metrics_path, metrics_uri)


def _write_jsonl(path: Path, rows: Sequence[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def launch_eval(
    ablation: str,
    run_name: str | None,
    *,
    limit: int | None = None,
    flavor: str = EVAL_FLAVOR,
) -> JobInfo:
    """Build eval image, submit job, wait, and download local metrics."""
    resolved_run_name = resolve_run_name(ablation, run_name)
    image = resolve_eval_image()
    ensure_eval_image(image)
    job = upload_to_hf_jobs(
        image,
        eval_job_config(
            ablation,
            resolved_run_name,
            limit=limit,
            flavor=flavor,
        ),
        push=image_requires_push(image),
    )
    print(job.url)
    wait_for_job(job.id)
    metrics_uri = build_results_s3_uri(ablation, resolved_run_name, "metrics.jsonl")
    dest = local_metrics_path(ablation, resolved_run_name)
    download_s3_object(metrics_uri, dest)
    print(dest)
    return job


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Evaluate a Study 2 LoRA adapter on three label tables with vLLM."
    )
    parser.add_argument(
        "--ablation",
        required=True,
        choices=ABLATION_CHOICES,
        help="Training ablation whose adapter to load (unanimous, split, or all).",
    )
    parser.add_argument(
        "--run-name",
        default=None,
        help="Weights & Biases run name / adapter folder. Defaults to the latest.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Score only the first N rows (smoke). Default is the full table.",
    )
    parser.add_argument(
        "--flavor",
        default=EVAL_FLAVOR,
        choices=FLAVOR_CHOICES,
        help="Hugging Face Jobs GPU flavor. Default l4x1; use a100-large after OOM.",
    )
    parser.add_argument(
        "--in-job",
        action="store_true",
        help="Run inside Hugging Face Jobs (load model, upload results).",
    )
    return parser


def main(argv: list[str] | None = None) -> None:
    args = build_parser().parse_args(argv)
    limit = args.limit
    if limit is not None and limit < 1:
        raise SystemExit("--limit must be >= 1.")
    if args.in_job:
        if not args.run_name or not str(args.run_name).strip():
            raise SystemExit("--run-name is required when --in-job is set.")
        run_in_job(args.ablation, str(args.run_name).strip(), limit=limit)
        return
    launch_eval(
        args.ablation,
        args.run_name,
        limit=limit,
        flavor=str(args.flavor),
    )


if __name__ == "__main__":
    main(sys.argv[1:])
