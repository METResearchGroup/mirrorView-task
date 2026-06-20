from __future__ import annotations

import math
from dataclasses import dataclass, field
from enum import Enum
from typing import Callable

import pandas as pd
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableConfig
from pydantic import BaseModel
from tqdm import tqdm

from experiments.match_lengths_original_mirrors_2026_06_19.prompts import (
    CHAR_BOUNDS_SUFFIX,
    FLIP_PROMPT_PLAIN,
    FLIP_PROMPT_V2,
    LENGTH_REWRITE_PROMPT,
    SHORTEN_PROMPT,
)
from experiments.match_lengths_original_mirrors_2026_06_19.run_match_lengths import (
    LENGTH_DIFF_THRESHOLD,
    _compute_target_group,
    get_llm,
)
from experiments.scaled_mirrors_generation_2026_06_02.prompts import FLIP_PROMPT

MIN_MAX_TOKENS = 32
CHAR_BOUNDS_LO = 0.90
CHAR_BOUNDS_HI = 1.10


class OutputFormat(str, Enum):
    JSON_V1 = "json_v1"
    JSON_V2 = "json_v2"
    PLAIN = "plain"


class RetryMode(str, Enum):
    NONE = "none"
    RETIGHTEN_CAP = "retighten_cap"
    SHORTEN_PASS = "shorten_pass"


@dataclass(frozen=True)
class AblationConfig:
    ablation_id: str
    changes: str
    output_format: OutputFormat = OutputFormat.JSON_V2
    max_tokens_fn: Callable[[int], int | None] | None = None
    char_bounds: bool = False
    retry_mode: RetryMode = RetryMode.NONE
    two_pass: bool = False
    use_token_calibration: bool = False
    use_batch: bool = False


class FlipResponseV1(BaseModel):
    flipped_text: str
    explanation: str


class FlipResponseV2(BaseModel):
    flipped_text: str


def max_tokens_b0(t: int) -> int:
    return max(math.ceil(t * 1.05) + 20, MIN_MAX_TOKENS)


def max_tokens_b1(t: int) -> int:
    return max(t + 12, MIN_MAX_TOKENS)


def max_tokens_b2(t: int) -> int:
    return max(t + 8, MIN_MAX_TOKENS)


def max_tokens_b3(t: int) -> int:
    return max(math.ceil(t * 0.95) + 12, MIN_MAX_TOKENS)


def max_tokens_b4(t: int) -> int:
    return max(math.ceil(t * 1.00) + 16, MIN_MAX_TOKENS)


def max_tokens_retry(t: int) -> int:
    return max(t + 8, MIN_MAX_TOKENS)


ABLATION_CONFIGS: dict[str, AblationConfig] = {
    "A0": AblationConfig(
        ablation_id="A0",
        changes="v1 baseline: prompt length line only; JSON with explanation; no max_tokens; batched",
        output_format=OutputFormat.JSON_V1,
        use_batch=True,
    ),
    "B0": AblationConfig(
        ablation_id="B0",
        changes="v2 baseline: max_tokens = ceil(t×1.05)+20; JSON flipped_text only",
        max_tokens_fn=max_tokens_b0,
    ),
    "B1": AblationConfig(
        ablation_id="B1",
        changes="Tighter cap: max_tokens = t+12; JSON flipped_text only",
        max_tokens_fn=max_tokens_b1,
    ),
    "B2": AblationConfig(
        ablation_id="B2",
        changes="Minimal overhead: max_tokens = t+8; JSON flipped_text only",
        max_tokens_fn=max_tokens_b2,
    ),
    "B3": AblationConfig(
        ablation_id="B3",
        changes="Under-budget: max_tokens = ceil(t×0.95)+12; JSON flipped_text only",
        max_tokens_fn=max_tokens_b3,
    ),
    "B4": AblationConfig(
        ablation_id="B4",
        changes="Mid cap: max_tokens = ceil(t×1.00)+16; JSON flipped_text only",
        max_tokens_fn=max_tokens_b4,
    ),
    "C1": AblationConfig(
        ablation_id="C1",
        changes="Char bounds [0.9N, 1.1N] in prompt + max_tokens = t+12",
        max_tokens_fn=max_tokens_b1,
        char_bounds=True,
    ),
    "C2": AblationConfig(
        ablation_id="C2",
        changes="Char bounds [0.9N, 1.1N] in prompt; no max_tokens",
        char_bounds=True,
    ),
    "C3": AblationConfig(
        ablation_id="C3",
        changes="Char bounds [0.9N, 1.1N] in prompt + max_tokens = t+8",
        max_tokens_fn=max_tokens_b2,
        char_bounds=True,
    ),
    "D1": AblationConfig(
        ablation_id="D1",
        changes="max_tokens = t+12; retry with t+8 if mirror > 1.10× original chars",
        max_tokens_fn=max_tokens_b1,
        retry_mode=RetryMode.RETIGHTEN_CAP,
    ),
    "D2": AblationConfig(
        ablation_id="D2",
        changes="max_tokens = t+12; second shorten pass if mirror > 1.10× original chars",
        max_tokens_fn=max_tokens_b1,
        retry_mode=RetryMode.SHORTEN_PASS,
    ),
    "E1": AblationConfig(
        ablation_id="E1",
        changes="Plain text output + max_tokens = t+12",
        output_format=OutputFormat.PLAIN,
        max_tokens_fn=max_tokens_b1,
    ),
    "E2": AblationConfig(
        ablation_id="E2",
        changes="Plain text output + char bounds + max_tokens = t+12",
        output_format=OutputFormat.PLAIN,
        max_tokens_fn=max_tokens_b1,
        char_bounds=True,
    ),
    "F1": AblationConfig(
        ablation_id="F1",
        changes="Two-pass: initial flip (t+12), then length rewrite to char bounds",
        max_tokens_fn=max_tokens_b1,
        two_pass=True,
    ),
    "G1": AblationConfig(
        ablation_id="G1",
        changes="Calibrated token estimate from Bedrock usage + max_tokens = cal(t)+12",
        max_tokens_fn=max_tokens_b1,
        use_token_calibration=True,
    ),
}


def _char_bounds(char_count: int) -> tuple[int, int]:
    return math.floor(char_count * CHAR_BOUNDS_LO), math.ceil(char_count * CHAR_BOUNDS_HI)


def _base_prompt_text(output_format: OutputFormat, *, char_bounds: bool) -> str:
    if output_format == OutputFormat.JSON_V1:
        prompt = FLIP_PROMPT
    elif output_format == OutputFormat.JSON_V2:
        prompt = FLIP_PROMPT_V2
    else:
        prompt = FLIP_PROMPT_PLAIN

    target_placeholder = "[SPECIFIC FIGURE/GROUP — e.g., Republicans/Democrats, Donald Trump/Joe Biden]"
    prompt = prompt.replace(target_placeholder, "{target_group}")
    if char_bounds:
        prompt = prompt + "\n\n" + CHAR_BOUNDS_SUFFIX
    prompt = prompt + "\n\nPost:\n{post_text}\n"
    return prompt


def _build_flip_chain(base_llm, config: AblationConfig, *, max_tokens: int | None):
    prompt_text = _base_prompt_text(config.output_format, char_bounds=config.char_bounds)
    variables = ["target_group", "post_text"]
    if config.char_bounds:
        variables.extend(["char_count", "char_lo", "char_hi"])
    prompt = ChatPromptTemplate.from_messages([("human", prompt_text)])

    llm = base_llm if max_tokens is None else base_llm.bind(max_tokens=max_tokens)
    if config.output_format == OutputFormat.PLAIN:
        return prompt | llm, variables

    response_model = FlipResponseV1 if config.output_format == OutputFormat.JSON_V1 else FlipResponseV2
    structured = llm.with_structured_output(response_model, method="json_schema")
    return prompt | structured, variables


def _invoke_inputs(
    post_text: str,
    stance: str,
    *,
    char_bounds: bool,
) -> dict[str, str | int]:
    char_count = len(post_text)
    inputs: dict[str, str | int] = {
        "post_text": post_text,
        "target_group": _compute_target_group(stance),
    }
    if char_bounds:
        lo, hi = _char_bounds(char_count)
        inputs.update({"char_count": char_count, "char_lo": lo, "char_hi": hi})
    return inputs


def _extract_mirror_text(resp, config: AblationConfig) -> str:
    if config.output_format == OutputFormat.PLAIN:
        return str(resp.content).strip()
    return str(resp.flipped_text).strip()


def _compute_budget_tokens(
    post_text: str,
    base_llm,
    config: AblationConfig,
    *,
    token_calibration_factor: float,
    override_fn: Callable[[int], int | None] | None = None,
) -> int | None:
    fn = override_fn or config.max_tokens_fn
    if fn is None:
        return None
    raw_tokens = base_llm.get_num_tokens(post_text)
    if config.use_token_calibration:
        # Convert LangChain token estimate into Bedrock output-token scale.
        raw_tokens = max(1, math.ceil(raw_tokens * token_calibration_factor))
    return fn(raw_tokens)


def _calibrate_token_factor(base_llm, df: pd.DataFrame, *, n_calibrate: int = 5) -> float:
    """Map LangChain post token estimates to Bedrock output tokens (median ratio)."""
    ratios: list[float] = []
    prompt_text = _base_prompt_text(OutputFormat.JSON_V2, char_bounds=False)
    prompt = ChatPromptTemplate.from_messages([("human", prompt_text)])

    for row in df.head(n_calibrate).itertuples(index=False):
        post_text = str(row.original_text)
        est = base_llm.get_num_tokens(post_text)
        if est <= 0:
            continue
        rendered = prompt.invoke(
            _invoke_inputs(post_text, str(row.sampled_stance), char_bounds=False)
        )
        resp = base_llm.invoke(rendered)
        usage = getattr(resp, "usage_metadata", None) or {}
        actual_out = int(usage.get("output_tokens", 0) or 0)
        if actual_out > 0 and est > 0:
            ratios.append(actual_out / est)

    if not ratios:
        return 1.0
    return sum(ratios) / len(ratios)


def _shorten_mirror(
    base_llm,
    *,
    original_text: str,
    mirrored_text: str,
    char_limit: int,
    max_tokens: int | None,
) -> str:
    prompt = ChatPromptTemplate.from_messages([("human", SHORTEN_PROMPT)])
    llm = base_llm if max_tokens is None else base_llm.bind(max_tokens=max_tokens)
    chain = prompt | llm
    resp = chain.invoke(
        {
            "char_limit": char_limit,
            "original_char_count": len(original_text),
            "original_text": original_text,
            "current_char_count": len(mirrored_text),
            "mirrored_text": mirrored_text,
        }
    )
    return str(resp.content).strip()


def _rewrite_for_length(base_llm, *, original_text: str, mirrored_text: str, max_tokens: int | None) -> str:
    char_count = len(original_text)
    lo, hi = _char_bounds(char_count)
    prompt = ChatPromptTemplate.from_messages([("human", LENGTH_REWRITE_PROMPT)])
    llm = base_llm if max_tokens is None else base_llm.bind(max_tokens=max_tokens)
    structured = llm.with_structured_output(FlipResponseV2, method="json_schema")
    chain = prompt | structured
    resp = chain.invoke(
        {
            "char_lo": lo,
            "char_hi": hi,
            "original_char_count": char_count,
            "original_text": original_text,
            "current_char_count": len(mirrored_text),
            "mirrored_text": mirrored_text,
        }
    )
    return str(resp.flipped_text).strip()


def _generate_one(
    row,
    base_llm,
    config: AblationConfig,
    *,
    token_calibration_factor: float,
) -> dict:
    post_text = str(row.original_text)
    stance = str(row.sampled_stance)
    input_tokens = base_llm.get_num_tokens(post_text)
    max_tokens = _compute_budget_tokens(
        post_text,
        base_llm,
        config,
        token_calibration_factor=token_calibration_factor,
    )

    chain, _ = _build_flip_chain(base_llm, config, max_tokens=max_tokens)
    resp = chain.invoke(_invoke_inputs(post_text, stance, char_bounds=config.char_bounds))
    mirrored_text = _extract_mirror_text(resp, config)
    n_attempts = 1
    retried = False

    if config.two_pass and mirrored_text:
        rewrite_cap = _compute_budget_tokens(
            post_text,
            base_llm,
            config,
            token_calibration_factor=token_calibration_factor,
        )
        mirrored_text = _rewrite_for_length(
            base_llm,
            original_text=post_text,
            mirrored_text=mirrored_text,
            max_tokens=rewrite_cap,
        )
        n_attempts = 2

    elif config.retry_mode != RetryMode.NONE and mirrored_text:
        char_limit = math.ceil(len(post_text) * CHAR_BOUNDS_HI)
        if len(mirrored_text) > char_limit:
            retried = True
            n_attempts = 2
            if config.retry_mode == RetryMode.RETIGHTEN_CAP:
                retry_cap = _compute_budget_tokens(
                    post_text,
                    base_llm,
                    config,
                    token_calibration_factor=token_calibration_factor,
                    override_fn=max_tokens_retry,
                )
                chain, _ = _build_flip_chain(base_llm, config, max_tokens=retry_cap)
                resp = chain.invoke(
                    _invoke_inputs(post_text, stance, char_bounds=config.char_bounds)
                )
                mirrored_text = _extract_mirror_text(resp, config)
            else:
                retry_cap = _compute_budget_tokens(
                    post_text,
                    base_llm,
                    config,
                    token_calibration_factor=token_calibration_factor,
                )
                mirrored_text = _shorten_mirror(
                    base_llm,
                    original_text=post_text,
                    mirrored_text=mirrored_text,
                    char_limit=char_limit,
                    max_tokens=retry_cap,
                )

    parse_failed = not mirrored_text
    return {
        "post_primary_key": str(row.post_primary_key),
        "original_text": post_text,
        "sample_toxicity_type": str(row.sample_toxicity_type),
        "sampled_stance": stance,
        "mirrored_text": mirrored_text,
        "original_token_count": input_tokens,
        "max_output_tokens": max_tokens if max_tokens is not None else "",
        "n_attempts": n_attempts,
        "retried": retried,
        "parse_failed": parse_failed,
    }


def _generate_batch(df: pd.DataFrame, config: AblationConfig) -> pd.DataFrame:
    base_llm = get_llm()
    prompt_text = _base_prompt_text(config.output_format, char_bounds=config.char_bounds)
    prompt = ChatPromptTemplate.from_messages([("human", prompt_text)])
    structured = base_llm.with_structured_output(FlipResponseV1, method="json_schema")
    chain = prompt | structured

    rows: list[dict] = []
    batch_size = 25
    for start in tqdm(range(0, len(df), batch_size), desc=config.ablation_id, unit="batch"):
        batch = df.iloc[start : start + batch_size]
        inputs = [
            _invoke_inputs(str(r.original_text), str(r.sampled_stance), char_bounds=config.char_bounds)
            for r in batch.itertuples(index=False)
        ]
        results = chain.batch(inputs, config=RunnableConfig(max_concurrency=10))
        for row_in, resp in zip(batch.itertuples(index=False), results, strict=True):
            mirrored_text = str(resp.flipped_text).strip()
            rows.append(
                {
                    "post_primary_key": str(row_in.post_primary_key),
                    "original_text": str(row_in.original_text),
                    "sample_toxicity_type": str(row_in.sample_toxicity_type),
                    "sampled_stance": str(row_in.sampled_stance),
                    "mirrored_text": mirrored_text,
                    "original_token_count": base_llm.get_num_tokens(str(row_in.original_text)),
                    "max_output_tokens": "",
                    "n_attempts": 1,
                    "retried": False,
                    "parse_failed": not mirrored_text,
                }
            )
    return pd.DataFrame(rows)


def generate_ablation(df: pd.DataFrame, config: AblationConfig) -> pd.DataFrame:
    if config.use_batch:
        return _generate_batch(df, config)

    base_llm = get_llm()
    token_calibration_factor = 1.0
    if config.use_token_calibration:
        token_calibration_factor = _calibrate_token_factor(base_llm, df)

    rows: list[dict] = []
    for row in tqdm(df.itertuples(index=False), total=len(df), desc=config.ablation_id):
        rows.append(
            _generate_one(
                row,
                base_llm,
                config,
                token_calibration_factor=token_calibration_factor,
            )
        )
    return pd.DataFrame(rows)


@dataclass
class AblationMetrics:
    n_posts: int
    char_fail_pct: float
    token_fail_pct: float
    too_long_char_pct: float
    too_short_char_pct: float
    avg_orig_chars: float
    avg_mirr_chars: float
    avg_orig_tokens: float
    avg_mirr_tokens: float
    parse_fail_pct: float
    retry_pct: float
    mean_abs_char_rel_diff: float

    def summary(self) -> str:
        return (
            f"char_fail={self.char_fail_pct:.1%}, token_fail={self.token_fail_pct:.1%}, "
            f"too_long={self.too_long_char_pct:.1%}, too_short={self.too_short_char_pct:.1%}, "
            f"parse_fail={self.parse_fail_pct:.1%}, avg_chars={self.avg_mirr_chars:.0f}/{self.avg_orig_chars:.0f}"
        )


def compute_metrics(df: pd.DataFrame) -> AblationMetrics:
    llm = get_llm()
    original_chars = df["original_text"].fillna("").astype(str).str.len()
    mirrored_chars = df["mirrored_text"].fillna("").astype(str).str.len()
    original_tokens = df["original_text"].fillna("").astype(str).map(llm.get_num_tokens)
    mirrored_tokens = df["mirrored_text"].fillna("").astype(str).map(llm.get_num_tokens)

    nonzero = original_chars > 0
    char_rel = (mirrored_chars - original_chars).abs() / original_chars
    token_rel = (mirrored_tokens - original_tokens).abs() / original_tokens

    n = len(df)
    parse_fail = df.get("parse_failed", pd.Series([False] * n)).fillna(False).astype(bool)

    return AblationMetrics(
        n_posts=n,
        char_fail_pct=float((nonzero & (char_rel >= LENGTH_DIFF_THRESHOLD)).mean()),
        token_fail_pct=float((nonzero & (token_rel >= LENGTH_DIFF_THRESHOLD)).mean()),
        too_long_char_pct=float((nonzero & (mirrored_chars > original_chars * (1 + LENGTH_DIFF_THRESHOLD))).mean()),
        too_short_char_pct=float((nonzero & (mirrored_chars < original_chars * (1 - LENGTH_DIFF_THRESHOLD))).mean()),
        avg_orig_chars=float(original_chars.mean()),
        avg_mirr_chars=float(mirrored_chars.mean()),
        avg_orig_tokens=float(original_tokens.mean()),
        avg_mirr_tokens=float(mirrored_tokens.mean()),
        parse_fail_pct=float(parse_fail.mean()),
        retry_pct=float(df.get("retried", pd.Series([False] * n)).fillna(False).astype(bool).mean()),
        mean_abs_char_rel_diff=float(char_rel[nonzero].mean()) if nonzero.any() else 0.0,
    )
