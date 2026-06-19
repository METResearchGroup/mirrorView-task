from __future__ import annotations

"""
Regenerate mirrored posts for v3 sample originals using the original FLIP_PROMPT.

Compares freshly generated flips against truncated v2 mirrors from sample_flips.csv.

Run from repo root:

PYTHONPATH=. uv run python experiments/truncate_posts_2026_06_19/regenerate_sample_flips.py
"""

from pathlib import Path

import pandas as pd
from langchain_aws import ChatBedrockConverse
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableConfig
from pydantic import BaseModel
from tqdm import tqdm

from experiments.scaled_mirrors_generation_2026_06_02.prompts import FLIP_PROMPT
from experiments.truncate_posts_2026_06_19.paths import (
    TruncationVersion,
    ensure_version_dir,
    sample_flips_csv,
    sample_new_flips_with_original_flips_csv,
)
from lib.constants import BEDROCK_REGION, DEFAULT_BEDROCK_SONNET_MODEL

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


def generate_sample_flips(
    *,
    v3_sample_csv: Path | None = None,
    v2_sample_csv: Path | None = None,
    output_csv: Path | None = None,
) -> pd.DataFrame:
    v3_sample_csv = v3_sample_csv or sample_flips_csv(TruncationVersion.v3)
    v2_sample_csv = v2_sample_csv or sample_flips_csv(TruncationVersion.v2)
    output_csv = output_csv or sample_new_flips_with_original_flips_csv()

    ensure_version_dir(TruncationVersion.v3)

    v3_df = pd.read_csv(v3_sample_csv)
    v2_df = pd.read_csv(v2_sample_csv)

    required_cols = [
        "post_primary_key",
        "original_text",
        "sample_toxicity_type",
        "sampled_stance",
        "mirrored_text",
    ]
    for label, df, path in [
        ("v3", v3_df, v3_sample_csv),
        ("v2", v2_df, v2_sample_csv),
    ]:
        missing = [col for col in required_cols if col not in df.columns]
        if missing:
            raise KeyError(f"Missing required columns in {label} sample {path}: {missing}")

    v2_mirrors = v2_df.set_index("post_primary_key")["mirrored_text"].astype(str)
    if not set(v3_df["post_primary_key"]).issubset(set(v2_mirrors.index)):
        missing_keys = set(v3_df["post_primary_key"]) - set(v2_mirrors.index)
        raise ValueError(f"v2 sample missing post_primary_key values: {sorted(missing_keys)}")

    completed_keys = _load_completed_keys(output_csv)
    df = v3_df[~v3_df["post_primary_key"].astype(str).isin(completed_keys)].reset_index(
        drop=True
    )
    if completed_keys:
        print(f"Resuming: skipping {len(v3_df) - len(df)} rows already in {output_csv}.")

    if df.empty:
        print(f"Nothing to do; {output_csv} already has all rows.")
        return pd.read_csv(output_csv)

    prompt = _build_prompt_template()
    llm = get_llm()
    structured = llm.with_structured_output(FlipResponse, method="json_schema")
    chain = prompt | structured

    write_header = not output_csv.exists()
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

        batch_rows: list[dict[str, str]] = []
        for row_in, resp in zip(batch.itertuples(index=False), results, strict=True):
            key = str(getattr(row_in, "post_primary_key"))
            batch_rows.append(
                {
                    "post_primary_key": key,
                    "original_text": str(getattr(row_in, "original_text")),
                    "sample_toxicity_type": str(getattr(row_in, "sample_toxicity_type")),
                    "sampled_stance": str(getattr(row_in, "sampled_stance")),
                    "original_flip": str(resp.flipped_text),
                    "new_flip": v2_mirrors.loc[key],
                }
            )

        _append_rows(output_csv, batch_rows, write_header=write_header)
        write_header = False

    result = pd.read_csv(output_csv)
    print(f"Wrote {len(df)} new rows to {output_csv} ({len(result)} total).")
    return result


def main() -> None:
    generate_sample_flips()


if __name__ == "__main__":
    main()
