from __future__ import annotations

"""
Generate topic-aligned mirrored posts for the v4 sample intervention.

Uses the base FLIP_PROMPT plus an instruction to keep the same political topic
while flipping only stance. Reads the 125-row v3 review sample from
``sample_flips.csv`` (from ``show_examples.py``), preserves ``original_flip``
from ``sample_new_flips_with_original_flips.csv`` where available (generating
missing baselines with the original FLIP_PROMPT), generates fresh topic-aligned
mirrors from ``original_text``, truncates them with v3 sentence-first logic,
and writes:

  outputs/truncation_v4/sample_new_flips_with_original_flips.csv

Columns:
  - ``original_flip``: baseline generation (original prompt), preserved or generated
  - ``new_flip``: topic-aligned generation, post-truncation (v3 rules)

Run from repo root:

PYTHONPATH=. uv run python experiments/truncate_posts_2026_06_19/truncation_v4/generate_sample_flips.py
PYTHONPATH=. uv run python experiments/truncate_posts_2026_06_19/truncation_v4/generate_sample_flips.py --force
"""

from pathlib import Path

import pandas as pd
import typer
from langchain_aws import ChatBedrockConverse
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableConfig
from pydantic import BaseModel
from tqdm import tqdm

from experiments.scaled_mirrors_generation_2026_06_02.prompts import FLIP_PROMPT
from experiments.truncate_posts_2026_06_19.truncation_v3 import (
    MAX_CHARS,
    SENTENCE_OVERFLOW,
    truncate_social_post,
)
from lib.constants import BEDROCK_REGION, DEFAULT_BEDROCK_SONNET_MODEL

EXPERIMENT_DIR = Path(__file__).resolve().parent.parent
SAMPLE_FLIPS_CSV = EXPERIMENT_DIR / "outputs" / "truncation_v3" / "sample_flips.csv"
BASELINE_FLIPS_CSV = (
    EXPERIMENT_DIR
    / "outputs"
    / "truncation_v3"
    / "sample_new_flips_with_original_flips.csv"
)
OUTPUT_DIR = EXPERIMENT_DIR / "outputs" / "truncation_v4"
OUTPUT_CSV = OUTPUT_DIR / "sample_new_flips_with_original_flips.csv"

TOPIC_ALIGNMENT_INSTRUCTION = (
    "Keep the mirror on the same political topic/issue as the original and flip "
    "only the stance, not the subject — switch to a different issue only when "
    "the original's topic has no natural opposite-stance position."
)

FLIP_PROMPT_V4 = f"{FLIP_PROMPT}\n\n{TOPIC_ALIGNMENT_INSTRUCTION}"

BATCH_SIZE = 25
MAX_CONCURRENCY = 10

OUTPUT_COLUMNS = [
    "post_primary_key",
    "original_text",
    "sample_toxicity_type",
    "sampled_stance",
    "original_flip",
    "new_flip",
]

app = typer.Typer(add_completion=False)


class FlipResponse(BaseModel):
    flipped_text: str
    explanation: str


def get_llm(
    model: str = DEFAULT_BEDROCK_SONNET_MODEL,
    region_name: str = BEDROCK_REGION,
) -> ChatBedrockConverse:
    return ChatBedrockConverse(model=model, region_name=region_name)


def _build_prompt_template(*, topic_aligned: bool) -> ChatPromptTemplate:
    target_placeholder = "[SPECIFIC FIGURE/GROUP — e.g., Republicans/Democrats, Donald Trump/Joe Biden]"
    base_prompt = FLIP_PROMPT_V4 if topic_aligned else FLIP_PROMPT
    prompt_template = base_prompt.replace(target_placeholder, "{target_group}")
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


def _truncate_flip(text: str) -> str:
    return truncate_social_post(
        text,
        MAX_CHARS,
        sentence_overflow=SENTENCE_OVERFLOW,
    )


def _load_source_df(input_csv: Path, baseline_csv: Path) -> pd.DataFrame:
    source_df = pd.read_csv(input_csv)
    required_cols = [
        "post_primary_key",
        "original_text",
        "sample_toxicity_type",
        "sampled_stance",
    ]
    missing = [col for col in required_cols if col not in source_df.columns]
    if missing:
        raise KeyError(f"Missing required columns in {input_csv}: {missing}")

    source_df = source_df.copy()
    source_df["original_flip"] = pd.NA
    if baseline_csv.exists():
        baseline_df = pd.read_csv(baseline_csv)
        if "original_flip" in baseline_df.columns:
            baseline_map = baseline_df.set_index("post_primary_key")["original_flip"].astype(str)
            source_df["original_flip"] = source_df["post_primary_key"].map(baseline_map)

    return source_df


def _load_completed_keys(out_fp: Path) -> set[str]:
    if not out_fp.exists():
        return set()
    existing = pd.read_csv(out_fp, usecols=["post_primary_key"])
    return set(existing["post_primary_key"].astype(str))


def _append_rows(out_fp: Path, rows: list[dict[str, str]], *, write_header: bool) -> None:
    pd.DataFrame(rows, columns=OUTPUT_COLUMNS).to_csv(
        out_fp,
        mode="a",
        header=write_header,
        index=False,
    )


def _batch_inputs(batch: pd.DataFrame) -> list[dict[str, str]]:
    return [
        {
            "post_text": str(text),
            "target_group": _compute_target_group(str(stance)),
        }
        for text, stance in zip(
            batch["original_text"].tolist(),
            batch["sampled_stance"].tolist(),
        )
    ]


def generate_sample_flips(
    *,
    input_csv: Path | None = None,
    baseline_csv: Path | None = None,
    output_csv: Path | None = None,
    force: bool = False,
) -> pd.DataFrame:
    input_csv = input_csv or SAMPLE_FLIPS_CSV
    baseline_csv = baseline_csv or BASELINE_FLIPS_CSV
    output_csv = output_csv or OUTPUT_CSV

    if not input_csv.exists():
        raise FileNotFoundError(f"Missing v3 sample CSV: {input_csv}")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    if force and output_csv.exists():
        output_csv.unlink()

    source_df = _load_source_df(input_csv, baseline_csv)
    completed_keys = _load_completed_keys(output_csv)
    df = source_df[
        ~source_df["post_primary_key"].astype(str).isin(completed_keys)
    ].reset_index(drop=True)
    if completed_keys:
        print(
            f"Resuming: skipping {len(source_df) - len(df)} rows already in {output_csv}."
        )

    if df.empty:
        print(f"Nothing to do; {output_csv} already has all rows.")
        return pd.read_csv(output_csv)

    llm = get_llm()
    original_chain = _build_prompt_template(topic_aligned=False) | llm.with_structured_output(
        FlipResponse, method="json_schema"
    )
    topic_chain = _build_prompt_template(topic_aligned=True) | llm.with_structured_output(
        FlipResponse, method="json_schema"
    )

    write_header = not output_csv.exists()
    n = len(df)
    for start in tqdm(range(0, n, BATCH_SIZE), desc="Generating v4 flips", unit="batch"):
        batch = df.iloc[start : start + BATCH_SIZE].copy()
        missing_original = batch["original_flip"].isna()
        if missing_original.any():
            missing_batch = batch.loc[missing_original]
            original_results = original_chain.batch(
                _batch_inputs(missing_batch),
                config=RunnableConfig(max_concurrency=MAX_CONCURRENCY),
            )
            for idx, resp in zip(missing_batch.index, original_results, strict=True):
                batch.at[idx, "original_flip"] = resp.flipped_text

        topic_results = topic_chain.batch(
            _batch_inputs(batch),
            config=RunnableConfig(max_concurrency=MAX_CONCURRENCY),
        )

        batch_rows: list[dict[str, str]] = []
        for row_in, resp in zip(batch.itertuples(index=False), topic_results, strict=True):
            batch_rows.append(
                {
                    "post_primary_key": str(getattr(row_in, "post_primary_key")),
                    "original_text": str(getattr(row_in, "original_text")),
                    "sample_toxicity_type": str(getattr(row_in, "sample_toxicity_type")),
                    "sampled_stance": str(getattr(row_in, "sampled_stance")),
                    "original_flip": str(getattr(row_in, "original_flip")),
                    "new_flip": _truncate_flip(resp.flipped_text),
                }
            )

        _append_rows(output_csv, batch_rows, write_header=write_header)
        write_header = False

    result = pd.read_csv(output_csv)
    print(f"Wrote {len(df)} new rows to {output_csv} ({len(result)} total).")
    return result


@app.command()
def main(
    force: bool = typer.Option(
        False,
        "--force",
        help="Delete existing output and regenerate all rows.",
    ),
) -> None:
    generate_sample_flips(force=force)


if __name__ == "__main__":
    app()
