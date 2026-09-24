"""Held-out test-set analysis for research questions Q1 through Q7.

Run from the repo root::

    PYTHONPATH=. uv run python -m experiments.llm_feature_generation_phase_2_part_3_2026_09_24.src.analyze \\
      --split test \\
      --codebook outputs/shared/codebook/approved_<ts>/codebook.json \\
      --label-matrix outputs/shared/label_matrix.parquet \\
      --part2-map outputs/shared/part2_theme_map/<ts>/theme_map.csv \\
      --write
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Callable

import numpy as np
import pandas as pd
from scipy.stats import chi2_contingency, fisher_exact
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import log_loss, roc_auc_score

from experiments.llm_feature_generation_phase_2_part_3_2026_09_24.src import constants, paths
from experiments.llm_feature_generation_phase_2_part_3_2026_09_24.src.cohort import slim_trials
from experiments.llm_feature_generation_phase_2_part_3_2026_09_24.src.label_posts import TEXT_SURFACE_MIRROR, TEXT_SURFACE_ORIGINAL
from shared.data.dataloader import load_dataset
from shared.data.registry import STUDY_PHASE_2_PART_2_AND_3_RESULTS_FULL

FEATURE_ID_CONFRONTATIONAL_DIRECT = "cb_026"
FEATURE_ID_DIRECT_SECOND_PERSON = "cb_027"
DERIVED_NEUTRAL_DIRECT_ADDRESS = "neutral_direct_address"
TEXT_SURFACE_ORIGINAL_ONLY = "original_only"
TEXT_SURFACE_MIRROR_ONLY = "mirror_only"
TEXT_ARM_PAIRED = "paired"
TEXT_ARM_COMBINED = "combined"
LABEL_DEFINITION_MODAL = "modal"
LABEL_DEFINITION_UNANIMOUS = "unanimous"
LABEL_DEFINITION_THREE_GROUP = "three_group"
LABEL_SOURCE_UNION = "union"
LABEL_SOURCE_PART3_ONLY = "part3_only"
LOGISTIC_MAX_ITER = 500
MIN_TRIALS_FOR_AUC = 10


class AblationAxis(str, Enum):
    """Supported ablation axes from the experiment plan."""

    TEXT_ARM = "text_arm"
    BATCH_DESIGN = "batch_design"
    LABEL_DEFINITION = "label_definition"
    LABEL_SOURCE = "label_source"
    PARTICIPANT_FILTER = "participant_filter"
    CLUSTERING = "clustering"
    SEED = "seed"


@dataclass(frozen=True)
class AnalysisConfig:
    """Primary and ablation settings for one analysis run."""

    text_arm: str = TEXT_ARM_PAIRED
    participant_filter: str = constants.PARTICIPANT_FILTER_ATTENTION_PASS
    label_source: str = LABEL_SOURCE_UNION
    label_definition: str = LABEL_DEFINITION_MODAL
    batch_design: str = constants.BATCH_DESIGN_MIXED
    clustering: str = "hdbscan"
    seed: int = constants.DEFAULT_SEED


@dataclass(frozen=True)
class AnalysisInputs:
    """Loaded tables for Q1 through Q7."""

    test_labels: pd.DataFrame
    feature_ids: list[str]
    cohort: pd.DataFrame
    theme_map: pd.DataFrame | None
    trial_frame: pd.DataFrame | None


def load_test_post_ids(split_dir: Path | None = None) -> set[str]:
    """Load held-out test post IDs from the committed split file."""
    directory = split_dir or paths.post_split_dir()
    test_path = directory / "test_post_ids.csv"
    frame = pd.read_csv(test_path)
    return set(frame["post_id"].astype(str))


def load_test_labels(
    label_matrix_path: Path,
    test_post_ids: set[str] | None = None,
) -> pd.DataFrame:
    """Return label-matrix rows for held-out test posts only."""
    matrix = pd.read_parquet(label_matrix_path)
    test_ids = test_post_ids or load_test_post_ids()
    filtered = matrix.loc[
        (matrix["split"] == constants.TEST_SPLIT) & matrix["post_id"].astype(str).isin(test_ids)
    ].copy()
    unique_posts = set(filtered["post_id"].astype(str))
    if unique_posts != test_ids:
        missing = test_ids - unique_posts
        extra = unique_posts - test_ids
        raise ValueError(f"test label mismatch missing={len(missing)} extra={len(extra)}")
    _assert_no_discovery_rows(filtered)
    return filtered


def load_cohort_for_filter(participant_filter: str) -> pd.DataFrame:
    """Load union cohort parquet for one participant filter."""
    cohort_dir = paths.latest_cohort_run_dir(TEXT_ARM_PAIRED, participant_filter)
    return pd.read_parquet(cohort_dir / constants.COHORT_FILENAME)


def enrich_test_labels(
    test_labels: pd.DataFrame,
    cohort: pd.DataFrame,
) -> pd.DataFrame:
    """Attach cohort metadata needed for Q1 through Q7."""
    meta_columns = [
        "post_id",
        "in_part2_catalog",
        "three_group_label",
        "sampled_stance",
        "sample_toxicity_type",
    ]
    meta = cohort[meta_columns].copy()
    merged = test_labels.merge(meta, on="post_id", how="left")
    _assert_no_discovery_rows(merged)
    return merged


def benjamini_hochberg(p_values: np.ndarray) -> np.ndarray:
    """Return BH-adjusted q-values for a 1D p-value array."""
    values = np.asarray(p_values, dtype=float)
    n_tests = len(values)
    if n_tests == 0:
        return values
    order = np.argsort(values)
    ranked = values[order]
    multipliers = np.arange(1, n_tests + 1)
    adjusted = ranked * n_tests / multipliers
    adjusted = np.minimum.accumulate(adjusted[::-1])[::-1]
    adjusted = np.clip(adjusted, 0.0, 1.0)
    q_values = np.empty(n_tests)
    q_values[order] = adjusted
    return q_values


def run_q1(
    frame: pd.DataFrame,
    feature_ids: list[str],
) -> dict[str, Any]:
    """Feature prevalence keep vs remove on test posts with BH correction."""
    working = _post_level_original(frame)
    working = _assert_test_only(working)
    rows = [_q1_feature_row(working, feature_id) for feature_id in feature_ids]
    p_values = np.array([row["p_value"] for row in rows], dtype=float)
    q_values = benjamini_hochberg(p_values)
    for index, row in enumerate(rows):
        row["q_value"] = float(q_values[index])
    return {"features": rows, "n_posts": len(working)}


def run_q1_replication(
    frame: pd.DataFrame,
    part3_cohort: pd.DataFrame,
    theme_map: pd.DataFrame | None,
) -> dict[str, Any]:
    """Part 2 catalog replication using part3_only modal labels."""
    posts = _replication_post_ids(frame, part3_cohort)
    subset = frame.loc[frame["post_id"].astype(str).isin(posts)].copy()
    subset = _apply_part3_modal(subset, part3_cohort)
    subset = _post_level_original(subset)
    subset = _assert_test_only(subset)
    result = {
        "n_posts": len(subset),
        "post_ids": sorted(posts),
        "uses_participant_filter": constants.PARTICIPANT_FILTER_PART3_ONLY,
        "in_part2_catalog_only": True,
    }
    if theme_map is not None and not theme_map.empty:
        result["theme_mapping"] = theme_map.to_dict(orient="records")
    return result


def run_q2(frame: pd.DataFrame, feature_ids: list[str]) -> dict[str, Any]:
    """Per-feature original-mirror concordance on test posts."""
    paired = _paired_post_features(frame, feature_ids)
    paired = _assert_test_only(paired)
    rows = [_concordance_row(paired, feature_id) for feature_id in feature_ids]
    p_values = np.array([1.0 - row["concordance_rate"] for row in rows], dtype=float)
    q_values = benjamini_hochberg(p_values)
    for index, row in enumerate(rows):
        row["q_value"] = float(q_values[index])
    return {"features": rows, "n_posts": len(paired)}


def run_q3(frame: pd.DataFrame, feature_ids: list[str]) -> dict[str, Any]:
    """Flip fidelity mismatch rates per feature."""
    paired = _paired_post_features(frame, feature_ids)
    paired = _assert_test_only(paired)
    rows = [_flip_row(paired, feature_id) for feature_id in feature_ids]
    return {"features": rows, "n_posts": len(paired)}


def run_q4(
    frame: pd.DataFrame,
    feature_ids: list[str],
) -> dict[str, Any]:
    """Logistic models by text arm with AUC and log loss."""
    original = _assert_test_only(_post_level_surface(frame, TEXT_SURFACE_ORIGINAL))
    mirror = _assert_test_only(_post_level_surface(frame, TEXT_SURFACE_MIRROR))
    paired = _assert_test_only(_paired_post_features(frame, feature_ids))
    combined = _assert_test_only(_combined_post_features(frame, feature_ids))
    models = {
        TEXT_SURFACE_ORIGINAL_ONLY: _logistic_metrics(
            original, _regression_columns_for_surface(feature_ids)
        ),
        TEXT_SURFACE_MIRROR_ONLY: _logistic_metrics(
            mirror, _regression_columns_for_surface(feature_ids)
        ),
        TEXT_ARM_PAIRED: _logistic_metrics(
            paired, _regression_columns_for_paired(feature_ids)
        ),
        TEXT_ARM_COMBINED: _logistic_metrics(
            combined, [f"diff_{feature_id}" for feature_id in feature_ids]
        ),
    }
    return {"models": models}


def run_q5(frame: pd.DataFrame, feature_ids: list[str]) -> dict[str, Any]:
    """Three-group prevalence among eligible test posts."""
    working = _post_level_original(frame)
    working = working.loc[working["three_group_label"].notna()].copy()
    working = _assert_test_only(working)
    group_counts = working["three_group_label"].value_counts().to_dict()
    rows = [_q5_feature_row(working, feature_id) for feature_id in feature_ids]
    return {"group_counts": group_counts, "features": rows, "n_posts": len(working)}


def run_q6(
    frame: pd.DataFrame,
    feature_ids: list[str],
    trial_frame: pd.DataFrame | None = None,
) -> dict[str, Any]:
    """Moderator party by stance by feature remove rates."""
    trials = trial_frame if trial_frame is not None else load_moderation_trials()
    test_posts = set(frame["post_id"].astype(str))
    rows = _q6_interaction_rows(trials, frame, feature_ids, test_posts)
    return {"rows": rows}


def run_q7(frame: pd.DataFrame, feature_ids: list[str]) -> dict[str, Any]:
    """Incremental AUC beyond toxicity bucket and stance."""
    working = _assert_test_only(_post_level_original(frame))
    covariate_cols = ["sample_toxicity_type", "sampled_stance"]
    base = _logistic_metrics(working, covariate_cols, derive_features=False)
    full_cols = covariate_cols + _regression_columns_for_surface(feature_ids)
    full = _logistic_metrics(working, full_cols, derive_features=True)
    return {
        "base_auc": base["auc"],
        "full_auc": full["auc"],
        "delta_auc": full["auc"] - base["auc"],
        "base_log_loss": base["log_loss"],
        "full_log_loss": full["log_loss"],
    }


def load_moderation_trials() -> pd.DataFrame:
    """Load slim moderation trials with moderator party."""
    raw = load_dataset(STUDY_PHASE_2_PART_2_AND_3_RESULTS_FULL, low_memory=False)
    trials = slim_trials(raw)
    party = raw.groupby("prolific_id")["political_affiliation"].first()
    trials = trials.merge(
        party.rename("moderator_party"),
        left_on="prolific_id",
        right_index=True,
        how="left",
    )
    trials["moderator_party"] = trials["moderator_party"].fillna("unknown").astype(str)
    return trials


def run_all(
    inputs: AnalysisInputs,
    config: AnalysisConfig,
    output_dir: Path,
) -> None:
    """Run Q1 through Q7 and write JSON plus CSV tables."""
    output_dir.mkdir(parents=True, exist_ok=True)
    frame = inputs.test_labels
    feature_ids = inputs.feature_ids
    part3_cohort = load_cohort_for_filter(constants.PARTICIPANT_FILTER_PART3_ONLY)
    results = {
        "q1": run_q1(frame, feature_ids),
        "q1_replication": run_q1_replication(frame, part3_cohort, inputs.theme_map),
        "q2": run_q2(frame, feature_ids),
        "q3": run_q3(frame, feature_ids),
        "q4": run_q4(frame, feature_ids),
        "q5": run_q5(frame, feature_ids),
        "q6": run_q6(frame, feature_ids, inputs.trial_frame),
        "q7": run_q7(frame, feature_ids),
    }
    _write_question_outputs(output_dir, results, feature_ids)
    summary_path = output_dir / "summary_tables.md"
    summary_path.write_text(_build_summary_markdown(results), encoding="utf-8")


def run_ablations(
    inputs: AnalysisInputs,
    axis: AblationAxis,
    values: list[str],
    output_dir: Path,
) -> None:
    """Write ablation summaries under ``output_dir/ablations/<axis>/``."""
    ablation_root = output_dir / "ablations" / axis.value
    ablation_root.mkdir(parents=True, exist_ok=True)
    for value in values:
        config = _config_for_ablation(axis, value)
        child_dir = ablation_root / value
        child_dir.mkdir(parents=True, exist_ok=True)
        payload = {"axis": axis.value, "value": value, "config": config.__dict__}
        (child_dir / "summary.json").write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def load_codebook_feature_ids(codebook_path: Path) -> list[str]:
    """Return ordered feature IDs from codebook JSON."""
    payload = json.loads(codebook_path.read_text(encoding="utf-8"))
    return [str(feature["feature_id"]) for feature in payload["features"]]


def load_theme_map(theme_map_path: Path | None) -> pd.DataFrame | None:
    """Load rank-1 Part 2 theme map CSV when present."""
    if theme_map_path is None or not theme_map_path.is_file():
        return None
    return pd.read_csv(theme_map_path)


def build_analysis_inputs(
    label_matrix_path: Path,
    codebook_path: Path,
    theme_map_path: Path | None,
    participant_filter: str,
    trial_frame: pd.DataFrame | None = None,
) -> AnalysisInputs:
    """Load matrices and cohort metadata for analysis."""
    test_labels = load_test_labels(label_matrix_path)
    cohort = load_cohort_for_filter(participant_filter)
    enriched = enrich_test_labels(test_labels, cohort)
    feature_ids = load_codebook_feature_ids(codebook_path)
    theme_map = load_theme_map(theme_map_path)
    return AnalysisInputs(enriched, feature_ids, cohort, theme_map, trial_frame)


def main(argv: list[str] | None = None) -> None:
    """CLI entry for primary analysis and ablations."""
    args = _parse_args(argv)
    if args.split != constants.TEST_SPLIT:
        raise SystemExit("only --split test is supported")
    config = AnalysisConfig(participant_filter=constants.PARTICIPANT_FILTER_ATTENTION_PASS)
    inputs = build_analysis_inputs(
        Path(args.label_matrix),
        Path(args.codebook),
        Path(args.part2_map) if args.part2_map else None,
        config.participant_filter,
    )
    arm = TEXT_ARM_PAIRED
    run_dir = paths.EXPERIMENT_ROOT / "outputs" / arm / "analysis" / paths.make_run_timestamp()
    if args.ablation:
        axis = AblationAxis(args.ablation)
        values = [value.strip() for value in args.values.split(",") if value.strip()]
        if args.write:
            run_ablations(inputs, axis, values, run_dir)
        return
    print(f"analyze split={args.split} n_posts={inputs.test_labels['post_id'].nunique()}")
    if args.write:
        run_all(inputs, config, run_dir)
        print(f"Wrote {run_dir}")


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Analyze held-out test labels.")
    parser.add_argument("--split", required=True)
    parser.add_argument("--codebook", required=True)
    parser.add_argument("--label-matrix", required=True)
    parser.add_argument("--part2-map", default=None)
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--ablation", default=None)
    parser.add_argument("--values", default="")
    return parser.parse_args(argv)


def _assert_no_discovery_rows(frame: pd.DataFrame) -> None:
    if (frame["split"] == constants.DISCOVERY_SPLIT).any():
        raise ValueError("discovery rows are not allowed in test analyses")


def _assert_test_only(frame: pd.DataFrame) -> pd.DataFrame:
    _assert_no_discovery_rows(frame)
    return frame


def _post_level_original(frame: pd.DataFrame) -> pd.DataFrame:
    return frame.loc[frame["text_surface"] == TEXT_SURFACE_ORIGINAL].copy()


def _post_level_surface(frame: pd.DataFrame, surface: str) -> pd.DataFrame:
    return frame.loc[frame["text_surface"] == surface].copy()


def _paired_post_features(frame: pd.DataFrame, feature_ids: list[str]) -> pd.DataFrame:
    original = _post_level_original(frame).set_index("post_id")
    mirror = _post_level_surface(frame, TEXT_SURFACE_MIRROR).set_index("post_id")
    rows: list[dict[str, Any]] = []
    for post_id in original.index:
        record: dict[str, Any] = {
            "post_id": post_id,
            "split": original.at[post_id, "split"],
            "modal_decision": original.at[post_id, "modal_decision"],
        }
        for feature_id in feature_ids:
            record[f"orig_{feature_id}"] = int(original.at[post_id, feature_id])
            record[f"mirror_{feature_id}"] = int(mirror.at[post_id, feature_id])
        rows.append(record)
    return pd.DataFrame(rows)


def _combined_post_features(frame: pd.DataFrame, feature_ids: list[str]) -> pd.DataFrame:
    paired = _paired_post_features(frame, feature_ids)
    for feature_id in feature_ids:
        paired[f"diff_{feature_id}"] = paired[f"orig_{feature_id}"] - paired[f"mirror_{feature_id}"]
    return paired


def _regression_columns_for_surface(feature_ids: list[str]) -> list[str]:
    """Surface feature columns with neutral direct address instead of cb_027."""
    columns = [
        feature_id for feature_id in feature_ids if feature_id != FEATURE_ID_DIRECT_SECOND_PERSON
    ]
    columns.append(DERIVED_NEUTRAL_DIRECT_ADDRESS)
    return columns


def _regression_columns_for_paired(feature_ids: list[str]) -> list[str]:
    """Paired-arm columns with per-side neutral direct address features."""
    columns: list[str] = []
    for prefix in ("orig_", "mirror_"):
        for feature_id in feature_ids:
            if feature_id == FEATURE_ID_DIRECT_SECOND_PERSON:
                continue
            columns.append(f"{prefix}{feature_id}")
        columns.append(f"{prefix}{DERIVED_NEUTRAL_DIRECT_ADDRESS}")
    return columns


def _add_neutral_direct_address(
    frame: pd.DataFrame,
    second_person_col: str,
    confrontational_col: str,
    output_col: str,
) -> None:
    frame[output_col] = (
        frame[second_person_col].astype(bool) & ~frame[confrontational_col].astype(bool)
    ).astype(int)


def _logistic_metrics(
    frame: pd.DataFrame,
    feature_columns: list[str],
    derive_features: bool = True,
) -> dict[str, float]:
    working = frame.copy()
    if derive_features:
        _apply_neutral_direct_derivations(working, feature_columns)
    y = (working["modal_decision"] == constants.DECISION_REMOVE).astype(int)
    usable = pd.get_dummies(working[feature_columns].fillna(0), drop_first=True).astype(float)
    if len(working) < MIN_TRIALS_FOR_AUC or y.nunique() < 2:
        return {"auc": float("nan"), "log_loss": float("nan")}
    model = LogisticRegression(max_iter=LOGISTIC_MAX_ITER)
    model.fit(usable, y)
    probabilities = model.predict_proba(usable)[:, 1]
    return {
        "auc": float(roc_auc_score(y, probabilities)),
        "log_loss": float(log_loss(y, probabilities)),
    }


def _apply_neutral_direct_derivations(frame: pd.DataFrame, feature_columns: list[str]) -> None:
    if DERIVED_NEUTRAL_DIRECT_ADDRESS in feature_columns:
        _add_neutral_direct_address(
            frame,
            FEATURE_ID_DIRECT_SECOND_PERSON,
            FEATURE_ID_CONFRONTATIONAL_DIRECT,
            DERIVED_NEUTRAL_DIRECT_ADDRESS,
        )
    paired_neutral = f"orig_{DERIVED_NEUTRAL_DIRECT_ADDRESS}"
    if paired_neutral in feature_columns:
        _add_neutral_direct_address(
            frame,
            f"orig_{FEATURE_ID_DIRECT_SECOND_PERSON}",
            f"orig_{FEATURE_ID_CONFRONTATIONAL_DIRECT}",
            f"orig_{DERIVED_NEUTRAL_DIRECT_ADDRESS}",
        )
        _add_neutral_direct_address(
            frame,
            f"mirror_{FEATURE_ID_DIRECT_SECOND_PERSON}",
            f"mirror_{FEATURE_ID_CONFRONTATIONAL_DIRECT}",
            f"mirror_{DERIVED_NEUTRAL_DIRECT_ADDRESS}",
        )


def _q1_feature_row(frame: pd.DataFrame, feature_id: str) -> dict[str, Any]:
    keep_mask = frame["modal_decision"] == constants.DECISION_KEEP
    table = pd.crosstab(frame[feature_id].astype(bool), keep_mask)
    p_value = _two_by_two_pvalue(table)
    keep_rate = float(frame.loc[keep_mask, feature_id].mean()) if keep_mask.any() else float("nan")
    remove_rate = float(frame.loc[~keep_mask, feature_id].mean()) if (~keep_mask).any() else float("nan")
    return {
        "feature_id": feature_id,
        "keep_rate": keep_rate,
        "remove_rate": remove_rate,
        "p_value": p_value,
    }


def _two_by_two_pvalue(table: pd.DataFrame) -> float:
    if table.shape != (2, 2):
        return 1.0
    _, p_value, _, _ = chi2_contingency(table.values)
    if table.values.min() < 5:
        _, p_value = fisher_exact(table.values)
    return float(p_value)


def _concordance_row(frame: pd.DataFrame, feature_id: str) -> dict[str, Any]:
    orig_col = f"orig_{feature_id}"
    mirror_col = f"mirror_{feature_id}"
    agrees = frame[orig_col] == frame[mirror_col]
    rate = float(agrees.mean()) if len(frame) else float("nan")
    return {"feature_id": feature_id, "concordance_rate": rate}


def _flip_row(frame: pd.DataFrame, feature_id: str) -> dict[str, Any]:
    orig_col = f"orig_{feature_id}"
    mirror_col = f"mirror_{feature_id}"
    n_posts = max(len(frame), 1)
    orig_on_mirror_off = float(((frame[orig_col] == 1) & (frame[mirror_col] == 0)).mean())
    mirror_on_orig_off = float(((frame[mirror_col] == 1) & (frame[orig_col] == 0)).mean())
    return {
        "feature_id": feature_id,
        "orig_present_mirror_absent_rate": orig_on_mirror_off,
        "mirror_present_orig_absent_rate": mirror_on_orig_off,
        "n_posts": n_posts,
    }


def _q5_feature_row(frame: pd.DataFrame, feature_id: str) -> dict[str, Any]:
    groups = {}
    for group_name in (
        constants.GROUP_UNANIMOUS_KEEP,
        constants.GROUP_SPLIT,
        constants.GROUP_UNANIMOUS_REMOVE,
    ):
        subset = frame.loc[frame["three_group_label"] == group_name]
        groups[group_name] = float(subset[feature_id].mean()) if len(subset) else float("nan")
    return {"feature_id": feature_id, "prevalence_by_group": groups}


def _q6_interaction_rows(
    trials: pd.DataFrame,
    frame: pd.DataFrame,
    feature_ids: list[str],
    test_posts: set[str],
) -> list[dict[str, Any]]:
    stance_by_post = frame.drop_duplicates("post_id").set_index("post_id")["sampled_stance"]
    feature_frame = _post_level_original(frame).set_index("post_id")
    remove_trials = trials.loc[
        (trials["decision"] == constants.DECISION_REMOVE) & trials["post_id"].isin(test_posts)
    ]
    rows: list[dict[str, Any]] = []
    for feature_id in feature_ids:
        for party in sorted(remove_trials["moderator_party"].unique()):
            for stance in sorted(stance_by_post.unique()):
                posts = remove_trials.loc[
                    (remove_trials["moderator_party"] == party)
                ]["post_id"].unique()
                stance_posts = [post for post in posts if stance_by_post.get(post) == stance]
                if not stance_posts:
                    continue
                presence = feature_frame.loc[stance_posts, feature_id].astype(float)
                rows.append(
                    {
                        "moderator_party": party,
                        "post_stance": stance,
                        "feature_id": feature_id,
                        "remove_rate": float(presence.mean()),
                        "n_trials": len(stance_posts),
                    }
                )
    return rows


def _replication_post_ids(frame: pd.DataFrame, part3_cohort: pd.DataFrame) -> set[str]:
    catalog = part3_cohort.loc[part3_cohort["in_part2_catalog"]].copy()
    catalog = catalog.loc[catalog["split"] == constants.TEST_SPLIT]
    test_posts = set(frame["post_id"].astype(str))
    return test_posts & set(catalog["post_id"].astype(str))


def _apply_part3_modal(frame: pd.DataFrame, part3_cohort: pd.DataFrame) -> pd.DataFrame:
    modal = part3_cohort.set_index("post_id")["modal_decision"]
    updated = frame.copy()
    updated["modal_decision"] = updated["post_id"].map(modal)
    return updated


def _write_question_outputs(output_dir: Path, results: dict[str, Any], feature_ids: list[str]) -> None:
    mapping = {
        "q1_replication.json": results["q1_replication"],
        "q2_stance_invariance.json": results["q2"],
        "q3_flip_fidelity.json": results["q3"],
        "q4_prediction.json": results["q4"],
        "q5_disagreement.json": results["q5"],
        "q6_party_interaction.json": results["q6"],
        "q7_incremental_auc.json": results["q7"],
    }
    for filename, payload in mapping.items():
        (output_dir / filename).write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    pd.DataFrame(results["q1"]["features"]).to_csv(output_dir / "q1_feature_prevalence.csv", index=False)
    pd.DataFrame(results["q1_replication"].get("theme_mapping", [])).to_csv(
        output_dir / "q1_part2_replication.csv", index=False
    )
    pd.DataFrame(results["q2"]["features"]).to_csv(output_dir / "q2_stance_invariance.csv", index=False)
    pd.DataFrame(results["q3"]["features"]).to_csv(output_dir / "q3_flip_fidelity.csv", index=False)
    pd.DataFrame(results["q4"]["models"]).T.reset_index().rename(columns={"index": "arm"}).to_csv(
        output_dir / "q4_prediction_auc.csv", index=False
    )
    pd.DataFrame(results["q5"]["features"]).to_csv(output_dir / "q5_disagreement.csv", index=False)
    pd.DataFrame(results["q6"]["rows"]).to_csv(output_dir / "q6_party_interaction.csv", index=False)
    pd.DataFrame([results["q7"]]).to_csv(output_dir / "q7_incremental_auc.csv", index=False)


def _build_summary_markdown(results: dict[str, Any]) -> str:
    lines = ["# Analysis summary", "", "## Q1 feature prevalence", ""]
    for row in results["q1"]["features"][:5]:
        lines.append(f"- {row['feature_id']}: q={row.get('q_value', 'n/a')}")
    lines.append("")
    return "\n".join(lines)


def _config_for_ablation(axis: AblationAxis, value: str) -> AnalysisConfig:
    base = AnalysisConfig()
    if axis is AblationAxis.TEXT_ARM:
        return AnalysisConfig(text_arm=value)
    if axis is AblationAxis.PARTICIPANT_FILTER:
        return AnalysisConfig(participant_filter=value)
    if axis is AblationAxis.LABEL_SOURCE:
        return AnalysisConfig(label_source=value)
    if axis is AblationAxis.LABEL_DEFINITION:
        return AnalysisConfig(label_definition=value)
    if axis is AblationAxis.BATCH_DESIGN:
        return AnalysisConfig(batch_design=value)
    if axis is AblationAxis.CLUSTERING:
        return AnalysisConfig(clustering=value)
    if axis is AblationAxis.SEED:
        return AnalysisConfig(seed=int(value))
    return base


if __name__ == "__main__":
    main()
