"""Shared execution runner for keep/remove prompting variants.

Leaf variants provide only prompt rendering functions; this runner owns:
- data split + few-shot support-example leakage policy
- concurrent LLM calls with tqdm progress
- incremental prediction writes (resume-safe)
- metrics computation + artifact writing

Run from root: PYTHONPATH=. uv run python experiments/predict_keep_remove_2026_07_01/models/llm_api/summarize_results.py
"""

from __future__ import annotations

import asyncio
import csv
import json
import os
import sys
import threading
from pathlib import Path
from typing import Any, Callable, Optional

import pandas as pd
from langchain_core.prompts import ChatPromptTemplate
from tqdm import tqdm

from experiments.predict_keep_remove_2026_07_01.models.llm_api.client import get_llm
from experiments.predict_keep_remove_2026_07_01.models.llm_api.constants import (
    InputMode,
    ModelSize,
    PromptType,
)
from experiments.predict_keep_remove_2026_07_01.models.llm_api.dataset import (
    SupportExample,
    load_train_test_splits,
    maybe_limit_df,
    select_support_examples,
)
from experiments.predict_keep_remove_2026_07_01.models.llm_api.schemas import KeepRemoveDecision
from experiments.simplified_predict_remove_2026_05_13.features import classification_metrics_summary
from lib.timestamp_utils import get_current_timestamp


UserPromptRenderFn = Callable[..., str]

PRED_COLUMNS = [
    "message_id",
    "keep_remove_label",
    "predicted_label",
    "predicted_remove_probability",
]


async def _predict_one(
    *,
    row: pd.Series,
    chain: Any,
    prompt_type: PromptType,
    input_mode: InputMode,
    support_examples: list[SupportExample],
    render_user_prompt_one_shot: UserPromptRenderFn,
    render_user_prompt_few_shot: UserPromptRenderFn,
) -> tuple[str, int, int, float]:
    user_prompt: str
    if prompt_type == "one_shot":
        user_prompt = render_user_prompt_one_shot(
            original_text=str(row["original_text"]),
            mirror_text=str(row["mirror_text"]),
            input_mode=input_mode,
        )
    else:
        user_prompt = render_user_prompt_few_shot(
            original_text=str(row["original_text"]),
            mirror_text=str(row["mirror_text"]),
            input_mode=input_mode,
            support_examples=support_examples,
        )

    # Structured output enforces schema; we still defend with retries upstream if needed.
    if hasattr(chain, "ainvoke"):
        resp: KeepRemoveDecision = await chain.ainvoke({"user_prompt": user_prompt})
    else:
        # Fallback: run sync invoke in a thread when async isn't available.
        resp = await asyncio.to_thread(chain.invoke, {"user_prompt": user_prompt})

    message_id = str(row["message_id"])
    y_true = int(row["keep_remove_label"])
    y_pred = 1 if resp.decision == "remove" else 0
    pos_score = float(resp.remove_probability)
    return message_id, y_true, y_pred, pos_score


def _select_render_fns(*, leaf_module: Any) -> tuple[UserPromptRenderFn, UserPromptRenderFn, str]:
    if not hasattr(leaf_module, "SYSTEM_PROMPT"):
        raise AttributeError(f"{leaf_module} missing SYSTEM_PROMPT")
    if not hasattr(leaf_module, "render_user_prompt_one_shot"):
        raise AttributeError(f"{leaf_module} missing render_user_prompt_one_shot")
    if not hasattr(leaf_module, "render_user_prompt_few_shot"):
        raise AttributeError(f"{leaf_module} missing render_user_prompt_few_shot")
    return (
        getattr(leaf_module, "render_user_prompt_one_shot"),
        getattr(leaf_module, "render_user_prompt_few_shot"),
        getattr(leaf_module, "SYSTEM_PROMPT"),
    )


def _load_predictions(path: Path) -> pd.DataFrame:
    if not path.exists() or path.stat().st_size == 0:
        return pd.DataFrame(columns=PRED_COLUMNS)
    df = pd.read_csv(path)
    for col in PRED_COLUMNS:
        if col not in df.columns:
            raise ValueError(f"{path} missing required column {col!r}")
    # Keep last prediction if a message_id was written more than once.
    df = df.drop_duplicates(subset=["message_id"], keep="last")
    return df[PRED_COLUMNS].copy()


def _append_prediction_row(
    *,
    path: Path,
    row: tuple[str, int, int, float],
    lock: threading.Lock,
) -> None:
    """Append one prediction and fsync so progress survives process death."""
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
    model_size: ModelSize,
    model_name: str,
    prompt_type: PromptType,
    input_mode: InputMode,
    train_split: float,
    seed: int,
    limit: Optional[int],
    max_concurrency: int,
    temperature: float,
    train_total_rows: int,
    train_scored_rows: int,
    test_rows: int,
    train_done_rows: int,
    test_done_rows: int,
    reserved_support: list[SupportExample],
    prompt_type_is_few_shot: bool,
    cmd_parts: list[str],
    status: str,
) -> dict[str, Any]:
    reserved_ids = [s.message_id for s in reserved_support] if prompt_type_is_few_shot else []
    return {
        "timestamp": timestamp,
        "variant_slug": variant_slug,
        "model_size": model_size,
        "model_name": model_name,
        "prompt_type": prompt_type,
        "input_mode": input_mode,
        "train_split": float(train_split),
        "seed": int(seed),
        "limit": None if limit is None else int(limit),
        "max_concurrency": int(max_concurrency),
        "temperature": float(temperature),
        "status": status,
        "split": {
            "train_total_rows": int(train_total_rows),
            "train_scored_rows": int(train_scored_rows),
            "test_rows": int(test_rows),
            "train_done_rows": int(train_done_rows),
            "test_done_rows": int(test_done_rows),
            "api_requests_total": int(train_scored_rows + test_rows),
            "api_requests_done": int(train_done_rows + test_done_rows),
            "api_requests_remaining": int(
                (train_scored_rows - train_done_rows) + (test_rows - test_done_rows)
            ),
        },
        "few_shot_reserved_support": {
            "reserved_support_count": int(len(reserved_support)),
            "reserved_support_message_ids": reserved_ids,
        },
        "label_encoding": {"keep_remove_label_0": "keep", "keep_remove_label_1": "remove"},
        "command": cmd_parts,
    }


async def _predict_rows_concurrently(
    *,
    df: pd.DataFrame,
    chain: Any,
    prompt_type: PromptType,
    input_mode: InputMode,
    support_examples: list[SupportExample],
    render_user_prompt_one_shot: UserPromptRenderFn,
    render_user_prompt_few_shot: UserPromptRenderFn,
    max_concurrency: int,
    predictions_path: Path,
    write_lock: threading.Lock,
    progress_desc: str,
    on_progress: Callable[[], None],
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
                prompt_type=prompt_type,
                input_mode=input_mode,
                support_examples=support_examples,
                render_user_prompt_one_shot=render_user_prompt_one_shot,
                render_user_prompt_few_shot=render_user_prompt_few_shot,
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


def run_llm_prompt_variant(
    *,
    variant_slug: str,
    model_name: str,
    model_size: ModelSize,
    prompt_type: PromptType,
    input_mode: InputMode,
    outputs_dir: Path,
    leaf_module: Any,
    train_split: float,
    seed: int,
    limit: Optional[int],
    max_concurrency: int,
    support_examples: int,
    temperature: float = 0.0,
    resume: Optional[Path] = None,
) -> Path:
    outputs_dir.mkdir(parents=True, exist_ok=True)

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

    render_one, render_few, system_prompt = _select_render_fns(leaf_module=leaf_module)
    (out_dir / "prompt_system.txt").write_text(system_prompt, encoding="utf-8")

    llm = get_llm(model_name=model_name, temperature=temperature)
    structured = llm.with_structured_output(KeepRemoveDecision)
    prompt_tmpl = ChatPromptTemplate.from_messages(
        [("system", system_prompt), ("human", "{user_prompt}")]
    )
    chain = prompt_tmpl | structured

    train_df, test_df = load_train_test_splits(train_split=train_split, seed=seed)

    # Few-shot leakage policy:
    # - reserve support examples strictly from train fold
    # - exclude reserved examples from train scoring/metrics
    reserved_support: list[SupportExample] = []
    train_scored_df = train_df
    if prompt_type == "few_shot":
        reserved_support, train_scored_df = select_support_examples(
            train_df, support_examples=support_examples, seed=seed
        )

    train_scored_df = maybe_limit_df(train_scored_df, limit=limit, seed=seed + 1)
    test_df = maybe_limit_df(test_df, limit=limit, seed=seed + 2)

    support_for_prompt = reserved_support if prompt_type == "few_shot" else []

    existing_train = _load_predictions(train_pred_path)
    existing_test = _load_predictions(test_pred_path)
    done_train_ids = set(existing_train["message_id"].astype(str))
    done_test_ids = set(existing_test["message_id"].astype(str))

    train_remaining_df = train_scored_df[
        ~train_scored_df["message_id"].astype(str).isin(done_train_ids)
    ].copy()
    test_remaining_df = test_df[~test_df["message_id"].astype(str).isin(done_test_ids)].copy()

    train_total = int(len(train_df))
    train_scored_n = int(len(train_scored_df))
    test_n = int(len(test_df))
    train_done_n = train_scored_n - int(len(train_remaining_df))
    test_done_n = test_n - int(len(test_remaining_df))
    remaining_n = int(len(train_remaining_df) + len(test_remaining_df))

    print(
        f"[{variant_slug}] api_requests_total={train_scored_n + test_n} "
        f"(train={train_scored_n}, test={test_n}); "
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
            model_size=model_size,
            model_name=model_name,
            prompt_type=prompt_type,
            input_mode=input_mode,
            train_split=train_split,
            seed=seed,
            limit=limit,
            max_concurrency=max_concurrency,
            temperature=temperature,
            train_total_rows=train_total,
            train_scored_rows=train_scored_n,
            test_rows=test_n,
            train_done_rows=progress_state["train_done"],
            test_done_rows=progress_state["test_done"],
            reserved_support=reserved_support,
            prompt_type_is_few_shot=(prompt_type == "few_shot"),
            cmd_parts=cmd_parts,
            status=status,
        )
        _write_json(metadata_path, metadata)

    def _bump(split: str) -> None:
        # Prediction CSV is already durable; metadata is a coarser progress snapshot.
        with write_lock:
            progress_state[f"{split}_done"] += 1
            done = progress_state["train_done"] + progress_state["test_done"]
            if done % metadata_write_every == 0:
                _write_metadata(status="running")

    def _bump_train() -> None:
        _bump("train")

    def _bump_test() -> None:
        _bump("test")

    _write_metadata(status="running")

    if remaining_n == 0 and metrics_path.exists():
        print(f"[{variant_slug}] already complete at {out_dir}", flush=True)
        return out_dir

    async def _do_predictions() -> None:
        await _predict_rows_concurrently(
            df=train_remaining_df,
            chain=chain,
            prompt_type=prompt_type,
            input_mode=input_mode,
            support_examples=support_for_prompt,
            render_user_prompt_one_shot=render_one,
            render_user_prompt_few_shot=render_few,
            max_concurrency=max_concurrency,
            predictions_path=train_pred_path,
            write_lock=write_lock,
            progress_desc=f"{variant_slug} train",
            on_progress=_bump_train,
        )
        await _predict_rows_concurrently(
            df=test_remaining_df,
            chain=chain,
            prompt_type=prompt_type,
            input_mode=input_mode,
            support_examples=support_for_prompt,
            render_user_prompt_one_shot=render_one,
            render_user_prompt_few_shot=render_few,
            max_concurrency=max_concurrency,
            predictions_path=test_pred_path,
            write_lock=write_lock,
            progress_desc=f"{variant_slug} test",
            on_progress=_bump_test,
        )

    asyncio.run(_do_predictions())

    train_pred_df = _load_predictions(train_pred_path)
    test_pred_df = _load_predictions(test_pred_path)

    if len(train_pred_df) != train_scored_n:
        raise RuntimeError(
            f"train predictions incomplete: got {len(train_pred_df)}, expected {train_scored_n}"
        )
    if len(test_pred_df) != test_n:
        raise RuntimeError(
            f"test predictions incomplete: got {len(test_pred_df)}, expected {test_n}"
        )

    # Metrics: class "remove" is the positive class (y=1).
    train_metrics = classification_metrics_summary(
        y_true=train_pred_df["keep_remove_label"].astype(int).values,
        y_pred=train_pred_df["predicted_label"].astype(int).values,
        pos_scores=train_pred_df["predicted_remove_probability"].astype(float).values,
    )
    test_metrics = classification_metrics_summary(
        y_true=test_pred_df["keep_remove_label"].astype(int).values,
        y_pred=test_pred_df["predicted_label"].astype(int).values,
        pos_scores=test_pred_df["predicted_remove_probability"].astype(float).values,
    )

    _write_json(
        metrics_path,
        {"train_metrics": train_metrics, "test_metrics": test_metrics},
    )

    progress_state["train_done"] = train_scored_n
    progress_state["test_done"] = test_n
    _write_metadata(status="complete")

    print(f"[{variant_slug}] complete -> {out_dir}", flush=True)
    return out_dir
