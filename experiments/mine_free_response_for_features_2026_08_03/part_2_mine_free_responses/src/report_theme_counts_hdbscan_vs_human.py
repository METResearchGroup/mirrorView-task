"""Follow-up script that asks an LLM to re-code and re-cluster some posts that were marked as "noise" during
the HDBSCAN clustering.

The clustering did its job and based on just the 256-D representation, it correctly generated the right clusters.

However, after human review, it looks like HDBSCAN missed a bunch of classes of features that it should've likely caught.

Here, we ask an LLM to code the groups itself.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from collections.abc import Callable
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field
from tqdm import tqdm

from experiments.mine_free_response_for_features_2026_08_03.part_2_mine_free_responses.src.generate_labels_for_embeddings import (
    ASSIGNMENTS_HDBSCAN_FILENAME,
    NOISE_CLUSTER_ID,
    load_hdbscan_assignments,
    resolve_clusters_run_dir,
)
from experiments.mine_free_response_for_features_2026_08_03.part_2_mine_free_responses.src.paths import (
    PART2_ROOT,
    latest_timestamp_subdir,
    stage4_root,
    validate_likert_group,
)
from lib.load_env_vars import EnvVarsContainer
from research_tools.llm.runner import run

DEFAULT_MODEL = "gpt-5.4-nano"
DEFAULT_BATCH_SIZE = 20
DEFAULT_RESIDUAL_MAX_THEMES = 5
OUTPUT_FILENAME = "theme_counts_hdbscan_vs_human.json"
OTHER_THEME_ID = "other"


class NoiseAssignment(BaseModel):
    """One noise feature mapped onto the Stage-4 codebook."""

    feature_id: str
    theme_id: str = Field(
        description=(
            "Existing cluster_id as a string (e.g. '0', '1') when the feature "
            "fits that theme's definition, otherwise 'other'."
        )
    )
    confidence: Literal["high", "medium", "low"]
    brief_reason: str = Field(
        description="One short clause justifying the assignment."
    )


class NoiseBatchResult(BaseModel):
    """Structured LLM response for one batch of noise features."""

    assignments: list[NoiseAssignment]


class ResidualTheme(BaseModel):
    """A residual theme proposed among leftover other features."""

    theme_key: str = Field(
        description="snake_case short key for the residual theme."
    )
    theme_label: str
    definition: str
    member_feature_ids: list[str]


class ResidualThemesResult(BaseModel):
    """Structured LLM response naming residual themes in other-coded noise."""

    themes: list[ResidualTheme]


def _load_stage4_themes(labels_run_dir: Path) -> dict[int, dict[str, Any]]:
    """Load cluster_id -> label metadata from Stage-4 runner outputs."""
    themes: dict[int, dict[str, Any]] = {}
    for path in sorted(labels_run_dir.glob("*.json")):
        if path.name == "metadata.json":
            continue
        row = json.loads(path.read_text(encoding="utf-8"))
        cluster_id = int(row["cluster_id"])
        result = row["result"]
        themes[cluster_id] = {
            "cluster_id": cluster_id,
            "cluster_label": result["cluster_label"],
            "definition": result["definition"],
            "n_members_labeled_from": int(row["n_members"]),
        }
    if not themes:
        raise ValueError(f"No Stage-4 theme labels in {labels_run_dir}")
    return themes


def resolve_labels_run_dir(
    likert_group: str,
    labels_run_dir: str | None,
) -> Path:
    """Resolve Stage-4 run directory from an explicit path or latest."""
    if labels_run_dir:
        path = Path(labels_run_dir)
        if not path.is_dir():
            raise FileNotFoundError(f"labels-run-dir not found: {path}")
        return path
    return latest_timestamp_subdir(stage4_root(likert_group) / "outputs")


def _codebook_block(themes: dict[int, dict[str, Any]]) -> str:
    """Format the Stage-4 codebook for the coding prompt."""
    lines: list[str] = []
    for cluster_id in sorted(themes):
        theme = themes[cluster_id]
        lines.append(
            f"- theme_id={cluster_id!s}: {theme['cluster_label']}\n"
            f"  definition: {theme['definition']}"
        )
    lines.append(
        f"- theme_id={OTHER_THEME_ID}: does not clearly fit any theme above"
    )
    return "\n".join(lines)


def _feature_block(features: list[dict[str, Any]]) -> str:
    """Format feature rows for the coding prompt."""
    chunks: list[str] = []
    for feature in features:
        chunks.append(
            "\n".join(
                [
                    f"feature_id: {feature['feature_id']}",
                    f"feature_name: {feature['feature_name']}",
                    f"feature_value: {feature['feature_value']}",
                    f"rationale: {feature['rationale']}",
                    f"evidence_span: {feature.get('evidence_span', '')}",
                    f"category: {feature.get('category', '')}",
                ]
            )
        )
    return "\n---\n".join(chunks)


def build_noise_coding_messages(
    item: dict[str, Any],
) -> list[dict[str, str]]:
    """Build chat messages for one noise-feature coding batch."""
    system = (
        "You are coding free-response moderation decision features into a "
        "fixed qualitative codebook. Assign each feature to the best-fitting "
        "theme_id, or 'other' when none fit.\n\n"
        "Rules:\n"
        "- Assign a codebook theme only when the feature's PRIMARY claim "
        "matches that theme's definition.\n"
        "- Paraphrases count; mere topical relatedness does not.\n"
        "- If two themes could apply, pick the single best fit; if neither "
        "is clearly primary, use 'other'.\n"
        "- Do NOT assign a theme just because the Likert group is low/high, "
        "or because the feature fails to mention something.\n"
        "- Especially for themes about pair comparison having little "
        "influence: require an explicit claim that pair/mirror comparison "
        "did not drive the decision (or that posts were judged "
        "individually / independently of the pairing).\n"
        "- Do not invent new theme_ids. Return one assignment per "
        "feature_id."
    )
    user = (
        f"Likert group: {item['likert_group']}\n\n"
        f"Codebook:\n{item['codebook']}\n\n"
        f"Features to code:\n{item['features_block']}\n\n"
        "Assign every feature_id exactly once."
    )
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]


def build_residual_messages(item: dict[str, Any]) -> list[dict[str, str]]:
    """Build chat messages for residual-theme naming among other features."""
    system = (
        "You are summarizing leftover free-response features that did not fit "
        "the primary codebook. Propose up to max_themes coherent residual "
        "themes. Only create a theme when at least 3 features clearly share "
        "it. Leave sparse one-offs out of member lists. theme_key must be "
        "snake_case."
    )
    user = (
        f"Likert group: {item['likert_group']}\n"
        f"max_themes: {item['max_themes']}\n\n"
        f"Leftover features:\n{item['features_block']}\n\n"
        "Return residual themes with member_feature_ids drawn only from the "
        "features above."
    )
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]


def _batch_features(
    features: list[dict[str, Any]],
    batch_size: int,
) -> list[list[dict[str, Any]]]:
    """Split features into contiguous batches."""
    return [
        features[index : index + batch_size]
        for index in range(0, len(features), batch_size)
    ]


def _wrap_writer_with_progress(
    base_writer: Callable[[dict[str, Any], Any], dict[str, Any]],
    progress_bar: tqdm,
) -> Callable[[dict[str, Any], Any], dict[str, Any]]:
    """Advance the progress bar after each completed runner item."""

    def wrapped(item: dict[str, Any], result: Any) -> dict[str, Any]:
        row = base_writer(item, result)
        progress_bar.update(1)
        return row

    return wrapped


def _valid_theme_ids(themes: dict[int, dict[str, Any]]) -> set[str]:
    """Return allowed theme_id strings including other."""
    return {str(cluster_id) for cluster_id in themes} | {OTHER_THEME_ID}


def _normalize_assignments(
    batch_features: list[dict[str, Any]],
    result: NoiseBatchResult,
    valid_ids: set[str],
) -> dict[str, dict[str, Any]]:
    """Map feature_id -> assignment; default missing/invalid to other."""
    by_id = {row.feature_id: row for row in result.assignments}
    out: dict[str, dict[str, Any]] = {}
    for feature in batch_features:
        feature_id = feature["feature_id"]
        row = by_id.get(feature_id)
        if row is None or row.theme_id not in valid_ids:
            out[feature_id] = {
                "feature_id": feature_id,
                "theme_id": OTHER_THEME_ID,
                "confidence": "low",
                "brief_reason": "missing_or_invalid_model_theme_id",
                "was_hdbscan_noise": True,
            }
            continue
        out[feature_id] = {
            "feature_id": feature_id,
            "theme_id": row.theme_id,
            "confidence": row.confidence,
            "brief_reason": row.brief_reason,
            "was_hdbscan_noise": True,
        }
    return out


def code_noise_features(
    *,
    likert_group: str,
    noise_features: list[dict[str, Any]],
    themes: dict[int, dict[str, Any]],
    batch_size: int,
    model: str,
    output_base: Path,
) -> dict[str, dict[str, Any]]:
    """LLM-code noise features into codebook themes or other."""
    if not noise_features:
        return {}

    EnvVarsContainer.get_env_var("OPENAI_API_KEY", required=True)
    codebook = _codebook_block(themes)
    valid_ids = _valid_theme_ids(themes)
    batches = _batch_features(noise_features, batch_size)
    items = [
        {
            "batch_index": index,
            "likert_group": likert_group,
            "codebook": codebook,
            "features_block": _feature_block(batch),
            "feature_ids": [feature["feature_id"] for feature in batch],
            "batch_features": batch,
        }
        for index, batch in enumerate(batches)
    ]

    def writer_map_fn(
        item: dict[str, Any],
        result: NoiseBatchResult,
    ) -> dict[str, Any]:
        normalized = _normalize_assignments(
            item["batch_features"],
            result,
            valid_ids,
        )
        return {
            "batch_index": item["batch_index"],
            "feature_ids": item["feature_ids"],
            "assignments": list(normalized.values()),
        }

    progress = tqdm(total=len(items), desc=f"code-noise:{likert_group}")
    try:
        run_dir = run(
            items,
            prompt_fn=build_noise_coding_messages,
            response_model=NoiseBatchResult,
            model=model,
            output_base_path=str(output_base),
            writer_map_fn=_wrap_writer_with_progress(writer_map_fn, progress),
            run_metadata={
                "stage": "noise_theme_coding",
                "likert_group": likert_group,
                "model": model,
                "batch_size": batch_size,
                "n_noise_features": len(noise_features),
                "theme_ids": sorted(valid_ids),
            },
        )
    finally:
        progress.close()

    assignments: dict[str, dict[str, Any]] = {}
    for path in sorted(run_dir.glob("*.json")):
        if path.name == "metadata.json":
            continue
        row = json.loads(path.read_text(encoding="utf-8"))
        for assignment in row["assignments"]:
            assignments[assignment["feature_id"]] = assignment
    return assignments


def name_residual_themes(
    *,
    likert_group: str,
    other_features: list[dict[str, Any]],
    max_themes: int,
    model: str,
    output_base: Path,
) -> list[dict[str, Any]]:
    """Propose residual themes among features coded as other."""
    if len(other_features) < 3:
        return []

    EnvVarsContainer.get_env_var("OPENAI_API_KEY", required=True)
    # Cap prompt size: keep up to 120 leftover features (deterministic order).
    sample = other_features[:120]
    item = {
        "likert_group": likert_group,
        "max_themes": max_themes,
        "features_block": _feature_block(sample),
        "allowed_ids": {feature["feature_id"] for feature in sample},
    }

    def writer_map_fn(
        _item: dict[str, Any],
        result: ResidualThemesResult,
    ) -> dict[str, Any]:
        allowed = item["allowed_ids"]
        themes_out: list[dict[str, Any]] = []
        for theme in result.themes:
            members = [
                feature_id
                for feature_id in theme.member_feature_ids
                if feature_id in allowed
            ]
            if len(members) < 3:
                continue
            themes_out.append(
                {
                    "theme_key": theme.theme_key,
                    "theme_label": theme.theme_label,
                    "definition": theme.definition,
                    "member_feature_ids": members,
                    "n_features": len(members),
                }
            )
        return {"themes": themes_out[:max_themes]}

    progress = tqdm(total=1, desc=f"residual:{likert_group}")
    try:
        run_dir = run(
            [item],
            prompt_fn=build_residual_messages,
            response_model=ResidualThemesResult,
            model=model,
            output_base_path=str(output_base),
            writer_map_fn=_wrap_writer_with_progress(writer_map_fn, progress),
            run_metadata={
                "stage": "residual_theme_naming",
                "likert_group": likert_group,
                "model": model,
                "n_other_features_in_prompt": len(sample),
                "n_other_features_total": len(other_features),
                "max_themes": max_themes,
            },
        )
    finally:
        progress.close()

    for path in sorted(run_dir.glob("*.json")):
        if path.name == "metadata.json":
            continue
        return json.loads(path.read_text(encoding="utf-8"))["themes"]
    return []


def _example_for(
    features: list[dict[str, Any]],
) -> dict[str, str] | None:
    """Pick a short representative example from a feature list."""
    if not features:
        return None
    ranked = sorted(
        features,
        key=lambda row: (
            len(row.get("evidence_span") or ""),
            len(row.get("feature_value") or ""),
        ),
        reverse=True,
    )
    chosen = ranked[0]
    return {
        "feature_id": chosen["feature_id"],
        "feature_name": chosen["feature_name"],
        "feature_value": chosen["feature_value"],
        "evidence_span": chosen.get("evidence_span") or "",
        "participant_id": chosen.get("participant_id") or "",
    }


def build_summary(
    *,
    likert_group: str,
    clusters_run_dir: Path,
    labels_run_dir: Path,
    assignments: list[dict[str, Any]],
    themes: dict[int, dict[str, Any]],
    noise_codes: dict[str, dict[str, Any]],
    residual_themes: list[dict[str, Any]],
    model: str,
    noise_coding_note: str,
) -> dict[str, Any]:
    """Assemble the dual HDBSCAN vs human theme-count report."""
    by_feature_id = {row["feature_id"]: row for row in assignments}
    hdbscan_members: dict[int, list[dict[str, Any]]] = defaultdict(list)
    noise_features: list[dict[str, Any]] = []
    for row in assignments:
        cluster_id = int(row["cluster_id"])
        if cluster_id == NOISE_CLUSTER_ID:
            noise_features.append(row)
        else:
            hdbscan_members[cluster_id].append(row)

    human_members: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for cluster_id, members in hdbscan_members.items():
        human_members[str(cluster_id)].extend(members)
    for feature in noise_features:
        code = noise_codes.get(feature["feature_id"])
        theme_id = code["theme_id"] if code else OTHER_THEME_ID
        human_members[theme_id].append(feature)

    theme_rows: list[dict[str, Any]] = []
    for cluster_id in sorted(themes):
        key = str(cluster_id)
        h_members = hdbscan_members.get(cluster_id, [])
        human = human_members.get(key, [])
        soft_from_noise = [
            row
            for row in human
            if int(row["cluster_id"]) == NOISE_CLUSTER_ID
        ]
        theme_rows.append(
            {
                "theme_id": key,
                "source": "hdbscan_labeled",
                "cluster_label": themes[cluster_id]["cluster_label"],
                "definition": themes[cluster_id]["definition"],
                "hdbscan": {
                    "n_features": len(h_members),
                    "n_participants": len(
                        {row["participant_id"] for row in h_members}
                    ),
                    "example": _example_for(h_members),
                },
                "human_annotated_read": {
                    "n_features": len(human),
                    "n_participants": len(
                        {row["participant_id"] for row in human}
                    ),
                    "n_features_from_hdbscan_core": len(h_members),
                    "n_features_soft_assigned_from_noise": len(soft_from_noise),
                    "example": _example_for(human),
                },
            }
        )

    other_members = human_members.get(OTHER_THEME_ID, [])
    residual_with_examples: list[dict[str, Any]] = []
    claimed: set[str] = set()
    for residual in residual_themes:
        members = [
            by_feature_id[feature_id]
            for feature_id in residual["member_feature_ids"]
            if feature_id in by_feature_id
        ]
        claimed.update(residual["member_feature_ids"])
        residual_with_examples.append(
            {
                **residual,
                "n_participants": len(
                    {row["participant_id"] for row in members}
                ),
                "example": _example_for(members),
            }
        )

    ungrouped_other = [
        row
        for row in other_members
        if row["feature_id"] not in claimed
    ]

    confidence_counts = Counter(
        code.get("confidence", "low") for code in noise_codes.values()
    )

    return {
        "likert_group": likert_group,
        "clusters_run_dir": str(clusters_run_dir),
        "labels_run_dir": str(labels_run_dir),
        "method": {
            "hdbscan": (
                "Hard HDBSCAN labels from assignments_hdbscan.json; "
                "cluster_id=-1 is noise."
            ),
            "human_annotated_read": noise_coding_note,
            "model": model,
        },
        "corpus": {
            "n_features_total": len(assignments),
            "n_participants_with_features": len(
                {row["participant_id"] for row in assignments}
            ),
            "n_hdbscan_noise_features": len(noise_features),
            "n_hdbscan_labeled_features": len(assignments) - len(noise_features),
        },
        "noise_soft_assignment_confidence_counts": dict(confidence_counts),
        "themes": theme_rows,
        "other_after_human_coding": {
            "theme_id": OTHER_THEME_ID,
            "n_features": len(other_members),
            "n_participants": len(
                {row["participant_id"] for row in other_members}
            ),
            "example": _example_for(other_members),
            "residual_themes": residual_with_examples,
            "n_features_still_ungrouped": len(ungrouped_other),
        },
        "noise_assignments": [
            {
                **noise_codes[feature["feature_id"]],
                "participant_id": feature["participant_id"],
                "feature_name": feature["feature_name"],
            }
            for feature in noise_features
            if feature["feature_id"] in noise_codes
        ],
    }


def run_for_group(
    *,
    likert_group: str,
    clusters_run_dir: Path,
    labels_run_dir: Path,
    batch_size: int,
    model: str,
    residual_max_themes: int,
    skip_residual: bool,
) -> Path:
    """Run coding + summary write for one Likert group."""
    assignments, _metadata = load_hdbscan_assignments(clusters_run_dir)
    themes = _load_stage4_themes(labels_run_dir)
    noise_features = [
        row
        for row in assignments
        if int(row["cluster_id"]) == NOISE_CLUSTER_ID
    ]

    coding_root = (
        PART2_ROOT
        / "outputs"
        / "theme_human_coding"
        / likert_group
        / "noise_coding"
    )
    residual_root = (
        PART2_ROOT
        / "outputs"
        / "theme_human_coding"
        / likert_group
        / "residual_naming"
    )

    noise_codes = code_noise_features(
        likert_group=likert_group,
        noise_features=noise_features,
        themes=themes,
        batch_size=batch_size,
        model=model,
        output_base=coding_root,
    )

    other_features = [
        feature
        for feature in noise_features
        if noise_codes.get(feature["feature_id"], {}).get("theme_id")
        == OTHER_THEME_ID
    ]
    residual_themes: list[dict[str, Any]] = []
    if not skip_residual:
        residual_themes = name_residual_themes(
            likert_group=likert_group,
            other_features=other_features,
            max_themes=residual_max_themes,
            model=model,
            output_base=residual_root,
        )

    summary = build_summary(
        likert_group=likert_group,
        clusters_run_dir=clusters_run_dir,
        labels_run_dir=labels_run_dir,
        assignments=assignments,
        themes=themes,
        noise_codes=noise_codes,
        residual_themes=residual_themes,
        model=model,
        noise_coding_note=(
            "HDBSCAN core members kept on their labeled theme. Each "
            "cluster_id=-1 feature was coded by an LLM against the Stage-4 "
            "theme definitions (human-style thematic assignment), or marked "
            "other. Residual themes are optional groupings within leftover "
            "other features."
        ),
    )

    out_path = clusters_run_dir / OUTPUT_FILENAME
    # Drop bulky per-noise list from the primary summary? Keep it — useful.
    out_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return out_path


def parse_args() -> argparse.Namespace:
    """Parse CLI arguments."""
    parser = argparse.ArgumentParser(
        description=(
            "Write theme_counts_hdbscan_vs_human.json for a Likert group."
        )
    )
    parser.add_argument(
        "--likert-group",
        required=True,
        choices=["low", "high"],
        help="Likert split to process.",
    )
    parser.add_argument(
        "--clusters-run-dir",
        default=None,
        help="Optional Stage-3 run dir (default: latest timestamp).",
    )
    parser.add_argument(
        "--labels-run-dir",
        default=None,
        help="Optional Stage-4 labels run dir (default: latest).",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=DEFAULT_BATCH_SIZE,
        help="Noise features per LLM coding call.",
    )
    parser.add_argument(
        "--model",
        default=DEFAULT_MODEL,
        help="OpenAI model for soft assignment / residual naming.",
    )
    parser.add_argument(
        "--residual-max-themes",
        type=int,
        default=DEFAULT_RESIDUAL_MAX_THEMES,
        help="Max residual themes to propose among leftover other.",
    )
    parser.add_argument(
        "--skip-residual",
        action="store_true",
        help="Skip residual-theme naming among leftover other features.",
    )
    return parser.parse_args()


def main() -> None:
    """CLI entry: code noise and write dual theme-count JSON."""
    args = parse_args()
    validate_likert_group(args.likert_group)
    clusters_run_dir = resolve_clusters_run_dir(
        args.likert_group,
        args.clusters_run_dir,
    )
    labels_run_dir = resolve_labels_run_dir(
        args.likert_group,
        args.labels_run_dir,
    )
    out_path = run_for_group(
        likert_group=args.likert_group,
        clusters_run_dir=clusters_run_dir,
        labels_run_dir=labels_run_dir,
        batch_size=args.batch_size,
        model=args.model,
        residual_max_themes=args.residual_max_themes,
        skip_residual=args.skip_residual,
    )
    print(f"Wrote {out_path}")


if __name__ == "__main__":
    main()
