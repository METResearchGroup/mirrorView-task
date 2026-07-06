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
    load_train_test_splits,
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


def _append_prediction_row(
    *,
    path: Path,
    row: tuple[str, int, int],
    lock: threading.Lock,
) -> None:
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
    train_split: float,
    seed: int,
    post_shuffle_seed: int,
    limit: Optional[int],
    max_concurrency: int,
    temperature: float,
    n_train: int,
    n_test: int,
    train_done_rows: int,
    test_done_rows: int,
    cmd_parts: list[str],
    status: str,
) -> dict[str, Any]:
    return {
        "timestamp": timestamp,
        "variant_slug": variant_slug,
        "bedrock_model_id": bedrock_model_id,
        "train_split": float(train_split),
        "seed": int(seed),
        "post_shuffle_seed": int(post_shuffle_seed),
        "limit": None if limit is None else int(limit),
        "max_concurrency": int(max_concurrency),
        "temperature": float(temperature),
        "status": status,
        "n_train": int(n_train),
        "n_test": int(n_test),
        "split": {
            "train_rows": int(n_train),
            "test_rows": int(n_test),
            "train_done_rows": int(train_done_rows),
            "test_done_rows": int(test_done_rows),
            "api_requests_total": int(n_train + n_test),
            "api_requests_done": int(train_done_rows + test_done_rows),
            "api_requests_remaining": int(
                (n_train - train_done_rows) + (n_test - test_done_rows)
            ),
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
    train_split: float = 0.8,
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

    train_pred_path = out_dir / "train_predictions.csv"
    test_pred_path = out_dir / "test_predictions.csv"
    metadata_path = out_dir / "metadata.json"
    metrics_path = out_dir / "metrics.json"

    cmd_parts = sys.argv.copy()
    (out_dir / "run_command.txt").write_text(json.dumps(cmd_parts, indent=2), encoding="utf-8")
    (out_dir / "prompt_template.txt").write_text(prompts.STUDY_PROMPT_TEMPLATE, encoding="utf-8")

    llm = get_llm(bedrock_model_id=bedrock_model_id, temperature=temperature)
    structured = llm.with_structured_output(IsRemoveResult, method="json_schema")
    prompt_tmpl = ChatPromptTemplate.from_messages([("human", "{user_prompt}")])
    chain = prompt_tmpl | structured

    train_df, test_df = load_train_test_splits(train_split=train_split, seed=seed)
    train_df = maybe_limit_df(train_df, limit=limit, seed=seed + 1)
    test_df = maybe_limit_df(test_df, limit=limit, seed=seed + 2)

    existing_train = _load_predictions(train_pred_path)
    existing_test = _load_predictions(test_pred_path)
    done_train_ids = set(existing_train["message_id"].astype(str))
    done_test_ids = set(existing_test["message_id"].astype(str))

    train_remaining_df = train_df[
        ~train_df["message_id"].astype(str).isin(done_train_ids)
    ].copy()
    test_remaining_df = test_df[~test_df["message_id"].astype(str).isin(done_test_ids)].copy()

    n_train = int(len(train_df))
    n_test = int(len(test_df))
    train_done_n = n_train - int(len(train_remaining_df))
    test_done_n = n_test - int(len(test_remaining_df))
    remaining_n = int(len(train_remaining_df) + len(test_remaining_df))

    print(
        f"[{variant_slug}] api_requests_total={n_train + n_test} "
        f"(train={n_train}, test={n_test}); "
        f"done={train_done_n + test_done_n}; remaining={remaining_n}",
        flush=True,
    )

    write_lock = threading.Lock()
    progress_state = {"train_done": train_done_n, "test_done": test_done_n}
    metadata_write_every = 10

    def _write_metadata(status: str) -> None:
        metadata = _build_metadata(
            timestamp=timestamp,
            variant_slug=variant_slug,
            bedrock_model_id=bedrock_model_id,
            train_split=train_split,
            seed=seed,
            post_shuffle_seed=post_shuffle_seed,
            limit=limit,
            max_concurrency=max_concurrency,
            temperature=temperature,
            n_train=n_train,
            n_test=n_test,
            train_done_rows=progress_state["train_done"],
            test_done_rows=progress_state["test_done"],
            cmd_parts=cmd_parts,
            status=status,
        )
        _write_json(metadata_path, metadata)

    def _bump(split: str) -> None:
        with write_lock:
            progress_state[f"{split}_done"] += 1
            done = progress_state["train_done"] + progress_state["test_done"]
            if done % metadata_write_every == 0:
                _write_metadata(status="running")

    _write_metadata(status="running")

    if remaining_n == 0 and metrics_path.exists():
        print(f"[{variant_slug}] already complete at {out_dir}", flush=True)
        return out_dir

    async def _do_predictions() -> None:
        await _predict_rows_concurrently(
            df=train_remaining_df,
            chain=chain,
            post_shuffle_seed=post_shuffle_seed,
            max_concurrency=max_concurrency,
            predictions_path=train_pred_path,
            write_lock=write_lock,
            progress_desc=f"{variant_slug} train",
            on_progress=lambda: _bump("train"),
        )
        await _predict_rows_concurrently(
            df=test_remaining_df,
            chain=chain,
            post_shuffle_seed=post_shuffle_seed,
            max_concurrency=max_concurrency,
            predictions_path=test_pred_path,
            write_lock=write_lock,
            progress_desc=f"{variant_slug} test",
            on_progress=lambda: _bump("test"),
        )

    asyncio.run(_do_predictions())

    train_pred_df = _load_predictions(train_pred_path)
    test_pred_df = _load_predictions(test_pred_path)

    if len(train_pred_df) != n_train:
        raise RuntimeError(
            f"train predictions incomplete: got {len(train_pred_df)}, expected {n_train}"
        )
    if len(test_pred_df) != n_test:
        raise RuntimeError(
            f"test predictions incomplete: got {len(test_pred_df)}, expected {n_test}"
        )

    train_metrics = _hard_label_metrics(
        y_true=train_pred_df["keep_remove_label"].astype(int).values,
        y_pred=train_pred_df["predicted_label"].astype(int).values,
    )
    test_metrics = _hard_label_metrics(
        y_true=test_pred_df["keep_remove_label"].astype(int).values,
        y_pred=test_pred_df["predicted_label"].astype(int).values,
    )

    _write_json(
        metrics_path,
        {"train_metrics": train_metrics, "test_metrics": test_metrics},
    )

    progress_state["train_done"] = n_train
    progress_state["test_done"] = n_test
    _write_metadata(status="complete")

    print(f"[{variant_slug}] complete -> {out_dir}", flush=True)
    return out_dir
