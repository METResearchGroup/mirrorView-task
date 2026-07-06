"""Shared execution runner for Bedrock zero-shot keep/remove baselines.

Run from root: PYTHONPATH=. uv run python experiments/predict_keep_remove_2026_07_01/models/llm_finetuning/api_baselines/ministral-3-8b-instruct/train.py
"""

from __future__ import annotations

import asyncio
import csv
import json
import os
import sys
import threading
from pathlib import Path
from typing import Any, Optional

import pandas as pd
from langchain_core.prompts import ChatPromptTemplate
from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score
from tqdm import tqdm

from experiments.predict_keep_remove_2026_07_01.models.llm_finetuning.api_baselines import prompts
from experiments.predict_keep_remove_2026_07_01.models.llm_finetuning.api_baselines.client import get_llm
from experiments.predict_keep_remove_2026_07_01.models.llm_finetuning.api_baselines.dataset import (
    load_dataset,
    maybe_limit_df,
)
from experiments.predict_keep_remove_2026_07_01.models.llm_finetuning.api_baselines.schemas import (
    IsRemoveResult,
)
from lib.timestamp_utils import get_current_timestamp

PRED_COLUMNS = [
    "message_id",
    "keep_remove_label",
    "predicted_label",
]

PREDICTIONS_FILENAME = "predictions.csv"


def _hard_label_metrics(
    *,
    y_true: list[int] | pd.Series,
    y_pred: list[int] | pd.Series,
) -> dict[str, float]:
    y_true_arr = [int(v) for v in y_true]
    y_pred_arr = [int(v) for v in y_pred]
    return {
        "accuracy": float(accuracy_score(y_true_arr, y_pred_arr)),
        "precision": float(precision_score(y_true_arr, y_pred_arr, zero_division=0)),
        "recall": float(recall_score(y_true_arr, y_pred_arr, zero_division=0)),
        "f1": float(f1_score(y_true_arr, y_pred_arr, zero_division=0)),
    }


async def _predict_one(
    *,
    row: pd.Series,
    chain: Any,
    post_shuffle_seed: int,
) -> tuple[str, int, int]:
    user_prompt = prompts.render_user_prompt(
        original_text=str(row["original_text"]),
        mirror_text=str(row["mirror_text"]),
        message_id=str(row["message_id"]),
        seed=post_shuffle_seed,
    )

    if hasattr(chain, "ainvoke"):
        resp: IsRemoveResult = await chain.ainvoke({"user_prompt": user_prompt})
    else:
        resp = await asyncio.to_thread(chain.invoke, {"user_prompt": user_prompt})

    message_id = str(row["message_id"])
    y_true = int(row["keep_remove_label"])
    y_pred = int(resp.is_remove)
    return message_id, y_true, y_pred


def _load_predictions(path: Path) -> pd.DataFrame:
    if not path.exists() or path.stat().st_size == 0:
        return pd.DataFrame(columns=PRED_COLUMNS)
    df = pd.read_csv(path)
    for col in PRED_COLUMNS:
        if col not in df.columns:
            raise ValueError(f"{path} missing required column {col!r}")
    df = df.drop_duplicates(subset=["message_id"], keep="last")
    return df[PRED_COLUMNS].copy()


def _load_done_message_ids(out_dir: Path) -> set[str]:
    """Collect message_ids already classified in this run."""
    path = out_dir / PREDICTIONS_FILENAME
    if not path.exists() or path.stat().st_size == 0:
        return set()
    return set(_load_predictions(path)["message_id"].astype(str).tolist())


def _append_prediction_row(
    *,
    path: Path,
    row: tuple[str, int, int],
    lock: threading.Lock,
) -> None:
    """Append one prediction row and fsync so progress survives process death."""
    with lock:
        write_header = not path.exists() or path.stat().st_size == 0
        with path.open("a", encoding="utf-8", newline="") as f:
            writer = csv.writer(f)
            if write_header:
                writer.writerow(PRED_COLUMNS)
            writer.writerow(row)
            f.flush()
            os.fsync(f.fileno())


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _build_metadata(
    *,
    timestamp: str,
    variant_slug: str,
    bedrock_model_id: str,
    seed: int,
    post_shuffle_seed: int,
    limit: Optional[int],
    max_concurrency: int,
    temperature: float,
    n_total: int,
    done_rows: int,
    cmd_parts: list[str],
    status: str,
) -> dict[str, Any]:
    return {
        "timestamp": timestamp,
        "variant_slug": variant_slug,
        "bedrock_model_id": bedrock_model_id,
        "seed": int(seed),
        "post_shuffle_seed": int(post_shuffle_seed),
        "limit": None if limit is None else int(limit),
        "max_concurrency": int(max_concurrency),
        "temperature": float(temperature),
        "status": status,
        "n_total": int(n_total),
        "progress": {
            "total_rows": int(n_total),
            "done_rows": int(done_rows),
            "api_requests_total": int(n_total),
            "api_requests_done": int(done_rows),
            "api_requests_remaining": int(n_total - done_rows),
        },
        "label_encoding": {"keep_remove_label_0": "keep", "keep_remove_label_1": "remove"},
        "command": cmd_parts,
    }


async def _predict_rows_concurrently(
    *,
    df: pd.DataFrame,
    chain: Any,
    post_shuffle_seed: int,
    max_concurrency: int,
    predictions_path: Path,
    write_lock: threading.Lock,
    progress_desc: str,
    on_progress: Any,
) -> None:
    if df.empty:
        return

    sem = asyncio.Semaphore(max(1, int(max_concurrency)))
    pbar = tqdm(
        total=len(df),
        desc=progress_desc,
        unit="req",
        file=sys.stdout,
        dynamic_ncols=True,
        mininterval=0.5,
    )

    async def _guarded(row: pd.Series) -> None:
        async with sem:
            result = await _predict_one(
                row=row,
                chain=chain,
                post_shuffle_seed=post_shuffle_seed,
            )
            await asyncio.to_thread(
                _append_prediction_row,
                path=predictions_path,
                row=result,
                lock=write_lock,
            )
            on_progress()
            pbar.update(1)

    try:
        tasks = [_guarded(row) for _, row in df.iterrows()]
        await asyncio.gather(*tasks)
    finally:
        pbar.close()


def run_bedrock_baseline_variant(
    *,
    variant_slug: str,
    bedrock_model_id: str,
    outputs_dir: Path,
    seed: int = 42,
    limit: int | None = None,
    max_concurrency: int = 2,
    temperature: float = 0.0,
    resume: Path | None = None,
) -> Path:
    outputs_dir.mkdir(parents=True, exist_ok=True)
    post_shuffle_seed = int(seed)

    if resume is not None:
        out_dir = resume.expanduser().resolve()
        if not out_dir.is_dir():
            raise FileNotFoundError(f"--resume path does not exist: {out_dir}")
        timestamp = out_dir.name
        print(f"Resuming incomplete run at {out_dir}", flush=True)
    else:
        timestamp = get_current_timestamp()
        out_dir = outputs_dir / timestamp
        out_dir.mkdir(parents=True, exist_ok=False)

    pred_path = out_dir / PREDICTIONS_FILENAME
    metadata_path = out_dir / "metadata.json"
    metrics_path = out_dir / "metrics.json"

    cmd_parts = sys.argv.copy()
    (out_dir / "run_command.txt").write_text(json.dumps(cmd_parts, indent=2), encoding="utf-8")
    (out_dir / "prompt_template.txt").write_text(prompts.STUDY_PROMPT_TEMPLATE, encoding="utf-8")

    llm = get_llm(bedrock_model_id=bedrock_model_id, temperature=temperature)
    structured = llm.with_structured_output(IsRemoveResult, method="json_schema")
    prompt_tmpl = ChatPromptTemplate.from_messages([("human", "{user_prompt}")])
    chain = prompt_tmpl | structured

    df = load_dataset()
    df = maybe_limit_df(df, limit=limit, seed=seed)

    done_ids = _load_done_message_ids(out_dir)
    remaining_df = df[~df["message_id"].astype(str).isin(done_ids)].copy()

    n_total = int(len(df))
    done_n = n_total - int(len(remaining_df))
    remaining_n = int(len(remaining_df))

    print(
        f"[{variant_slug}] api_requests_total={n_total}; "
        f"done={done_n}; remaining={remaining_n}",
        flush=True,
    )

    write_lock = threading.Lock()
    progress_state = {"done": done_n}

    def _write_metadata(status: str) -> None:
        metadata = _build_metadata(
            timestamp=timestamp,
            variant_slug=variant_slug,
            bedrock_model_id=bedrock_model_id,
            seed=seed,
            post_shuffle_seed=post_shuffle_seed,
            limit=limit,
            max_concurrency=max_concurrency,
            temperature=temperature,
            n_total=n_total,
            done_rows=progress_state["done"],
            cmd_parts=cmd_parts,
            status=status,
        )
        _write_json(metadata_path, metadata)

    def _bump() -> None:
        with write_lock:
            progress_state["done"] += 1
            _write_metadata(status="running")

    _write_metadata(status="running")

    if remaining_n == 0 and metrics_path.exists():
        print(f"[{variant_slug}] already complete at {out_dir}", flush=True)
        return out_dir

    async def _do_predictions() -> None:
        await _predict_rows_concurrently(
            df=remaining_df,
            chain=chain,
            post_shuffle_seed=post_shuffle_seed,
            max_concurrency=max_concurrency,
            predictions_path=pred_path,
            write_lock=write_lock,
            progress_desc=variant_slug,
            on_progress=_bump,
        )

    asyncio.run(_do_predictions())

    pred_df = _load_predictions(pred_path)

    if len(pred_df) != n_total:
        raise RuntimeError(
            f"predictions incomplete: got {len(pred_df)}, expected {n_total}"
        )

    metrics = _hard_label_metrics(
        y_true=pred_df["keep_remove_label"].astype(int).values,
        y_pred=pred_df["predicted_label"].astype(int).values,
    )

    _write_json(metrics_path, {"metrics": metrics})

    progress_state["done"] = n_total
    _write_metadata(status="complete")

    print(f"[{variant_slug}] complete -> {out_dir}", flush=True)
    return out_dir
