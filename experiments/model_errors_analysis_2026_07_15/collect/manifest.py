"""Enumerate eligible Bedrock + llm_api runs → run_manifest.json.

Hard constraint: only the pre-copied prediction artifacts listed in spec.md.
Do not call Bedrock / AWS / api_baselines train scripts.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path

EXPERIMENT_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = EXPERIMENT_ROOT.parents[1]
OUTPUTS_DIR = EXPERIMENT_ROOT / "outputs"
MANIFEST_PATH = OUTPUTS_DIR / "run_manifest.json"

PKR_ROOT = REPO_ROOT / "experiments" / "predict_keep_remove_2026_07_01"
API_BASELINES = PKR_ROOT / "models" / "llm_finetuning" / "api_baselines"
LLM_API = PKR_ROOT / "models" / "llm_api"

LONG_CSV_COLUMNS = (
    "post_id",
    "original_text",
    "mirrored_text",
    "label",
    "classifier_id",
    "family",
    "ablation",
    "is_correct",
)


@dataclass(frozen=True)
class RunSpec:
    classifier_id: str
    family: str
    ablation: str
    run_dir: str  # repo-relative
    prediction_files: tuple[str, ...]
    expected_rows: int


def _rel(path: Path) -> str:
    return str(path.relative_to(REPO_ROOT))


def canonical_runs() -> list[RunSpec]:
    """Return the exact V0 runs from the spec (fixed timestamps)."""
    bedrock = [
        RunSpec(
            classifier_id="bedrock/ministral-3-8b-instruct",
            family="bedrock",
            ablation=(
                "provider=bedrock|model=ministral-3-8b-instruct|"
                "bedrock_model_id=mistral.ministral-3-8b-instruct|"
                "prompt=linked_fate_both_posts|input_mode=original_plus_mirror"
            ),
            run_dir=_rel(
                API_BASELINES
                / "ministral-3-8b-instruct"
                / "outputs"
                / "2026_07_06-15:52:37"
            ),
            prediction_files=("predictions.csv",),
            expected_rows=8791,
        ),
        RunSpec(
            classifier_id="bedrock/ministral-3-14b-instruct",
            family="bedrock",
            ablation=(
                "provider=bedrock|model=ministral-3-14b-instruct|"
                "bedrock_model_id=mistral.ministral-3-14b-instruct|"
                "prompt=linked_fate_both_posts|input_mode=original_plus_mirror"
            ),
            run_dir=_rel(
                API_BASELINES
                / "ministral-3-14b-instruct"
                / "outputs"
                / "2026_07_06-16:12:54"
            ),
            prediction_files=("predictions.csv",),
            expected_rows=8791,
        ),
        RunSpec(
            classifier_id="bedrock/qwen3-32b",
            family="bedrock",
            ablation=(
                "provider=bedrock|model=qwen3-32b|"
                "bedrock_model_id=qwen.qwen3-32b-v1:0|"
                "prompt=linked_fate_both_posts|input_mode=original_plus_mirror"
            ),
            run_dir=_rel(API_BASELINES / "qwen3-32b" / "outputs" / "2026_07_06-16:35:49"),
            prediction_files=("predictions.csv",),
            expected_rows=8791,
        ),
        RunSpec(
            classifier_id="bedrock/qwen3-next-80b-a3b",
            family="bedrock",
            ablation=(
                "provider=bedrock|model=qwen3-next-80b-a3b|"
                "bedrock_model_id=qwen.qwen3-next-80b-a3b|"
                "prompt=linked_fate_both_posts|input_mode=original_plus_mirror"
            ),
            run_dir=_rel(
                API_BASELINES / "qwen3-next-80b-a3b" / "outputs" / "2026_07_06-16:57:43"
            ),
            prediction_files=("predictions.csv",),
            expected_rows=8791,
        ),
    ]

    llm_api = [
        RunSpec(
            classifier_id="llm_api/one_shot/original/small",
            family="llm_api",
            ablation=(
                "provider=openai|model=gpt-5.4-nano|model_size=small|"
                "prompt_type=one_shot|input_mode=original"
            ),
            run_dir=_rel(
                LLM_API / "one_shot" / "original" / "small" / "outputs" / "2026_07_03-18:30:51"
            ),
            prediction_files=("train_predictions.csv", "test_predictions.csv"),
            expected_rows=8791,
        ),
        RunSpec(
            classifier_id="llm_api/one_shot/original_plus_mirror/small",
            family="llm_api",
            ablation=(
                "provider=openai|model=gpt-5.4-nano|model_size=small|"
                "prompt_type=one_shot|input_mode=original_plus_mirror"
            ),
            run_dir=_rel(
                LLM_API
                / "one_shot"
                / "original_plus_mirror"
                / "small"
                / "outputs"
                / "2026_07_03-18:30:14"
            ),
            prediction_files=("train_predictions.csv", "test_predictions.csv"),
            expected_rows=8791,
        ),
    ]
    return bedrock + llm_api


def _count_csv_rows(path: Path) -> int:
    # Subtract header; empty files would be 0.
    with path.open("r", encoding="utf-8") as f:
        n = sum(1 for _ in f)
    return max(0, n - 1)


def build_manifest(*, write: bool = True) -> dict:
    """Validate prediction files exist and write run_manifest.json."""
    runs_out: list[dict] = []
    for spec in canonical_runs():
        run_path = REPO_ROOT / spec.run_dir
        if not run_path.is_dir():
            raise FileNotFoundError(f"Missing run dir for {spec.classifier_id}: {run_path}")

        file_counts: dict[str, int] = {}
        total = 0
        for name in spec.prediction_files:
            pred_path = run_path / name
            if not pred_path.is_file():
                raise FileNotFoundError(
                    f"Missing prediction file for {spec.classifier_id}: {pred_path}"
                )
            n = _count_csv_rows(pred_path)
            file_counts[name] = n
            total += n

        if total != spec.expected_rows:
            raise ValueError(
                f"Row count mismatch for {spec.classifier_id}: "
                f"expected {spec.expected_rows}, got {total} ({file_counts})"
            )

        metadata_path = run_path / "metadata.json"
        metrics_path = run_path / "metrics.json"
        if metadata_path.is_file():
            meta = json.loads(metadata_path.read_text(encoding="utf-8"))
            if meta.get("limit") not in (None,):
                raise ValueError(
                    f"Refusing smoke/limited run for {spec.classifier_id}: limit={meta.get('limit')}"
                )

        entry = {
            **asdict(spec),
            "prediction_files": list(spec.prediction_files),
            "row_counts": file_counts,
            "n_rows": total,
            "metadata_path": _rel(metadata_path) if metadata_path.is_file() else None,
            "metrics_path": _rel(metrics_path) if metrics_path.is_file() else None,
        }
        runs_out.append(entry)

    manifest = {
        "experiment": "model_errors_analysis_2026_07_15",
        "policy": (
            "LLM-API-only long CSV (family in {bedrock, llm_api}). "
            "Bedrock predictions reused from copied artifacts; do not call Bedrock/AWS."
        ),
        "long_csv_columns": list(LONG_CSV_COLUMNS),
        "n_classifiers": len(runs_out),
        "expected_long_csv_rows": sum(r["n_rows"] for r in runs_out),
        "runs": runs_out,
    }

    if write:
        OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
        MANIFEST_PATH.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

    return manifest


def main() -> None:
    manifest = build_manifest(write=True)
    print(f"Wrote {MANIFEST_PATH.relative_to(REPO_ROOT)}")
    print(f"classifiers={manifest['n_classifiers']} expected_rows={manifest['expected_long_csv_rows']}")


if __name__ == "__main__":
    main()
