from __future__ import annotations

"""
Sample original posts, generate mirrored flips with per-post max_tokens, and validate length parity.

Run from repo root:

PYTHONPATH=. uv run python experiments/match_lengths_original_mirrors_2026_06_19/run_match_lengths_v2.py
"""

import math
from pathlib import Path

import pandas as pd
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel
from tqdm import tqdm

from experiments.match_lengths_original_mirrors_2026_06_19.prompts import FLIP_PROMPT_V2
from experiments.match_lengths_original_mirrors_2026_06_19.run_match_lengths import (
    INPUT_CSV,
    LENGTH_DIFF_THRESHOLD,
    RANDOM_SEED,
    _compute_target_group,
    _output_timestamp,
    _sample_posts,
    _validate_equal_lengths,
    get_llm,
)

EXPERIMENT_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = EXPERIMENT_DIR / "outputs" / "match_lengths_v2"

TOKEN_BUFFER = 1.05
JSON_OVERHEAD_TOKENS = 20
MIN_MAX_TOKENS = 32


class FlipResponse(BaseModel):
    flipped_text: str


def _build_prompt_template() -> ChatPromptTemplate:
    target_placeholder = "[SPECIFIC FIGURE/GROUP — e.g., Republicans/Democrats, Donald Trump/Joe Biden]"
    prompt_template = FLIP_PROMPT_V2.replace(target_placeholder, "{target_group}")
    prompt_template = prompt_template + "\n\nPost:\n{post_text}\n"
    return ChatPromptTemplate.from_messages([("human", prompt_template)])


def _compute_max_tokens(post_text: str, llm) -> int:
    input_tokens = llm.get_num_tokens(post_text)
    budget = math.ceil(input_tokens * TOKEN_BUFFER) + JSON_OVERHEAD_TOKENS
    return max(budget, MIN_MAX_TOKENS)


def _generate_flips(df: pd.DataFrame) -> pd.DataFrame:
    prompt = _build_prompt_template()
    base_llm = get_llm()

    rows: list[dict[str, str | int]] = []
    for row in tqdm(df.itertuples(index=False), total=len(df), desc="Generating flips"):
        post_text = str(row.original_text)
        max_tokens = _compute_max_tokens(post_text, base_llm)
        llm = base_llm.bind(max_tokens=max_tokens)
        structured = llm.with_structured_output(FlipResponse, method="json_schema")
        chain = prompt | structured
        resp = chain.invoke(
            {
                "post_text": post_text,
                "target_group": _compute_target_group(str(row.sampled_stance)),
            }
        )
        rows.append(
            {
                "post_primary_key": str(row.post_primary_key),
                "original_text": post_text,
                "sample_toxicity_type": str(row.sample_toxicity_type),
                "sampled_stance": str(row.sampled_stance),
                "mirrored_text": str(resp.flipped_text),
                "original_token_count": base_llm.get_num_tokens(post_text),
                "max_output_tokens": max_tokens,
            }
        )

    return pd.DataFrame(rows)


def _validate_token_lengths(df: pd.DataFrame) -> None:
    llm = get_llm()
    original_tokens = df["original_text"].fillna("").astype(str).map(llm.get_num_tokens)
    mirrored_tokens = df["mirrored_text"].fillna("").astype(str).map(llm.get_num_tokens)

    nonzero_original = original_tokens > 0
    rel_diff = (mirrored_tokens - original_tokens).abs() / original_tokens
    length_diff_mask = nonzero_original & (rel_diff >= LENGTH_DIFF_THRESHOLD)

    n_posts = len(df)
    n_length_diff = int(length_diff_mask.sum())

    print("Token-based length check:")
    print(f"Average original length (tokens): {original_tokens.mean():.1f}")
    print(f"Average mirrored length (tokens): {mirrored_tokens.mean():.1f}")
    print(
        f"Posts with mirrored token count differing from original by "
        f">={LENGTH_DIFF_THRESHOLD:.0%}: {n_length_diff:,} "
        f"({n_length_diff / n_posts:.1%})"
    )
    print()


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
    print()
    _validate_token_lengths(results)


if __name__ == "__main__":
    main()
