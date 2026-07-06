"""Run zero-shot Bedrock baseline for Qwen3 Next 80B A3B.

Run from root: PYTHONPATH=. uv run python experiments/predict_keep_remove_2026_07_01/models/llm_finetuning/api_baselines/qwen3-next-80b-a3b/train.py
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer

from experiments.predict_keep_remove_2026_07_01.models.llm_finetuning.api_baselines.runner import (
    run_bedrock_baseline_variant,
)

app = typer.Typer(add_completion=False, no_args_is_help=True)

_OUTPUTS_PARENT = Path(__file__).resolve().parent / "outputs"


@app.command()
def main(
    train_split: float = typer.Option(0.8, "--train-split", min=0.01, max=0.99),
    seed: int = typer.Option(42, "--seed"),
    limit: Optional[int] = typer.Option(None, "--limit"),
    max_concurrency: int = typer.Option(2, "--max-concurrency", min=1, max=50),
    temperature: float = typer.Option(0.0, "--temperature", min=-1.0, max=2.0),
    resume: Optional[Path] = typer.Option(None, "--resume", exists=True, file_okay=False, dir_okay=True),
) -> None:
    run_bedrock_baseline_variant(
        variant_slug="qwen3_next_80b_a3b",
        bedrock_model_id="qwen.qwen3-next-80b-a3b",
        outputs_dir=_OUTPUTS_PARENT,
        train_split=train_split,
        seed=seed,
        limit=limit,
        max_concurrency=max_concurrency,
        temperature=temperature,
        resume=resume,
    )


if __name__ == "__main__":
    app()
