from __future__ import annotations

import re
from pathlib import Path

import pandas as pd
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableConfig
from langchain_openai import ChatOpenAI
from pydantic import BaseModel
from tqdm import tqdm

from experiments.scaled_mirrors_generation_2026_06_02.prompts import FLIP_PROMPT
from lib.constants import DEFAULT_LLM_MODEL
from lib.load_env_vars import EnvVarsContainer

EXPERIMENT_DIR = Path(__file__).resolve().parent

INPUT_GLOB = "sampled_posts_*.csv"
OUTPUT_PREFIX = "flips_"

# Hard-coded generation settings. This script intentionally provides no CLI args.
BATCH_SIZE = 25
MAX_CONCURRENCY = 10


class FlipResponse(BaseModel):
    flipped_text: str
    explanation: str


def _pick_latest_input_csv() -> Path:
    candidates = sorted(EXPERIMENT_DIR.glob(INPUT_GLOB), key=lambda p: p.stat().st_mtime)
    if not candidates:
        raise FileNotFoundError(f"No input CSVs found: {EXPERIMENT_DIR / INPUT_GLOB}")
    return candidates[-1]


def _extract_input_timestamp(filename: str) -> str:
    m = re.match(r"^sampled_posts_(.+)\\.csv$", filename)
    if not m:
        raise ValueError(f"Unexpected input filename format: {filename}")
    return m.group(1)


def _build_prompt_template() -> ChatPromptTemplate:
    # Replace the bracket placeholder with a runtime template variable.
    target_placeholder = "[SPECIFIC FIGURE/GROUP — e.g., Republicans/Democrats, Donald Trump/Joe Biden]"
    prompt_template = FLIP_PROMPT.replace(target_placeholder, "{target_group}")
    # FLIP_PROMPT does not currently include the post text. Add it explicitly.
    prompt_template = prompt_template + "\n\nPost:\n{post_text}\n"
    return ChatPromptTemplate.from_messages([("human", prompt_template)])


def _compute_target_group(political_stance: str) -> str:
    # Deterministic minimal mapping that assumes stance labels are left/right.
    # We also map "unclear"/"neutral" to themselves so the pipeline does not crash.
    mapping = {
        "left": "right",
        "right": "left",
        "unclear": "unclear",
        "neutral": "neutral",
    }
    return mapping[political_stance]


def main() -> None:
    input_csv = _pick_latest_input_csv()
    input_timestamp = _extract_input_timestamp(input_csv.name)
    out_fp = EXPERIMENT_DIR / f"{OUTPUT_PREFIX}{input_timestamp}.csv"

    df = pd.read_csv(input_csv)

    input_id_col = "id" if "id" in df.columns else "post_id"
    if input_id_col not in df.columns:
        raise KeyError(f"Expected input id column `{input_id_col}` in {input_csv}")

    prompt = _build_prompt_template()
    api_key = EnvVarsContainer.get_env_var("OPENAI_API_KEY", required=True)
    llm = ChatOpenAI(model=DEFAULT_LLM_MODEL, api_key=api_key)
    structured = llm.with_structured_output(FlipResponse)
    chain = prompt | structured

    rows: list[dict[str, str]] = []
    n = len(df)
    for start in tqdm(range(0, n, BATCH_SIZE), desc="Generating flips", unit="batch"):
        batch = df.iloc[start : start + BATCH_SIZE]
        inputs = [
            {
                "post_text": str(t),
                "target_group": _compute_target_group(str(stance)),
            }
            for t, stance in zip(batch["text"].tolist(), batch["political_stance"].tolist())
        ]

        # Batch call via LCEL.
        results = chain.batch(inputs, config=RunnableConfig(max_concurrency=MAX_CONCURRENCY))

        for row_in, resp in zip(batch.itertuples(index=False), results, strict=True):
            rows.append(
                {
                    "ID": str(getattr(row_in, input_id_col)),
                    "original_text": str(getattr(row_in, "text")),
                    "mirrored_text": str(resp.flipped_text),
                    "toxicity_tier": str(getattr(row_in, "toxicity_tier")),
                    "political_stance": str(getattr(row_in, "political_stance")),
                }
            )

    out_df = pd.DataFrame(
        rows,
        columns=[
            "ID",
            "original_text",
            "mirrored_text",
            "toxicity_tier",
            "political_stance",
        ],
    )
    out_df.to_csv(out_fp, index=False)
    print(f"Wrote {out_fp} ({len(out_df)} rows).")


if __name__ == "__main__":
    main()

