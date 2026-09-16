"""Score thinking traces and write RESULTS.md.

Run from the repo root:

    PYTHONPATH=. uv run python experiments/reasoning_during_moderation_2026_09_15/experiment4/run.py
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from experiments.reasoning_during_moderation_2026_09_15.experiment1.run import (
    _read_jsonl,
)
from experiments.reasoning_during_moderation_2026_09_15.experiment3.run import (
    EXPERIMENT3_S3_KEY,
)
from experiments.reasoning_during_moderation_2026_09_15.experiment4.summarize import (
    group_contrasts,
    marker_item_rates,
    marker_rates,
    paired_arm_comparison,
    phrase_marker_rates,
    strict_marker_rates,
)
from experiments.reasoning_during_moderation_2026_09_15.shared.artifacts import (
    download_if_missing,
    upload_under_prefix,
)
from experiments.reasoning_during_moderation_2026_09_15.shared.constants import (
    COHORT_OUTPUT_DIR,
    DEEPSEEK_MODEL_ID,
    EXPERIMENT_DIR,
    EXPERIMENT_S3_PREFIX,
    GROUP_SPLIT,
    GROUP_UNANIMOUS_KEEP,
    GROUP_UNANIMOUS_REMOVE,
    METADATA_FILENAME,
    METADATA_S3_KEY,
    QWEN_MODEL_ID,
    VLLM_OUTPUT_DIRNAME,
)
from lib.constants import REPO_ROOT

MARKER_RATES_FILENAME = "marker_rates.csv"
STRICT_MARKER_RATES_FILENAME = "strict_marker_rates.csv"
PHRASE_MARKER_RATES_FILENAME = "phrase_marker_rates.csv"
ITEM_RATES_FILENAME = "marker_item_rates.csv"
GROUP_CONTRASTS_FILENAME = "group_contrasts.csv"
ARM_COMPARISON_FILENAME = "arm_comparison.csv"
TOKEN_SUMMARY_FILENAME = "token_summary.csv"
RESPONSE_TIME_SUMMARY_FILENAME = "response_time_summary.csv"
RESULTS_FILENAME = "RESULTS.md"
EXPERIMENT4_OUTPUT_DIR = EXPERIMENT_DIR / "experiment4" / "outputs"
EXPERIMENT4_S3_PREFIX = f"{EXPERIMENT_S3_PREFIX}/experiment4/"
MISSING_TABLE_NOTE = "_No rows. GPU traces were not present in this environment._"
NO_HIGH_ITEMS_NOTE = "_No marker item has a pooled rate at or above 0.05._"
HUMAN_TIME_NOTE = "Values are milliseconds."
BROAD_MARKER_NOTE = (
    "Broad rates count any confirmed phrase or token. Qwen values near 1.0 are a "
    "length and lexicon ceiling, because `wait`, `however`, and `both posts` fire "
    "on almost every long span. Do not treat those rates as a group contrast."
)
STRICT_MARKER_NOTE = (
    "Strict rates drop generic chain-of-thought tokens (`however`, `maybe`, `wait`, "
    "`actually`, `instead`, `perhaps`, `probably`, `possibly`) and prompt-echo items "
    "(`both posts`, `opposite`). Density is the number of distinct strict items per "
    "1,000 thinking tokens."
)
PHRASE_MARKER_NOTE = (
    "Phrase-only rates ignore bag-of-words tokens. Tension phrase rates stay high "
    "when `both posts` is common, because that phrase is in the prompt."
)
CONTRAST_NOTE = (
    "Split minus keep and split minus remove on the strict rates and densities. "
    "Rate is the share of valid traces. Density is distinct strict item hits per "
    "1,000 thinking tokens."
)
ITEM_RATE_NOTE = (
    "Item rates are the share of valid traces containing that phrase or token. "
    "Rows below are model-level (groups pooled) for items at or above 0.05."
)
HIGH_ITEM_RATE = 0.05
EMPTY_GPU_CLOSER = (
    "Human `response_time_ms` is in the experiment 3 table. Thinking-token counts "
    "and marker rates were not measured, because this environment had no GPU traces. "
    "F1 and accuracy are out of scope."
)
PENDING_EXP2_CLOSER = (
    "Experiment 4 marker rates use experiment 1 traces. "
    "The paired experiment 1 versus experiment 2 comparison waits on experiment 2 traces. "
    "F1 and accuracy were not measured."
)
ZERO_DIFF = 0.0
TOKEN_GROUPS = (GROUP_SPLIT, GROUP_UNANIMOUS_KEEP, GROUP_UNANIMOUS_REMOVE)
LONGER_LABEL = "higher"
NOT_LONGER_LABEL = "not higher"


def trace_jsonl_path(output_dir: Path, model_id: str) -> Path:
    """Return the vLLM jsonl path for one model under an experiment output dir."""
    name = "qwen" if model_id == QWEN_MODEL_ID else "deepseek"
    return output_dir / VLLM_OUTPUT_DIRNAME / f"traces_{name}.jsonl"


def traces_are_complete(traces: pd.DataFrame, expected_posts: int) -> bool:
    """True when both models have at least expected_posts unique post ids."""
    if expected_posts <= 0 or traces.empty:
        return False
    if "model_id" not in traces.columns or "post_id" not in traces.columns:
        return False
    for model_id in (QWEN_MODEL_ID, DEEPSEEK_MODEL_ID):
        n_posts = traces.loc[traces["model_id"] == model_id, "post_id"].nunique()
        if int(n_posts) < expected_posts:
            return False
    return True


def results_closer(rates: pd.DataFrame, comparison: pd.DataFrame) -> str:
    """Return the RESULTS.md closing paragraph for the current trace set."""
    if not comparison.empty:
        statements = [_diff_sentence(row) for _, row in comparison.iterrows()]
        return " ".join(statements) + " F1 and accuracy were not measured."
    if not rates.empty:
        return PENDING_EXP2_CLOSER
    return EMPTY_GPU_CLOSER


def main() -> None:
    rates_path, comparison_path = _write_outputs()
    print("wrote_results=true")
    print(f"marker_rates={rates_path}")
    print(f"arm_comparison={comparison_path}")


def _write_outputs() -> tuple[Path, Path]:
    exp1 = _load_experiment_traces(EXPERIMENT_DIR / "experiment1" / "outputs")
    exp2_raw = _load_experiment_traces(EXPERIMENT_DIR / "experiment2" / "outputs")
    expected_posts = int(exp1["post_id"].nunique()) if not exp1.empty else 0
    exp2 = (
        exp2_raw
        if traces_are_complete(exp2_raw, expected_posts)
        else pd.DataFrame()
    )
    traces = pd.concat([exp1, exp2], ignore_index=True)
    rates = marker_rates(traces)
    strict = strict_marker_rates(traces)
    phrases = phrase_marker_rates(traces)
    items = marker_item_rates(traces)
    contrasts = group_contrasts(strict)
    comparison = paired_arm_comparison(exp1, exp2)
    rates_path = _write_csv(rates, MARKER_RATES_FILENAME)
    strict_path = _write_csv(strict, STRICT_MARKER_RATES_FILENAME)
    phrase_path = _write_csv(phrases, PHRASE_MARKER_RATES_FILENAME)
    items_path = _write_csv(items, ITEM_RATES_FILENAME)
    contrast_path = _write_csv(contrasts, GROUP_CONTRASTS_FILENAME)
    comparison_path = _write_csv(comparison, ARM_COMPARISON_FILENAME)
    _write_results(rates, strict, phrases, items, contrasts, comparison)
    _upload_output(rates_path)
    _upload_output(strict_path)
    _upload_output(phrase_path)
    _upload_output(items_path)
    _upload_output(contrast_path)
    _upload_output(comparison_path)
    return rates_path, comparison_path


def _load_experiment_traces(output_dir: Path) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for model_id in (QWEN_MODEL_ID, DEEPSEEK_MODEL_ID):
        path = trace_jsonl_path(output_dir, model_id)
        _download_optional(path)
        if path.is_file():
            rows.extend(_read_jsonl(path))
    return pd.DataFrame(rows)


def _download_optional(path: Path) -> None:
    if path.is_file():
        return
    try:
        download_if_missing(path, str(path.relative_to(REPO_ROOT)))
    except FileNotFoundError:
        return


def _write_csv(frame: pd.DataFrame, filename: str) -> Path:
    path = EXPERIMENT4_OUTPUT_DIR / filename
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(path, index=False)
    return path


def _write_results(
    rates: pd.DataFrame,
    strict: pd.DataFrame,
    phrases: pd.DataFrame,
    items: pd.DataFrame,
    contrasts: pd.DataFrame,
    comparison: pd.DataFrame,
) -> None:
    metadata = _load_metadata()
    exp1 = _read_csv_or_empty(
        EXPERIMENT_DIR / "experiment1" / "outputs" / TOKEN_SUMMARY_FILENAME
    )
    exp2 = _read_csv_or_empty(
        EXPERIMENT_DIR / "experiment2" / "outputs" / TOKEN_SUMMARY_FILENAME
    )
    exp3 = _read_experiment3_summary()
    text = _results_markdown(
        metadata,
        exp1,
        exp2,
        exp3,
        rates,
        strict,
        phrases,
        items,
        contrasts,
        comparison,
    )
    (EXPERIMENT_DIR / RESULTS_FILENAME).write_text(text)


def _load_metadata() -> dict[str, object]:
    path = COHORT_OUTPUT_DIR / METADATA_FILENAME
    _download_optional_key(path, METADATA_S3_KEY)
    if not path.is_file():
        return {}
    return json.loads(path.read_text())


def _download_optional_key(path: Path, key: str) -> None:
    if path.is_file():
        return
    try:
        download_if_missing(path, key)
    except FileNotFoundError:
        return


def _read_csv_or_empty(path: Path) -> pd.DataFrame:
    _download_optional(path)
    if not path.is_file():
        return pd.DataFrame()
    return pd.read_csv(path)


def _results_markdown(
    metadata: dict[str, object],
    exp1: pd.DataFrame,
    exp2: pd.DataFrame,
    exp3: pd.DataFrame,
    rates: pd.DataFrame,
    strict: pd.DataFrame,
    phrases: pd.DataFrame,
    items: pd.DataFrame,
    contrasts: pd.DataFrame,
    comparison: pd.DataFrame,
) -> str:
    parts = [
        "# Reasoning tokens on split versus unanimous moderation posts",
        "",
        _metadata_block(metadata),
        "",
        *_section("Experiment 1", exp1),
        _token_finding(exp1),
        "",
        *_section("Experiment 2", exp2),
        *_section("Experiment 3", exp3, HUMAN_TIME_NOTE),
        "## Experiment 4",
        "",
        *_experiment4_body(rates, strict, phrases, items, contrasts, comparison),
        "",
        _strict_finding(strict),
        "",
        _phrase_finding(phrases),
        "",
        results_closer(rates, comparison),
        "",
    ]
    return "\n".join(parts)


def _section(title: str, frame: pd.DataFrame, note: str = "") -> list[str]:
    extra = [note, ""] if note else []
    return [f"## {title}", "", *extra, _markdown_table(frame), ""]


def _experiment4_body(
    rates: pd.DataFrame,
    strict: pd.DataFrame,
    phrases: pd.DataFrame,
    items: pd.DataFrame,
    contrasts: pd.DataFrame,
    comparison: pd.DataFrame,
) -> list[str]:
    if rates.empty and strict.empty and comparison.empty:
        return [MISSING_TABLE_NOTE]
    high = _pooled_high_items(items)
    high_table = _markdown_table(high) if not high.empty else NO_HIGH_ITEMS_NOTE
    return [
        "Broad family rates:",
        "",
        BROAD_MARKER_NOTE,
        "",
        _markdown_table(rates),
        "",
        "Strict family rates:",
        "",
        STRICT_MARKER_NOTE,
        "",
        _markdown_table(strict),
        "",
        "Phrase-only family rates:",
        "",
        PHRASE_MARKER_NOTE,
        "",
        _markdown_table(phrases),
        "",
        "Strict group contrasts:",
        "",
        CONTRAST_NOTE,
        "",
        _markdown_table(contrasts),
        "",
        "High-frequency marker items:",
        "",
        ITEM_RATE_NOTE,
        "",
        high_table,
        "",
        "Paired experiment 1 versus experiment 2:",
        "",
        _markdown_table(comparison),
    ]


def _metadata_block(metadata: dict[str, object]) -> str:
    since_date = metadata.get("since_date", "unknown")
    csv_files = metadata.get("csv_files", "unknown")
    split = metadata.get("split", "unknown")
    keep = metadata.get("unanimous_keep", "unknown")
    remove = metadata.get("unanimous_remove", "unknown")
    return (
        f"Export `since_date={since_date}`, `csv_files={csv_files}`, "
        f"`split={split}`, `unanimous_keep={keep}`, `unanimous_remove={remove}`."
    )


def _markdown_table(frame: pd.DataFrame) -> str:
    if frame.empty:
        return MISSING_TABLE_NOTE
    columns = [str(column) for column in frame.columns]
    header = "| " + " | ".join(columns) + " |"
    separator = "| " + " | ".join("---" for _unused in columns) + " |"
    rows = [_markdown_row(frame, index, columns) for index in range(len(frame))]
    return "\n".join([header, separator, *rows])


def _markdown_row(frame: pd.DataFrame, index: int, columns: list[str]) -> str:
    cells = [_format_cell(frame.iloc[index][column]) for column in columns]
    return "| " + " | ".join(cells) + " |"


def _format_cell(value: object) -> str:
    if isinstance(value, float):
        return f"{value:.4f}"
    return str(value)


def _read_experiment3_summary() -> pd.DataFrame:
    path = EXPERIMENT_DIR / "experiment3" / "outputs" / RESPONSE_TIME_SUMMARY_FILENAME
    _download_optional_key(path, EXPERIMENT3_S3_KEY)
    if not path.is_file():
        return pd.DataFrame()
    return pd.read_csv(path)


def _diff_sentence(row: pd.Series) -> str:
    diff = float(row["mean_thinking_token_diff"])
    direction = "lower" if diff < ZERO_DIFF else "not lower"
    return (
        f"{row['model_id']} {row['group']}: experiment 2 thinking-token mean is "
        f"{direction} than experiment 1 (diff={diff:.3f})."
    )


def _token_finding(exp1: pd.DataFrame) -> str:
    """Return the experiment 1 length finding from the token-summary table."""
    if exp1.empty:
        return ""
    model_sentences: list[str] = []
    split_higher: list[bool] = []
    for model_id, subset in exp1.groupby("model_id", sort=False):
        sentence, is_higher = _token_model_sentence(str(model_id), subset)
        if not sentence:
            continue
        model_sentences.append(sentence)
        split_higher.append(is_higher)
    if not model_sentences:
        return ""
    if split_higher and not any(split_higher):
        opener = (
            "Split posts do not have a higher mean thinking-token count than "
            "unanimous keep posts on these traces."
        )
        return " ".join([opener, *model_sentences])
    return " ".join(model_sentences)


def _token_model_sentence(model_id: str, subset: pd.DataFrame) -> tuple[str, bool]:
    means = _group_float_map(subset, "mean")
    if any(group not in means for group in TOKEN_GROUPS):
        return "", False
    split_mean = means[GROUP_SPLIT]
    keep_mean = means[GROUP_UNANIMOUS_KEEP]
    remove_mean = means[GROUP_UNANIMOUS_REMOVE]
    is_higher = split_mean > keep_mean
    relation = LONGER_LABEL if is_higher else NOT_LONGER_LABEL
    longest = max(means, key=means.get)
    shortest = min(means, key=means.get)
    n_clause = ""
    if "n_valid" in subset.columns:
        n_map = _group_float_map(subset, "n_valid")
        n_clause = (
            f" n_valid is {int(n_map[GROUP_SPLIT])} split, "
            f"{int(n_map[GROUP_UNANIMOUS_KEEP])} keep, and "
            f"{int(n_map[GROUP_UNANIMOUS_REMOVE])} remove."
        )
    sentence = (
        f"{model_id} split is {relation} than keep "
        f"(split={split_mean:.1f}, keep={keep_mean:.1f}, remove={remove_mean:.1f}). "
        f"The longest group is {longest}, and the shortest is {shortest}.{n_clause}"
    )
    return sentence, is_higher


def _strict_finding(strict: pd.DataFrame) -> str:
    """Return the experiment 4 finding from the strict rate table."""
    if strict.empty:
        return ""
    parts = [
        "Broad family rates sit near 1.0 on Qwen, so they do not distinguish groups. "
        "Those rates fire because `wait`, `however`, and `both posts` appear in "
        "almost every long thinking span. The statements below use the strict rates, "
        "which drop those generic tokens and the prompt-echo items."
    ]
    for model_id, subset in strict.groupby("model_id", sort=False):
        sentence = _strict_model_sentence(str(model_id), subset)
        if sentence:
            parts.append(sentence)
    parts.append(
        "If uncertainty density is close across groups, a higher rate means a "
        "larger share of traces contain at least one strict item, not more "
        "uncertainty language per token."
    )
    return " ".join(parts)


def _strict_model_sentence(model_id: str, subset: pd.DataFrame) -> str:
    by_group = {str(row["group"]): row for _, row in subset.iterrows()}
    if any(group not in by_group for group in TOKEN_GROUPS):
        return ""
    split = by_group[GROUP_SPLIT]
    keep = by_group[GROUP_UNANIMOUS_KEEP]
    remove = by_group[GROUP_UNANIMOUS_REMOVE]
    u_split = float(split["uncertainty_rate"])
    u_keep = float(keep["uncertainty_rate"])
    u_remove = float(remove["uncertainty_rate"])
    r_split = float(split["revision_rate"])
    r_keep = float(keep["revision_rate"])
    r_remove = float(remove["revision_rate"])
    t_split = float(split["tension_rate"])
    t_keep = float(keep["tension_rate"])
    t_remove = float(remove["tension_rate"])
    d_split = float(split["uncertainty_density"])
    d_keep = float(keep["uncertainty_density"])
    d_remove = float(remove["uncertainty_density"])
    return (
        f"{model_id}: strict uncertainty rates are {u_split:.3f} on split, "
        f"{u_keep:.3f} on keep, and {u_remove:.3f} on remove "
        f"(split minus keep {u_split - u_keep:+.3f}). "
        f"Strict revision rates are {r_split:.3f}, {r_keep:.3f}, and {r_remove:.3f}. "
        f"Strict tension rates are {t_split:.3f}, {t_keep:.3f}, and {t_remove:.3f}. "
        f"Uncertainty density is {d_split:.3f}, {d_keep:.3f}, and {d_remove:.3f} "
        f"distinct strict items per 1,000 thinking tokens."
    )


def _phrase_finding(phrases: pd.DataFrame) -> str:
    """Return the phrase-only finding from the phrase rate table."""
    if phrases.empty:
        return ""
    parts = [
        "Phrase-only uncertainty ignores bag-of-words tokens, so it is the "
        "narrower reading of explicit hedging language."
    ]
    for model_id, subset in phrases.groupby("model_id", sort=False):
        sentence = _phrase_model_sentence(str(model_id), subset)
        if sentence:
            parts.append(sentence)
    return " ".join(parts)


def _phrase_model_sentence(model_id: str, subset: pd.DataFrame) -> str:
    by_group = {str(row["group"]): row for _, row in subset.iterrows()}
    if any(group not in by_group for group in TOKEN_GROUPS):
        return ""
    split = by_group[GROUP_SPLIT]
    keep = by_group[GROUP_UNANIMOUS_KEEP]
    remove = by_group[GROUP_UNANIMOUS_REMOVE]
    u_split = float(split["uncertainty_rate"])
    u_keep = float(keep["uncertainty_rate"])
    u_remove = float(remove["uncertainty_rate"])
    t_split = float(split["tension_rate"])
    t_keep = float(keep["tension_rate"])
    t_remove = float(remove["tension_rate"])
    return (
        f"{model_id}: phrase-only uncertainty is {u_split:.3f} on split, "
        f"{u_keep:.3f} on keep, and {u_remove:.3f} on remove. "
        f"Phrase-only tension is {t_split:.3f}, {t_keep:.3f}, and {t_remove:.3f}."
    )


def _pooled_high_items(items: pd.DataFrame) -> pd.DataFrame:
    """Pool item rates across groups and keep items at or above HIGH_ITEM_RATE."""
    if items.empty:
        return items
    work = items.copy()
    work["_hits"] = work["rate"] * work["n_valid"]
    grouped = work.groupby(
        ["prompt_arm", "model_id", "family", "kind", "item"], sort=False
    )
    pooled = grouped.agg(n_valid=("n_valid", "sum"), _hits=("_hits", "sum")).reset_index()
    pooled["rate"] = pooled["_hits"] / pooled["n_valid"]
    pooled = pooled.drop(columns=["_hits"])
    pooled = pooled[
        [
            "prompt_arm",
            "model_id",
            "family",
            "kind",
            "item",
            "n_valid",
            "rate",
        ]
    ]
    high = pooled.loc[pooled["rate"] >= HIGH_ITEM_RATE]
    return high.sort_values(["model_id", "rate"], ascending=[True, False]).reset_index(
        drop=True
    )


def _group_float_map(subset: pd.DataFrame, column: str) -> dict[str, float]:
    return {str(row["group"]): float(row[column]) for _, row in subset.iterrows()}


def _upload_output(path: Path) -> None:
    """Upload under the experiment 4 prefix. put_new when absent, else replace."""
    upload_under_prefix(path, EXPERIMENT4_S3_PREFIX)


if __name__ == "__main__":
    main()
