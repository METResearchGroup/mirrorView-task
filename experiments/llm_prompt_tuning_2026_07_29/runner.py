"""Run a keep/remove prompt against posts via research_tools LLMService (Bedrock).

Example:
  PYTHONPATH=. uv run python experiments/llm_prompt_tuning_2026_07_29/runner.py --limit 5
"""

from __future__ import annotations

import csv
import json
import sys
from pathlib import Path
from typing import Optional

import typer
from research_tools import LLMService
from research_tools.prompting import build_prompt_with_stimuli

from experiments.llm_prompt_tuning_2026_07_29 import prompt as prompt_module
from experiments.llm_prompt_tuning_2026_07_29.schemas import IsRemoveResult
from experiments.predict_keep_remove_2026_07_01.data.dataloader import Dataloader
from lib.timestamp_utils import get_current_timestamp

app = typer.Typer(add_completion=False, no_args_is_help=True)

_EXPERIMENT_ROOT = Path(__file__).resolve().parent
_OUTPUTS_DIR = _EXPERIMENT_ROOT / "outputs"

# Public model id registered in research_tools Bedrock provider / models.yaml.
DEFAULT_BEDROCK_MODEL = "qwen/qwen3.6-plus"

PRED_COLUMNS = [
    "message_id",
    "keep_remove_label",
    "predicted_label",
    "is_remove",
]

def _build_messages(*, original_text: str, mirror_text: str, message_id: str, seed: int) -> list[dict]:
    # Deterministic Post 1 / Post 2 blinding; builder only formats numbered JSON.
    stimuli = [{"post": original_text}, {"post": mirror_text}]
    content = build_prompt_with_stimuli(
        system_prompt=prompt_module.SYSTEM_PROMPT,
        stimuli=stimuli,
        shuffle_stimuli=True,
    )
    return [{"role": "user", "content": content}]


def run_prompt_on_dataset(
    *,
    limit: int,
    seed: int,
    model: str,
    temperature: float,
    outputs_dir: Path,
) -> Path:
    outputs_dir.mkdir(parents=True, exist_ok=True)
    timestamp = get_current_timestamp()
    out_dir = outputs_dir / timestamp
    out_dir.mkdir(parents=True, exist_ok=False)

    (out_dir / "prompt_system.txt").write_text(prompt_module.SYSTEM_PROMPT, encoding="utf-8")
    (out_dir / "run_command.txt").write_text(json.dumps(sys.argv, indent=2), encoding="utf-8")

    df = Dataloader().load_training_dataframe()
    df = df.sample(n=min(limit, len(df)), random_state=seed).reset_index(drop=True)

    service = LLMService()
    predictions_path = out_dir / "predictions.csv"
    rows: list[dict] = []

    print(
        f"Running {len(df)} posts with model={model!r} via research_tools LLMService (Bedrock)",
        flush=True,
    )

    with predictions_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=PRED_COLUMNS)
        writer.writeheader()

        for i, row in df.iterrows():
            message_id = str(row["message_id"])
            messages = _build_messages(
                original_text=str(row["original_text"]),
                mirror_text=str(row["mirror_text"]),
                message_id=message_id,
                seed=seed,
            )
            result: IsRemoveResult = service.structured_completion(
                messages=messages,
                response_model=IsRemoveResult,
                model=model,
                temperature=temperature,
            )
            predicted_label = int(result.is_remove)
            y_true = int(row["keep_remove_label"])
            out_row = {
                "message_id": message_id,
                "keep_remove_label": y_true,
                "predicted_label": predicted_label,
                "is_remove": result.is_remove,
            }
            writer.writerow(out_row)
            f.flush()
            rows.append(out_row)
            print(
                f"[{i + 1}/{len(df)}] message_id={message_id} "
                f"y_true={y_true} y_pred={predicted_label}",
                flush=True,
            )

    n_correct = sum(1 for r in rows if int(r["keep_remove_label"]) == int(r["predicted_label"]))
    metadata = {
        "timestamp": timestamp,
        "model": model,
        "provider": "bedrock",
        "seed": seed,
        "limit": limit,
        "n_rows": len(rows),
        "n_correct": n_correct,
        "accuracy": (n_correct / len(rows)) if rows else None,
        "predictions_path": str(predictions_path),
    }
    (out_dir / "metadata.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    print(json.dumps(metadata, indent=2), flush=True)
    return out_dir


@app.command()
def main(
    limit: int = typer.Option(5, "--limit", min=1, help="Number of posts to score."),
    seed: int = typer.Option(42, "--seed"),
    model: str = typer.Option(DEFAULT_BEDROCK_MODEL, "--model"),
    temperature: float = typer.Option(0.0, "--temperature"),
    outputs_dir: Optional[Path] = typer.Option(None, "--outputs-dir"),
) -> None:
    run_prompt_on_dataset(
        limit=limit,
        seed=seed,
        model=model,
        temperature=temperature,
        outputs_dir=outputs_dir or _OUTPUTS_DIR,
    )


if __name__ == "__main__":
    app()
