from __future__ import annotations

import json
from pathlib import Path

import typer

from experiments.predict_keep_remove_2026_05_07.dataloader import Dataloader
from experiments.predict_keep_remove_2026_05_07.models.load_model import load_model
from lib.timestamp_utils import get_current_timestamp

app = typer.Typer(add_completion=False, no_args_is_help=True)
DEFAULT_RANDOM_SEED = 42


@app.command()
def train_model(
    model: str = typer.Option(
        ...,
        "--model",
        help="Model strategy to train (e.g., logistic_regression).",
    ),
    train_split: float = typer.Option(
        0.8,
        "--train-split",
        min=0.01,
        max=0.99,
        help="Train-set fraction for train/test split.",
    ),
    seed: int = typer.Option(
        DEFAULT_RANDOM_SEED,
        "--seed",
        help="Random seed for reproducible splits/training.",
    ),
) -> None:
    """Train a keep/remove model and save outputs under timestamped folder."""
    timestamp = get_current_timestamp()
    output_dir = (
        Path(__file__).resolve().parent / "models" / "outputs" / timestamp
    )
    output_dir.mkdir(parents=True, exist_ok=False)

    dataloader = Dataloader()
    train_df, test_df = dataloader.generate_train_test_split(
        train_split=train_split,
        random_state=seed,
    )

    model_strategy = load_model(model)
    if hasattr(model_strategy, "random_state"):
        setattr(model_strategy, "random_state", seed)
    result = model_strategy.train(
        train_df,
        test_df,
        output_dir=output_dir,
        target_column=Dataloader.TARGET_COLUMN,
    )

    metadata = {
        "timestamp": timestamp,
        "model": model,
        "train_split": train_split,
        "seed": seed,
        "target_column": Dataloader.TARGET_COLUMN,
        "train_rows": int(len(train_df)),
        "test_rows": int(len(test_df)),
        "result": result,
    }
    metadata_path = output_dir / "metadata.json"
    metadata_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")

    print(f"Output directory: {output_dir}")
    print(f"Metadata: {metadata_path}")
    print("Train metrics:")
    for key, value in result["train_metrics"].items():
        print(f"  - {key}: {value:.6f}")
    print("Test metrics:")
    for key, value in result["test_metrics"].items():
        print(f"  - {key}: {value:.6f}")


if __name__ == "__main__":
    app()
