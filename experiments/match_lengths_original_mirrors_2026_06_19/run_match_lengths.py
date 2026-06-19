from __future__ import annotations

"""
Sample original posts, generate mirrored flips, and validate length parity.

Run from repo root:

PYTHONPATH=. uv run python experiments/match_lengths_original_mirrors_2026_06_19/run_match_lengths.py
"""

from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
from langchain_aws import ChatBedrockConverse
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableConfig
from pydantic import BaseModel
from tqdm import tqdm

from experiments.scaled_mirrors_generation_2026_06_02.prompts import FLIP_PROMPT
from lib.constants import BEDROCK_REGION, DEFAULT_BEDROCK_SONNET_MODEL

EXPERIMENT_DIR = Path(__file__).resolve().parent
INPUT_CSV = (
    Path(__file__).resolve().parents[1]
    / "scaled_mirrors_generation_2026_06_02"
    / "generated_flips"
    / "combined_flips"
    / "flips.csv"
)
OUTPUT_DIR = EXPERIMENT_DIR / "outputs" / "match_lengths"

SAMPLE_SIZE = 50
RANDOM_SEED = 42
BATCH_SIZE = 25
MAX_CONCURRENCY = 10
LENGTH_DIFF_THRESHOLD = 0.10

OUTPUT_COLUMNS = [
    "post_primary_key",
    "original_text",
    "sample_toxicity_type",
    "sampled_stance",
    "mirrored_text",
]


class FlipResponse(BaseModel):
    flipped_text: str
    explanation: str


def get_llm(
    model: str = DEFAULT_BEDROCK_SONNET_MODEL,
    region_name: str = BEDROCK_REGION,
) -> ChatBedrockConverse:
    return ChatBedrockConverse(model=model, region_name=region_name)


def _build_prompt_template() -> ChatPromptTemplate:
    target_placeholder = "[SPECIFIC FIGURE/GROUP — e.g., Republicans/Democrats, Donald Trump/Joe Biden]"
    prompt_template = FLIP_PROMPT.replace(target_placeholder, "{target_group}")
    prompt_template = prompt_template + "\n\nPost:\n{post_text}\n"
    return ChatPromptTemplate.from_messages([("human", prompt_template)])


def _compute_target_group(sampled_stance: str) -> str:
    mapping = {
        "left": "right",
        "right": "left",
    }
    if sampled_stance not in mapping:
        raise ValueError(f"Unexpected sampled_stance `{sampled_stance}`.")
    return mapping[sampled_stance]


def _output_timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y_%m_%d-%H:%M:%S")


def _sample_posts(df: pd.DataFrame) -> pd.DataFrame:
    if len(df) < SAMPLE_SIZE:
        raise ValueError(
            f"Input has {len(df)} rows; need at least {SAMPLE_SIZE} to sample."
        )
    return df.sample(n=SAMPLE_SIZE, random_state=RANDOM_SEED).reset_index(drop=True)


def _generate_flips(df: pd.DataFrame) -> pd.DataFrame:
    prompt = _build_prompt_template()
    llm = get_llm()
    structured = llm.with_structured_output(FlipResponse, method="json_schema")
    chain = prompt | structured

    rows: list[dict[str, str]] = []
    n = len(df)
    for start in tqdm(range(0, n, BATCH_SIZE), desc="Generating flips", unit="batch"):
        batch = df.iloc[start : start + BATCH_SIZE]
        inputs = [
            {
                "post_text": str(text),
                "target_group": _compute_target_group(str(stance)),
            }
            for text, stance in zip(
                batch["original_text"].tolist(),
                batch["sampled_stance"].tolist(),
            )
        ]

        results = chain.batch(inputs, config=RunnableConfig(max_concurrency=MAX_CONCURRENCY))

        for row_in, resp in zip(batch.itertuples(index=False), results, strict=True):
            rows.append(
                {
                    "post_primary_key": str(getattr(row_in, "post_primary_key")),
                    "original_text": str(getattr(row_in, "original_text")),
                    "sample_toxicity_type": str(getattr(row_in, "sample_toxicity_type")),
                    "sampled_stance": str(getattr(row_in, "sampled_stance")),
                    "mirrored_text": str(resp.flipped_text),
                }
            )

    return pd.DataFrame(rows, columns=OUTPUT_COLUMNS)


def _validate_equal_lengths(df: pd.DataFrame, *, flips_csv: Path) -> None:
    if "original_text" not in df.columns or "mirrored_text" not in df.columns:
        raise ValueError(
            f"Expected `original_text` and `mirrored_text` columns in {flips_csv}"
        )

    original_lengths = df["original_text"].fillna("").astype(str).str.len()
    mirrored_lengths = df["mirrored_text"].fillna("").astype(str).str.len()

    nonzero_original = original_lengths > 0
    rel_diff = (mirrored_lengths - original_lengths).abs() / original_lengths
    length_diff_mask = nonzero_original & (rel_diff >= LENGTH_DIFF_THRESHOLD)
    empty_original = original_lengths == 0

    n_posts = len(df)
    n_length_diff = int(length_diff_mask.sum())
    n_empty_original = int(empty_original.sum())

    print(f"Flips CSV: {flips_csv}")
    print(f"Total posts: {n_posts:,}")
    print()
    print(f"Average original length (chars): {original_lengths.mean():.1f}")
    print(f"Average mirrored length (chars): {mirrored_lengths.mean():.1f}")
    print()
    print(
        f"Posts with mirrored length differing from original by "
        f">={LENGTH_DIFF_THRESHOLD:.0%}: {n_length_diff:,} "
        f"({n_length_diff / n_posts:.1%})"
    )
    if n_empty_original:
        print(
            f"Posts with empty original text (excluded from >=10% check): "
            f"{n_empty_original:,}"
        )


def main() -> None:
    if not INPUT_CSV.exists():
        raise FileNotFoundError(f"Input CSV not found: {INPUT_CSV}")

    df = pd.read_csv(INPUT_CSV)
    required_cols = [
        "post_primary_key",
        "original_text",
        "sample_toxicity_type",
        "sampled_stance",
    ]
    missing_cols = [col for col in required_cols if col not in df.columns]
    if missing_cols:
        raise KeyError(f"Missing required columns in {INPUT_CSV}: {missing_cols}")

    sampled = _sample_posts(df)
    print(f"Sampled {len(sampled)} posts from {INPUT_CSV} (seed={RANDOM_SEED}).")

    results = _generate_flips(sampled)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = _output_timestamp()
    out_fp = OUTPUT_DIR / f"{timestamp}.csv"
    results.to_csv(out_fp, index=False)
    print(f"Wrote {len(results)} rows to {out_fp}.")
    print()

    _validate_equal_lengths(results, flips_csv=out_fp)


if __name__ == "__main__":
    main()
