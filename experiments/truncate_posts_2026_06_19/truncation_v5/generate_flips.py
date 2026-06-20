from __future__ import annotations

"""
Generate topic-aligned mirrored posts for the full combined flips dataset.

This is the v5 extension of the v4 prompt intervention:

    Keep the mirror on the same political topic/issue as the original and flip only
    the stance, not the subject — switch to a different issue only when the original's
    topic has no natural opposite-stance position.

Inputs
  - Default input CSV:
      experiments/scaled_mirrors_generation_2026_06_02/generated_flips/combined_flips/flips.csv
    Required columns:
      - post_primary_key
      - original_text
      - sample_toxicity_type
      - sampled_stance

Outputs
  - Append-only CSV written to:
      experiments/truncate_posts_2026_06_19/outputs/truncation_v5/flips.csv
    Columns:
      - post_primary_key
      - original_text
      - sample_toxicity_type
      - sampled_stance
      - raw_mirrored_text
      - processed_mirrored_text

Idempotency / retries
  - Resume-safe: on start, reads already-written post_primary_key values from the output
    CSV and skips them.
  - Append-only: writes new rows in batches; safe to rerun after interruption.

Run from repo root:

PYTHONPATH=. uv run python experiments/truncate_posts_2026_06_19/truncation_v5/generate_flips.py --max-posts 10 --force
"""

from dataclasses import dataclass
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

app = typer.Typer(add_completion=False)

EXPERIMENT_DIR = Path(__file__).resolve().parent.parent
OUTPUT_DIR = EXPERIMENT_DIR / "outputs" / "truncation_v5"
OUTPUT_CSV = OUTPUT_DIR / "flips.csv"

DEFAULT_INPUT_CSV = (
    EXPERIMENT_DIR.parent
    / "scaled_mirrors_generation_2026_06_02"
    / "generated_flips"
    / "combined_flips"
    / "flips.csv"
)

BATCH_SIZE = 25
MAX_CONCURRENCY = 10
CHUNK_SIZE = 2_000

TOPIC_ALIGNMENT_INSTRUCTION = (
    "Keep the mirror on the same political topic/issue as the original and flip "
    "only the stance, not the subject — switch to a different issue only when "
    "the original's topic has no natural opposite-stance position."
)

FLIP_PROMPT_V5 = f"{FLIP_PROMPT}\n\n{TOPIC_ALIGNMENT_INSTRUCTION}"

OUTPUT_COLUMNS = [
    "post_primary_key",
    "original_text",
    "sample_toxicity_type",
    "sampled_stance",
    "raw_mirrored_text",
    "processed_mirrored_text",
]


class FlipResponse(BaseModel):
    flipped_text: str
    explanation: str


@dataclass(frozen=True)
class InputRow:
    post_primary_key: str
    original_text: str
    sample_toxicity_type: str
    sampled_stance: str


def get_llm(
    model: str = DEFAULT_BEDROCK_SONNET_MODEL,
    region_name: str = BEDROCK_REGION,
) -> ChatBedrockConverse:
    return ChatBedrockConverse(model=model, region_name=region_name)


def _build_prompt_template() -> ChatPromptTemplate:
    target_placeholder = "[SPECIFIC FIGURE/GROUP — e.g., Republicans/Democrats, Donald Trump/Joe Biden]"
    prompt_template = FLIP_PROMPT_V5.replace(target_placeholder, "{target_group}")
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


def _process_mirror(text: str) -> str:
    return truncate_social_post(
        str(text),
        MAX_CHARS,
        sentence_overflow=SENTENCE_OVERFLOW,
    )


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


def _iter_input_rows(input_csv: Path) -> tuple[int | None, "pd.io.parsers.TextFileReader"]:
    # TextFileReader supports chunked iteration without loading the full CSV into memory.
    reader = pd.read_csv(input_csv, chunksize=CHUNK_SIZE)
    return None, reader


def _validate_input_cols(df: pd.DataFrame, *, input_csv: Path) -> None:
    required_input_cols = [
        "post_primary_key",
        "original_text",
        "sample_toxicity_type",
        "sampled_stance",
    ]
    missing_cols = [col for col in required_input_cols if col not in df.columns]
    if missing_cols:
        raise KeyError(f"Missing required columns in {input_csv}: {missing_cols}")


def generate_flips(
    *,
    input_csv: Path = DEFAULT_INPUT_CSV,
    output_csv: Path = OUTPUT_CSV,
    max_posts: int | None = None,
    force: bool = False,
) -> None:
    if not input_csv.exists():
        raise FileNotFoundError(f"Missing input CSV: {input_csv}")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    if force and output_csv.exists():
        output_csv.unlink()

    completed_keys = _load_completed_keys(output_csv)
    if completed_keys:
        print(f"Resuming: found {len(completed_keys)} completed rows in {output_csv}.")

    llm = get_llm()
    prompt = _build_prompt_template()
    structured = llm.with_structured_output(FlipResponse, method="json_schema")
    chain = prompt | structured

    write_header = not output_csv.exists()
    written = 0

    _, reader = _iter_input_rows(input_csv)
    pbar = tqdm(desc="Generating v5 flips", unit="post")
    buffered: list[InputRow] = []

    def flush_buffer(n_to_flush: int | None = None) -> None:
        nonlocal write_header, written, buffered, completed_keys
        if not buffered:
            return

        if n_to_flush is None or n_to_flush >= len(buffered):
            batch_rows = buffered
            buffered = []
        else:
            batch_rows = buffered[:n_to_flush]
            buffered = buffered[n_to_flush:]

        inputs = [
            {
                "post_text": row.original_text,
                "target_group": _compute_target_group(row.sampled_stance),
            }
            for row in batch_rows
        ]
        results = chain.batch(inputs, config=RunnableConfig(max_concurrency=MAX_CONCURRENCY))

        out_rows: list[dict[str, str]] = []
        for row_in, resp in zip(batch_rows, results, strict=True):
            out_rows.append(
                {
                    "post_primary_key": row_in.post_primary_key,
                    "original_text": row_in.original_text,
                    "sample_toxicity_type": row_in.sample_toxicity_type,
                    "sampled_stance": row_in.sampled_stance,
                    "raw_mirrored_text": str(resp.flipped_text),
                    "processed_mirrored_text": _process_mirror(resp.flipped_text),
                }
            )

        _append_rows(output_csv, out_rows, write_header=write_header)
        write_header = False
        for row in out_rows:
            completed_keys.add(str(row["post_primary_key"]))

        written += len(out_rows)
        pbar.update(len(out_rows))

    for chunk in reader:
        if chunk.empty:
            continue
        _validate_input_cols(chunk, input_csv=input_csv)

        # De-dupe within chunk to avoid repeated ids causing duplicate writes inside one run.
        chunk = chunk.drop_duplicates(subset=["post_primary_key"], keep="first")

        # Skip already written rows for idempotency.
        mask = ~chunk["post_primary_key"].astype(str).isin(completed_keys)
        chunk = chunk[mask]
        if chunk.empty:
            continue

        for row in chunk.itertuples(index=False):
            if max_posts is not None and written >= max_posts:
                # Do not flush remaining buffered work; we've hit the cap.
                pbar.close()
                print(
                    f"Reached max_posts={max_posts}. Wrote {written} rows to {output_csv}."
                )
                return

            buffered.append(
                InputRow(
                    post_primary_key=str(getattr(row, "post_primary_key")),
                    original_text=str(getattr(row, "original_text")),
                    sample_toxicity_type=str(getattr(row, "sample_toxicity_type")),
                    sampled_stance=str(getattr(row, "sampled_stance")),
                )
            )

            if max_posts is None:
                target_batch = BATCH_SIZE
            else:
                target_batch = min(BATCH_SIZE, max_posts - written)
            if target_batch <= 0:
                continue
            if len(buffered) >= target_batch:
                flush_buffer(target_batch)
                if max_posts is not None and written >= max_posts:
                    pbar.close()
                    print(
                        f"Reached max_posts={max_posts}. Wrote {written} rows to {output_csv}."
                    )
                    return

    if max_posts is not None and written < max_posts and buffered:
        flush_buffer(min(len(buffered), max_posts - written))
    else:
        flush_buffer()
    pbar.close()
    print(f"Done. Wrote {written} rows to {output_csv}.")


@app.command()
def main(
    input_csv: Path = typer.Option(
        DEFAULT_INPUT_CSV,
        "--input-csv",
        help="Source CSV of originals to mirror.",
    ),
    max_posts: int | None = typer.Option(
        None,
        "--max-posts",
        min=1,
        help="Write at most this many NEW rows (skips already-written keys).",
    ),
    force: bool = typer.Option(
        False,
        "--force",
        help="Delete the output CSV and regenerate from scratch.",
    ),
) -> None:
    generate_flips(input_csv=input_csv, max_posts=max_posts, force=force)


if __name__ == "__main__":
    app()

