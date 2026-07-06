"""Run zero-shot Bedrock baseline for Ministral 3 14B Instruct.

Run from root: PYTHONPATH=. uv run python experiments/predict_keep_remove_2026_07_01/models/llm_finetuning/api_baselines/ministral-3-14b-instruct/train.py
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
    seed: int = typer.Option(42, "--seed"),
    limit: Optional[int] = typer.Option(None, "--limit"),
    max_concurrency: int = typer.Option(2, "--max-concurrency", min=1, max=50),
    temperature: float = typer.Option(0.0, "--temperature", min=-1.0, max=2.0),
    resume: Optional[Path] = typer.Option(None, "--resume", exists=True, file_okay=False, dir_okay=True),
) -> None:
    run_bedrock_baseline_variant(
        variant_slug="ministral_3_14b_instruct",
        bedrock_model_id="mistral.ministral-3-14b-instruct",
        outputs_dir=_OUTPUTS_PARENT,
        seed=seed,
        limit=limit,
        max_concurrency=max_concurrency,
        temperature=temperature,
        resume=resume,
    )


if __name__ == "__main__":
    app()
