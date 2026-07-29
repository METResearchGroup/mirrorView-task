"""Example wiring for the shared structured LLM runner.

Run from root (after filling posts + OPENAI_API_KEY):
  PYTHONPATH=. uv run python experiments/llm_prompt_tuning_2026_07_29/scaffold.py
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
from pydantic import BaseModel, Field

from experiments.llm_prompt_tuning_2026_07_29 import prompt as prompt_mod
from shared.models.llm import LLMConfig, run_structured_llm

EXPERIMENT_DIR = Path(__file__).resolve().parent


class Decision(BaseModel):
    decision: str = Field(description="Model decision label.")
    confidence: float = Field(ge=0.0, le=1.0, description="Confidence in [0, 1].")


def render_user_prompt(row: pd.Series) -> str:
    return f"""Post:
{row['original_text']}

{prompt_mod.prompt}
"""


def main() -> None:
    posts = pd.DataFrame(
        columns=["message_id", "original_text"],
        # Replace with a real dataset load.
    )
    if posts.empty:
        raise SystemExit("scaffold: load posts before running")

    run_structured_llm(
        posts,
        llm_config=LLMConfig.openai(max_concurrency=2),
        output_path=EXPERIMENT_DIR,
        response_model=Decision,
        system_prompt="You classify social media posts.",
        render_user_prompt=render_user_prompt,
        id_column="message_id",
        pass_through_columns=["original_text"],
        progress_desc="prompt_tuning",
    )


if __name__ == "__main__":
    main()
