"""Map codebook features to rank-1 Part 2 themes via Titan cosine similarity.

Run from the repo root::

    PYTHONPATH=. uv run python -m \\
        experiments.llm_feature_generation_phase_2_part_3_2026_09_24.src.map_part2_themes \\
        --codebook outputs/shared/codebook/approved_<ts>/codebook.json \\
        --part2-themes-dir experiments/llm_based_feature_generation_2026_07_31/outputs/2026_08_01-14:08:32.373981 \\
        --write
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

import numpy as np
import pandas as pd

from experiments.llm_feature_generation_phase_2_part_3_2026_09_24.src import constants, paths
from shared.embeddings.bedrock import BEDROCK_MODEL_ID, cosine_similarity, create_embedding

PART2_THEME_DEFINITION_SEPARATOR = "; "
THEME_MAP_RANK_ONE = 1
EXPECTED_PART2_THEME_COUNT = 132


@dataclass(frozen=True)
class Part2Theme:
    """One Part 2 stage-2 synthesis theme."""

    theme_id: str
    label: str
    definition_text: str


def embed_feature_text(name: str, definition: str) -> str:
    """Return Titan input text for a codebook feature."""
    return f"{name}. {definition}"


def load_part2_themes(part2_themes_dir: Path) -> list[Part2Theme]:
    """Load Part 2 themes from stage-2 JSON shards (one entry per shard theme)."""
    if not part2_themes_dir.is_dir():
        raise FileNotFoundError(part2_themes_dir)
    themes: list[Part2Theme] = []
    for json_path in sorted(part2_themes_dir.glob("*.json")):
        payload = json.loads(json_path.read_text(encoding="utf-8"))
        for theme in payload.get("result", {}).get("themes", []):
            theme_key = f"{json_path.stem}:{theme['id']}"
            definition = PART2_THEME_DEFINITION_SEPARATOR.join(theme.get("defining_features", []))
            themes.append(
                Part2Theme(
                    theme_id=theme_key,
                    label=str(theme["label"]),
                    definition_text=definition,
                )
            )
    return themes


def theme_embed_text(theme: Part2Theme) -> str:
    """Build Titan input for one Part 2 theme."""
    return embed_feature_text(theme.label, theme.definition_text)


def rank1_theme_map_rows(
    codebook_features: list[dict[str, Any]],
    themes: list[Part2Theme],
    embed_fn: Callable[[str], list[float]],
) -> list[dict[str, Any]]:
    """Return rank-1 nearest Part 2 theme per codebook feature."""
    theme_vectors = [(theme, embed_fn(theme_embed_text(theme))) for theme in themes]
    rows: list[dict[str, Any]] = []
    for feature in codebook_features:
        feature_id = str(feature["feature_id"])
        feature_name = str(feature["name"])
        vector = embed_fn(embed_feature_text(feature_name, str(feature["definition"])))
        best = _best_theme_match(theme_vectors, vector)
        rows.append(
            {
                "feature_id": feature_id,
                "feature_name": feature_name,
                "part2_theme_id": best["part2_theme_id"],
                "part2_theme_label": best["part2_theme_label"],
                "cosine_similarity": best["cosine_similarity"],
                "rank": THEME_MAP_RANK_ONE,
            }
        )
    return rows


def write_theme_map_outputs(
    run_dir: Path,
    rows: list[dict[str, Any]],
    part2_themes_dir: Path,
    n_themes: int,
) -> Path:
    """Write theme_map.csv, theme_map.md, and metadata.json."""
    run_dir.mkdir(parents=True, exist_ok=True)
    csv_path = run_dir / "theme_map.csv"
    pd.DataFrame(rows).to_csv(csv_path, index=False)
    md_path = run_dir / "theme_map.md"
    md_path.write_text(_theme_map_markdown(rows), encoding="utf-8")
    metadata = {
        "part2_themes_dir": str(part2_themes_dir),
        "n_themes": n_themes,
        "bedrock_model_id": BEDROCK_MODEL_ID,
        "built_at": datetime.now(timezone.utc).isoformat(),
    }
    (run_dir / "metadata.json").write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    return csv_path


def load_codebook_features(codebook_path: Path) -> list[dict[str, Any]]:
    """Load feature dicts from approved codebook JSON."""
    payload = json.loads(codebook_path.read_text(encoding="utf-8"))
    return list(payload["features"])


def main(argv: list[str] | None = None) -> None:
    """CLI entry for Part 2 theme mapping."""
    args = _parse_args(argv)
    codebook_path = Path(args.codebook)
    themes_dir = Path(args.part2_themes_dir)
    themes = load_part2_themes(themes_dir)
    print(f"part2_themes_loaded={len(themes)}")
    features = load_codebook_features(codebook_path)
    embed_fn = _default_embed_fn if args.write else _noop_embed_fn
    rows = rank1_theme_map_rows(features, themes, embed_fn)
    if not args.write:
        return
    run_dir = paths.EXPERIMENT_ROOT / "outputs/shared/part2_theme_map" / paths.make_run_timestamp()
    csv_path = write_theme_map_outputs(run_dir, rows, themes_dir, len(themes))
    print(f"Wrote {csv_path}")


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Map codebook features to Part 2 themes.")
    parser.add_argument("--codebook", required=True)
    parser.add_argument("--part2-themes-dir", default=constants.PART2_STAGE2_OUTPUT_DIR)
    parser.add_argument("--write", action="store_true")
    return parser.parse_args(argv)


def _default_embed_fn(text: str) -> list[float]:
    response = create_embedding(
        text,
        model_id=constants.EMBEDDING_MODEL_ID,
        dimensions=constants.EMBEDDING_DIM,
        normalize=constants.EMBEDDING_NORMALIZE,
    )
    return list(response["embedding"])


def _noop_embed_fn(text: str) -> list[float]:
    raise RuntimeError("embedding requires --write")


def _best_theme_match(
    theme_vectors: list[tuple[Part2Theme, list[float]]],
    feature_vector: list[float],
) -> dict[str, Any]:
    best_score = -1.0
    best_theme = theme_vectors[0][0]
    for theme, vector in theme_vectors:
        score = cosine_similarity(feature_vector, vector)
        if score > best_score:
            best_score = score
            best_theme = theme
    return {
        "part2_theme_id": best_theme.theme_id,
        "part2_theme_label": best_theme.label,
        "cosine_similarity": float(best_score),
    }


def _theme_map_markdown(rows: list[dict[str, Any]]) -> str:
    lines = ["| feature_id | part2_theme_label | cosine_similarity |", "| --- | --- | --- |"]
    for row in rows:
        lines.append(
            f"| {row['feature_id']} | {row['part2_theme_label']} | {row['cosine_similarity']:.4f} |"
        )
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    main()
