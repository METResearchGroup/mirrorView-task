from __future__ import annotations

"""
Run from repo root:

PYTHONPATH=. uv run python experiments/scaled_mirrors_generation_2026_06_02/generate_flips.py
"""

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

CONCATENATED_RECORDS_DIR = EXPERIMENT_DIR / "concatenated_records"
GENERATED_FLIPS_DIR = EXPERIMENT_DIR / "generated_flips"

# Hard-coded generation settings. This script intentionally provides no CLI args.
BATCH_SIZE = 25
MAX_CONCURRENCY = 10

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


def _pick_latest_input_csv() -> Path:
    candidates = sorted(
        CONCATENATED_RECORDS_DIR.glob("*/records.csv"),
        key=lambda p: p.stat().st_mtime,
    )
    if not candidates:
        raise FileNotFoundError(
            f"No records CSVs found: {CONCATENATED_RECORDS_DIR / '*/records.csv'}"
        )
    return candidates[-1]


def _extract_input_timestamp(records_csv: Path) -> str:
    return records_csv.parent.name


def _build_prompt_template() -> ChatPromptTemplate:
    # Replace the bracket placeholder with a runtime template variable.
    target_placeholder = "[SPECIFIC FIGURE/GROUP — e.g., Republicans/Democrats, Donald Trump/Joe Biden]"
    prompt_template = FLIP_PROMPT.replace(target_placeholder, "{target_group}")
    # FLIP_PROMPT does not currently include the post text. Add it explicitly.
    prompt_template = prompt_template + "\n\nPost:\n{post_text}\n"
    return ChatPromptTemplate.from_messages([("human", prompt_template)])


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


def _compute_target_group(sampled_stance: str) -> str:
    # Deterministic minimal mapping that assumes stance labels are left/right.
    mapping = {
        "left": "right",
        "right": "left",
    }
    if sampled_stance not in mapping:
        raise ValueError(f"Unexpected sampled_stance `{sampled_stance}`.")
    return mapping[sampled_stance]


def main() -> None:
    input_csv = _pick_latest_input_csv()
    input_timestamp = _extract_input_timestamp(input_csv)
    out_dir = GENERATED_FLIPS_DIR / input_timestamp
    out_dir.mkdir(parents=True, exist_ok=True)
    out_fp = out_dir / "flips.csv"

    df = pd.read_csv(input_csv)

    required_input_cols = [
        "post_primary_key",
        "original_text",
        "sample_toxicity_type",
        "sampled_stance",
    ]
    missing_cols = [col for col in required_input_cols if col not in df.columns]
    if missing_cols:
        raise KeyError(f"Missing required columns in {input_csv}: {missing_cols}")

    completed_keys = _load_completed_keys(out_fp)
    if completed_keys:
        n_before = len(df)
        df = df[~df["post_primary_key"].astype(str).isin(completed_keys)].reset_index(drop=True)
        print(f"Resuming: skipping {n_before - len(df)} rows already in {out_fp}.")

    if df.empty:
        print(f"Nothing to do; {out_fp} already has all rows.")
        return

    prompt = _build_prompt_template()
    llm = get_llm()
    structured = llm.with_structured_output(FlipResponse, method="json_schema")
    chain = prompt | structured

    write_header = not out_fp.exists()
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

        # Batch call via LCEL.
        results = chain.batch(inputs, config=RunnableConfig(max_concurrency=MAX_CONCURRENCY))

        batch_rows: list[dict[str, str]] = []
        for row_in, resp in zip(batch.itertuples(index=False), results, strict=True):
            batch_rows.append(
                {
                    "post_primary_key": str(getattr(row_in, "post_primary_key")),
                    "original_text": str(getattr(row_in, "original_text")),
                    "sample_toxicity_type": str(getattr(row_in, "sample_toxicity_type")),
                    "sampled_stance": str(getattr(row_in, "sampled_stance")),
                    "mirrored_text": str(resp.flipped_text),
                }
            )

        _append_rows(out_fp, batch_rows, write_header=write_header)
        write_header = False

    total_rows = len(pd.read_csv(out_fp))
    print(f"Wrote {len(df)} new rows to {out_fp} ({total_rows} total).")


if __name__ == "__main__":
    main()
