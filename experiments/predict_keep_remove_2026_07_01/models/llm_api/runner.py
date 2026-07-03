"""Shared execution runner for keep/remove prompting variants.

Leaf variants provide only prompt rendering functions; this runner owns:
- data split + few-shot support-example leakage policy
- concurrent LLM calls
- metrics computation + artifact writing

Run from root: PYTHONPATH=. uv run python experiments/predict_keep_remove_2026_07_01/models/llm_api/summarize_results.py
"""

from __future__ import annotations

import asyncio
import json
import sys
from dataclasses import asdict
from pathlib import Path
from typing import Any, Awaitable, Callable, Optional

import pandas as pd
from langchain_core.prompts import ChatPromptTemplate

from experiments.predict_keep_remove_2026_07_01.models.llm_api.client import get_llm
from experiments.predict_keep_remove_2026_07_01.models.llm_api.constants import (
    InputMode,
    ModelSize,
    PromptType,
)
from experiments.predict_keep_remove_2026_07_01.models.llm_api.dataset import (
    SupportExample,
    label_int_to_decision,
    load_train_test_splits,
    maybe_limit_df,
    select_support_examples,
)
from experiments.predict_keep_remove_2026_07_01.models.llm_api.schemas import KeepRemoveDecision
from experiments.simplified_predict_remove_2026_05_13.features import classification_metrics_summary
from lib.timestamp_utils import get_current_timestamp


UserPromptRenderFn = Callable[..., str]


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
) -> list[tuple[str, int, int, float]]:
    sem = asyncio.Semaphore(max(1, int(max_concurrency)))

    async def _guarded(row: pd.Series) -> tuple[str, int, int, float]:
        async with sem:
            return await _predict_one(
                row=row,
                chain=chain,
                prompt_type=prompt_type,
                input_mode=input_mode,
                support_examples=support_examples,
                render_user_prompt_one_shot=render_user_prompt_one_shot,
                render_user_prompt_few_shot=render_user_prompt_few_shot,
            )

    tasks = [_guarded(row) for _, row in df.iterrows()]
    return await asyncio.gather(*tasks)


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
) -> Path:
    timestamp = get_current_timestamp()
    out_dir = outputs_dir / timestamp
    out_dir.mkdir(parents=True, exist_ok=False)

    cmd_parts = sys.argv.copy()
    l = out_dir / "run_command.txt"
    l.write_text(json.dumps(cmd_parts, indent=2), encoding="utf-8")

    render_one, render_few, system_prompt = _select_render_fns(leaf_module=leaf_module)

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

    # Convert support examples to keep/remove decisions (for prompt rendering).
    support_for_prompt = reserved_support if prompt_type == "few_shot" else []

    async def _do_predictions() -> tuple[pd.DataFrame, pd.DataFrame]:
        train_results = await _predict_rows_concurrently(
            df=train_scored_df,
            chain=chain,
            prompt_type=prompt_type,
            input_mode=input_mode,
            support_examples=support_for_prompt,
            render_user_prompt_one_shot=render_one,
            render_user_prompt_few_shot=render_few,
            max_concurrency=max_concurrency,
        )
        test_results = await _predict_rows_concurrently(
            df=test_df,
            chain=chain,
            prompt_type=prompt_type,
            input_mode=input_mode,
            support_examples=support_for_prompt,
            render_user_prompt_one_shot=render_one,
            render_user_prompt_few_shot=render_few,
            max_concurrency=max_concurrency,
        )

        train_pred_df = pd.DataFrame(
            train_results,
            columns=["message_id", "keep_remove_label", "predicted_label", "predicted_remove_probability"],
        )
        test_pred_df = pd.DataFrame(
            test_results,
            columns=["message_id", "keep_remove_label", "predicted_label", "predicted_remove_probability"],
        )

        # Keep contract-compatible column naming.
        train_pred_df = train_pred_df.rename(columns={"predicted_label": "predicted_label"})
        test_pred_df = test_pred_df.rename(columns={"predicted_label": "predicted_label"})

        return train_pred_df, test_pred_df

    train_pred_df, test_pred_df = asyncio.run(_do_predictions())

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

    (out_dir / "metrics.json").write_text(
        json.dumps({"train_metrics": train_metrics, "test_metrics": test_metrics}, indent=2),
        encoding="utf-8",
    )

    # Predictions CSV naming matches existing contract.
    train_pred_df[
        ["message_id", "keep_remove_label", "predicted_label", "predicted_remove_probability"]
    ].to_csv(out_dir / "train_predictions.csv", index=False)
    test_pred_df[
        ["message_id", "keep_remove_label", "predicted_label", "predicted_remove_probability"]
    ].to_csv(out_dir / "test_predictions.csv", index=False)

    reserved_ids = [s.message_id for s in reserved_support] if prompt_type == "few_shot" else []
    metadata: dict[str, Any] = {
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
        "split": {
            "train_total_rows": int(len(train_df)),
            "train_scored_rows": int(len(train_scored_df)),
            "test_rows": int(len(test_df)),
        },
        "few_shot_reserved_support": {
            "reserved_support_count": int(len(reserved_support)),
            "reserved_support_message_ids": reserved_ids,
        },
        "label_encoding": {"keep_remove_label_0": "keep", "keep_remove_label_1": "remove"},
        "command": cmd_parts,
    }
    (out_dir / "metadata.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")

    # Also store the prompt SYSTEM_PROMPT for provenance (no user prompt content is written).
    (out_dir / "prompt_system.txt").write_text(system_prompt, encoding="utf-8")

    return out_dir

