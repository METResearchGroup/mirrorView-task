"""Head-only ModernBERT-base keep/remove classifier training.

Supports local runs (in-process dataloader) and SageMaker channel CSVs
(``SM_CHANNEL_TRAIN`` / ``SM_CHANNEL_VAL`` / ``SM_CHANNEL_TEST``).

Run from root::

    PYTHONPATH=. uv run --extra modernbert-training python \\
      experiments/predict_keep_remove_2026_07_01/models/modernbert/train.py \\
      --config experiments/predict_keep_remove_2026_07_01/models/modernbert/configs/modernbert_base.yaml
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import torch
import torch.nn as nn
import yaml
from datasets import Dataset
from sklearn.metrics import (
    accuracy_score,
    average_precision_score,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from transformers import (
    AutoModelForSequenceClassification,
    AutoTokenizer,
    Trainer,
    TrainingArguments,
)

PACKAGE_DIR = Path(__file__).resolve().parent
DEFAULT_THRESHOLD = 0.5
PREDICTION_COLUMNS = [
    "message_id",
    "keep_remove_label",
    "predicted_label",
    "predicted_remove_probability",
]


def _classification_metrics_summary(
    y_true: Any,
    y_pred: Any,
    pos_scores: Any,
) -> dict[str, float]:
    """Metrics helper; prefers shared experiment implementation when available."""
    try:
        from experiments.simplified_predict_remove_2026_05_13.features import (
            classification_metrics_summary,
        )

        return classification_metrics_summary(y_true, y_pred, pos_scores)
    except ImportError:
        y_t = np.asarray(y_true).astype(np.int64)
        y_p = np.asarray(y_pred).astype(np.int64)
        s = np.asarray(pos_scores).astype(np.float64)
        out: dict[str, float] = {
            "accuracy": float(accuracy_score(y_t, y_p)),
            "precision": float(precision_score(y_t, y_p, zero_division=0)),
            "recall": float(recall_score(y_t, y_p, zero_division=0)),
            "f1": float(f1_score(y_t, y_p, zero_division=0)),
        }

        def _maybe(fn: Any) -> float:
            try:
                return float(fn())
            except ValueError:
                return float("nan")

        out["roc_auc"] = _maybe(lambda: roc_auc_score(y_t, s))
        out["pr_auc"] = _maybe(lambda: average_precision_score(y_t, s))
        cm = confusion_matrix(y_t, y_p, labels=[0, 1])
        tn, fp, fn, tp = cm.ravel().tolist()
        out["confusion_matrix_tn"] = float(tn)
        out["confusion_matrix_fp"] = float(fp)
        out["confusion_matrix_fn"] = float(fn)
        out["confusion_matrix_tp"] = float(tp)
        return out


def _get_current_timestamp() -> str:
    try:
        from lib.timestamp_utils import get_current_timestamp

        return get_current_timestamp()
    except ImportError:
        return datetime.now(timezone.utc).strftime("%Y_%m_%d-%H:%M:%S")


def _load_wandb_api_key() -> str:
    try:
        from lib.load_env_vars import EnvVarsContainer

        return EnvVarsContainer.get_env_var("WANDB_API_KEY", required=True)
    except ImportError:
        key = os.environ.get("WANDB_API_KEY", "").strip()
        if not key:
            raise ValueError(
                "WANDB_API_KEY is required but is missing. "
                "Please set the WANDB_API_KEY environment variable."
            )
        return key


def _load_config(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    if not isinstance(cfg, dict):
        raise ValueError(f"Config must be a mapping: {path}")
    return cfg


def _read_split_csv(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    required = {"message_id", "text", "label", "keep_remove_label"}
    missing = required - set(df.columns)
    if missing:
        raise KeyError(f"Split CSV {path} missing columns: {sorted(missing)}")
    df = df.copy()
    df["message_id"] = df["message_id"].astype(str)
    df["text"] = df["text"].fillna("").astype(str)
    df["label"] = df["label"].astype(int)
    df["keep_remove_label"] = df["keep_remove_label"].astype(int)
    return df


def _load_splits_from_sagemaker_channels() -> (
    tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame] | None
):
    train_ch = os.environ.get("SM_CHANNEL_TRAIN")
    val_ch = os.environ.get("SM_CHANNEL_VAL")
    test_ch = os.environ.get("SM_CHANNEL_TEST")
    if not (train_ch and val_ch and test_ch):
        return None

    def _one(channel: str, name: str) -> pd.DataFrame:
        channel_path = Path(channel)
        csv_path = channel_path / f"{name}.csv"
        if not csv_path.is_file():
            candidates = sorted(channel_path.glob("*.csv"))
            if len(candidates) == 1:
                csv_path = candidates[0]
            else:
                raise FileNotFoundError(
                    f"Expected {name}.csv under SageMaker channel {channel_path}"
                )
        return _read_split_csv(csv_path)

    return _one(train_ch, "train"), _one(val_ch, "val"), _one(test_ch, "test")


def _load_splits_local(cfg: dict[str, Any], limit: int | None) -> (
    tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]
):
    # Local path needs repo PYTHONPATH; SageMaker uses channel CSVs instead.
    from experiments.predict_keep_remove_2026_07_01.models.modernbert.dataloader import (
        load_classifier_dataframe,
        make_train_val_test_split,
    )

    df = load_classifier_dataframe()
    if limit is not None:
        if limit < 1:
            raise ValueError("--limit must be >= 1")
        df = df.sample(
            n=min(limit, len(df)),
            random_state=int(cfg["random_state"]),
        ).reset_index(drop=True)

    return make_train_val_test_split(
        df,
        train_fraction=float(cfg["train_fraction"]),
        val_fraction=float(cfg["val_fraction"]),
        test_fraction=float(cfg["test_fraction"]),
        seed=int(cfg["random_state"]),
        label_column=str(cfg["label_col"]),
    )


def _apply_limit_to_splits(
    train_df: pd.DataFrame,
    val_df: pd.DataFrame,
    test_df: pd.DataFrame,
    limit: int,
    seed: int,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Proportionally subsample splits when --limit is set on channel data."""
    total = len(train_df) + len(val_df) + len(test_df)
    if limit >= total:
        return train_df, val_df, test_df
    train_n = max(1, int(round(limit * len(train_df) / total)))
    val_n = max(1, int(round(limit * len(val_df) / total)))
    test_n = max(1, limit - train_n - val_n)
    if test_n < 1:
        test_n = 1
        if train_n > 1:
            train_n -= 1
    return (
        train_df.sample(n=min(train_n, len(train_df)), random_state=seed).reset_index(
            drop=True
        ),
        val_df.sample(n=min(val_n, len(val_df)), random_state=seed).reset_index(
            drop=True
        ),
        test_df.sample(n=min(test_n, len(test_df)), random_state=seed).reset_index(
            drop=True
        ),
    )


def _freeze_non_classifier(model: Any) -> tuple[int, int]:
    trainable = 0
    total = 0
    for name, param in model.named_parameters():
        total += param.numel()
        if "classifier" not in name:
            param.requires_grad = False
        if param.requires_grad:
            trainable += param.numel()
    return trainable, total


class WeightedTrainer(Trainer):
    """Trainer with fixed class-weighted cross-entropy (keep, remove)."""

    def __init__(self, *args: Any, class_weights: torch.Tensor, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.class_weights = class_weights

    def compute_loss(
        self,
        model: Any,
        inputs: dict[str, Any],
        return_outputs: bool = False,
        num_items_in_batch: int | None = None,
    ) -> Any:
        labels = inputs.pop("labels")
        outputs = model(**inputs)
        logits = outputs.logits
        weight = self.class_weights.to(device=logits.device, dtype=logits.dtype)
        loss_fct = nn.CrossEntropyLoss(weight=weight)
        loss = loss_fct(logits.view(-1, model.config.num_labels), labels.view(-1))
        return (loss, outputs) if return_outputs else loss


def _tokenize_dataframe(
    df: pd.DataFrame,
    tokenizer: Any,
    *,
    text_col: str,
    label_col: str,
    max_length: int,
) -> Dataset:
    texts = df[text_col].tolist()
    labels = df[label_col].astype(int).tolist()
    encodings = tokenizer(
        texts,
        truncation=True,
        padding="max_length",
        max_length=max_length,
    )
    encodings["labels"] = labels
    return Dataset.from_dict(encodings)


def _predict_remove_proba(trainer: Trainer, dataset: Dataset) -> np.ndarray:
    pred_out = trainer.predict(dataset)
    logits = pred_out.predictions
    if isinstance(logits, tuple):
        logits = logits[0]
    logits_t = torch.tensor(logits, dtype=torch.float32)
    probs = torch.softmax(logits_t, dim=-1).numpy()
    return probs[:, 1]


def _write_predictions_csv(
    df: pd.DataFrame,
    remove_proba: np.ndarray,
    path: Path,
    *,
    threshold: float = DEFAULT_THRESHOLD,
) -> pd.DataFrame:
    out = pd.DataFrame(
        {
            "message_id": df["message_id"].astype(str).values,
            "keep_remove_label": df["keep_remove_label"].astype(int).values,
            "predicted_label": (remove_proba >= threshold).astype(int),
            "predicted_remove_probability": remove_proba.astype(float),
        }
    )
    out = out[PREDICTION_COLUMNS]
    out.to_csv(path, index=False)
    return out


def _resolve_run_dir(cfg: dict[str, Any], timestamp: str) -> Path:
    sm_model_dir = os.environ.get("SM_MODEL_DIR")
    if sm_model_dir:
        run_dir = Path(sm_model_dir)
        run_dir.mkdir(parents=True, exist_ok=True)
        return run_dir

    output_dir = Path(str(cfg["output_dir"]))
    if not output_dir.is_absolute():
        output_dir = PACKAGE_DIR / output_dir
    run_dir = output_dir / timestamp
    run_dir.mkdir(parents=True, exist_ok=False)
    return run_dir


def _build_training_arguments(
    cfg: dict[str, Any],
    *,
    run_dir: Path,
    num_train_epochs: float,
) -> TrainingArguments:
    kwargs: dict[str, Any] = {
        "output_dir": str(run_dir / "trainer_checkpoints"),
        "learning_rate": float(cfg["learning_rate"]),
        "num_train_epochs": float(num_train_epochs),
        "per_device_train_batch_size": int(cfg["per_device_train_batch_size"]),
        "per_device_eval_batch_size": int(cfg["per_device_eval_batch_size"]),
        "weight_decay": float(cfg["weight_decay"]),
        "save_strategy": "epoch",
        "load_best_model_at_end": True,
        "metric_for_best_model": "eval_loss",
        "greater_is_better": False,
        "report_to": ["wandb"],
        "seed": int(cfg["random_state"]),
        "logging_strategy": "epoch",
        "save_total_limit": 1,
        "dataloader_pin_memory": False,
        "remove_unused_columns": False,
    }
    # transformers 4.46+ renamed evaluation_strategy -> eval_strategy
    try:
        return TrainingArguments(eval_strategy="epoch", **kwargs)
    except TypeError:
        return TrainingArguments(evaluation_strategy="epoch", **kwargs)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Train head-only ModernBERT keep/remove classifier."
    )
    parser.add_argument(
        "--config",
        required=True,
        help="Path to YAML config (e.g. configs/modernbert_base.yaml).",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Optional row cap for smoke runs.",
    )
    parser.add_argument(
        "--num-train-epochs",
        type=float,
        default=None,
        help="Optional override for num_train_epochs (smoke).",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)
    config_path = Path(args.config)
    if not config_path.is_file():
        # Allow config paths relative to package dir (SageMaker).
        alt = PACKAGE_DIR / args.config
        if alt.is_file():
            config_path = alt
        else:
            raise FileNotFoundError(f"Config not found: {args.config}")

    cfg = _load_config(config_path)
    wandb_key = _load_wandb_api_key()
    os.environ["WANDB_API_KEY"] = wandb_key

    timestamp = _get_current_timestamp()
    run_dir = _resolve_run_dir(cfg, timestamp)

    channel_splits = _load_splits_from_sagemaker_channels()
    if channel_splits is not None:
        train_df, val_df, test_df = channel_splits
        if args.limit is not None:
            train_df, val_df, test_df = _apply_limit_to_splits(
                train_df,
                val_df,
                test_df,
                limit=int(args.limit),
                seed=int(cfg["random_state"]),
            )
    else:
        train_df, val_df, test_df = _load_splits_local(cfg, args.limit)

    num_train_epochs = (
        float(args.num_train_epochs)
        if args.num_train_epochs is not None
        else float(cfg["num_train_epochs"])
    )

    import wandb

    wandb_entity = cfg.get("wandb_entity")
    init_kwargs: dict[str, Any] = {
        "project": str(cfg["wandb_project"]),
        "name": f"modernbert-base-{timestamp}",
        "config": {
            **{k: v for k, v in cfg.items() if k != "sagemaker"},
            "num_train_epochs": num_train_epochs,
            "limit": args.limit,
            "run_dir": str(run_dir),
        },
    }
    if wandb_entity:
        init_kwargs["entity"] = wandb_entity
    wandb_run = wandb.init(**init_kwargs)

    model_name = str(cfg["model_name"])
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    # ModernBERT defaults to FlashAttention (Ampere+ only). Use SDPA so
    # SageMaker ml.g4dn.xlarge (T4 / Turing) can train.
    model = AutoModelForSequenceClassification.from_pretrained(
        model_name,
        num_labels=2,
        attn_implementation="sdpa",
    )

    trainable_param_count = 0
    total_param_count = sum(p.numel() for p in model.parameters())
    if bool(cfg.get("freeze_encoder", True)):
        trainable_param_count, total_param_count = _freeze_non_classifier(model)
    else:
        trainable_param_count = total_param_count

    text_col = str(cfg["text_col"])
    label_col = str(cfg["label_col"])
    max_length = int(cfg["max_length"])

    train_ds = _tokenize_dataframe(
        train_df, tokenizer, text_col=text_col, label_col=label_col, max_length=max_length
    )
    val_ds = _tokenize_dataframe(
        val_df, tokenizer, text_col=text_col, label_col=label_col, max_length=max_length
    )
    test_ds = _tokenize_dataframe(
        test_df, tokenizer, text_col=text_col, label_col=label_col, max_length=max_length
    )

    class_weights = torch.tensor(
        [float(cfg["class_weight_keep"]), float(cfg["class_weight_remove"])],
        dtype=torch.float32,
    )

    training_args = _build_training_arguments(
        cfg, run_dir=run_dir, num_train_epochs=num_train_epochs
    )

    trainer = WeightedTrainer(
        model=model,
        args=training_args,
        train_dataset=train_ds,
        eval_dataset=val_ds,
        class_weights=class_weights,
    )

    trainer.train()

    train_proba = _predict_remove_proba(trainer, train_ds)
    val_proba = _predict_remove_proba(trainer, val_ds)
    test_proba = _predict_remove_proba(trainer, test_ds)

    train_pred = (train_proba >= DEFAULT_THRESHOLD).astype(int)
    val_pred = (val_proba >= DEFAULT_THRESHOLD).astype(int)
    test_pred = (test_proba >= DEFAULT_THRESHOLD).astype(int)

    train_metrics = _classification_metrics_summary(
        train_df[label_col].astype(int).values, train_pred, train_proba
    )
    val_metrics = _classification_metrics_summary(
        val_df[label_col].astype(int).values, val_pred, val_proba
    )
    test_metrics = _classification_metrics_summary(
        test_df[label_col].astype(int).values, test_pred, test_proba
    )

    _write_predictions_csv(train_df, train_proba, run_dir / "train_predictions.csv")
    _write_predictions_csv(val_df, val_proba, run_dir / "val_predictions.csv")
    _write_predictions_csv(test_df, test_proba, run_dir / "test_predictions.csv")

    metrics_blob = {
        "train_metrics": train_metrics,
        "val_metrics": val_metrics,
        "test_metrics": test_metrics,
    }
    (run_dir / "metrics.json").write_text(
        json.dumps(metrics_blob, indent=2),
        encoding="utf-8",
    )

    metadata = {
        "timestamp": timestamp,
        "seed": int(cfg["random_state"]),
        "random_state": int(cfg["random_state"]),
        "train_fraction": float(cfg["train_fraction"]),
        "val_fraction": float(cfg["val_fraction"]),
        "test_fraction": float(cfg["test_fraction"]),
        "train_rows": int(len(train_df)),
        "val_rows": int(len(val_df)),
        "test_rows": int(len(test_df)),
        "model_name": model_name,
        "freeze_encoder": bool(cfg.get("freeze_encoder", True)),
        "trainable_param_count": int(trainable_param_count),
        "total_param_count": int(total_param_count),
        "class_weight_keep": float(cfg["class_weight_keep"]),
        "class_weight_remove": float(cfg["class_weight_remove"]),
        "command": list(sys.argv),
        "label_encoding": {"0": "keep", "1": "remove"},
        "wandb_run_id": getattr(wandb_run, "id", None),
        "wandb_project": str(cfg["wandb_project"]),
        "s3_uri": os.environ.get("SM_OUTPUT_DATA_DIR"),
        "threshold": DEFAULT_THRESHOLD,
        "limit": args.limit,
        "num_train_epochs": num_train_epochs,
    }
    (run_dir / "metadata.json").write_text(
        json.dumps(metadata, indent=2),
        encoding="utf-8",
    )

    trainer.save_model(str(run_dir))
    tokenizer.save_pretrained(str(run_dir))

    # Persist trainer_state.json at run root when present under checkpoints.
    state_candidates = list((run_dir / "trainer_checkpoints").glob("*/trainer_state.json"))
    latest_state = run_dir / "trainer_checkpoints" / "trainer_state.json"
    if latest_state.is_file():
        (run_dir / "trainer_state.json").write_text(
            latest_state.read_text(encoding="utf-8"),
            encoding="utf-8",
        )
    elif state_candidates:
        newest = max(state_candidates, key=lambda p: p.stat().st_mtime)
        (run_dir / "trainer_state.json").write_text(
            newest.read_text(encoding="utf-8"),
            encoding="utf-8",
        )
    elif hasattr(trainer, "state") and trainer.state is not None:
        (run_dir / "trainer_state.json").write_text(
            json.dumps(trainer.state.to_dict(), indent=2),
            encoding="utf-8",
        )

    wandb.log(
        {
            "final/train_f1": train_metrics["f1"],
            "final/val_f1": val_metrics["f1"],
            "final/test_f1": test_metrics["f1"],
            "final/test_accuracy": test_metrics["accuracy"],
            "final/test_precision": test_metrics["precision"],
            "final/test_recall": test_metrics["recall"],
        }
    )
    wandb.finish()

    print(f"Output directory: {run_dir}")
    print("Test metrics:", json.dumps(test_metrics, indent=2))


if __name__ == "__main__":
    main()
