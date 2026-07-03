"""Run few-shot/original/small keep/remove prompting.

Run from root: PYTHONPATH=. uv run python experiments/predict_keep_remove_2026_07_01/models/llm_api/few_shot/original/small/train.py
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer

from experiments.predict_keep_remove_2026_07_01.models.llm_api import constants
from experiments.predict_keep_remove_2026_07_01.models.llm_api.runner import run_llm_prompt_variant

from experiments.predict_keep_remove_2026_07_01.models.llm_api.few_shot.original.small import (
    prompt as leaf_prompt,
)

app = typer.Typer(add_completion=False, no_args_is_help=True)

_RUN_ROOT = Path(__file__).resolve().parent
_OUTPUTS_PARENT = _RUN_ROOT / "outputs"


@app.command()
def main(
    train_split: float = typer.Option(0.8, "--train-split", min=0.01, max=0.99),
    seed: int = typer.Option(42, "--seed"),
    limit: Optional[int] = typer.Option(None, "--limit"),
    max_concurrency: int = typer.Option(2, "--max-concurrency", min=1, max=50),
    support_examples: int = typer.Option(8, "--support-examples", min=0, max=200),
    temperature: float = typer.Option(0.0, "--temperature", min=-1.0, max=2.0),
) -> None:
    run_llm_prompt_variant(
        variant_slug="few_shot_original_small",
        model_name=constants.MODEL_ID_BY_SIZE["small"],
        model_size="small",
        prompt_type="few_shot",
        input_mode="original",
        outputs_dir=_OUTPUTS_PARENT,
        leaf_module=leaf_prompt,
        train_split=train_split,
        seed=seed,
        limit=limit,
        max_concurrency=max_concurrency,
        support_examples=support_examples,
        temperature=temperature,
    )


if __name__ == "__main__":
    app()

