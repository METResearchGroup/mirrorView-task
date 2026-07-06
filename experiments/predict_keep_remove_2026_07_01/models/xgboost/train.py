"""Train XGBoost on concat+cosine embedding features (07_01 run).

Run from repo root::

    PYTHONPATH=. uv run python experiments/predict_keep_remove_2026_07_01/models/xgboost/train.py

Mirrors `experiments/simplified_predict_remove_2026_05_13/models/xgboost/train.py`
but uses a simpler, fixed dense feature vector:
  x = concat([orig_emb, mirror_emb, cosine_similarity])
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import joblib
import pandas as pd
import typer

from experiments.predict_keep_remove_2026_07_01.data.dataloader import Dataloader
from experiments.predict_keep_remove_2026_07_01.embeddings.cache_loader import (
    load_embeddings_via_dynamodb_and_s3_with_cache,
)
from experiments.predict_keep_remove_2026_07_01.embeddings.features.concat_cosine import (
    ConcatCosineFeatureBuilder,
    build_xy_from_joined,
)
from experiments.simplified_predict_remove_2026_05_13.experiment_bedrock_embeddings import (
    BEDROCK_MODEL_ID,
    EMBEDDING_DIMENSIONS,
)
from experiments.simplified_predict_remove_2026_05_13.experiment_create_embedding_and_upload import (
    DYNAMODB_TABLE_NAME,
    S3_BUCKET,
)
from experiments.simplified_predict_remove_2026_05_13.features import (
    classification_metrics_summary,
    join_embeddings,
)
from experiments.simplified_predict_remove_2026_05_13.models.xgboost.model import (
    XGBoostKeepRemoveModel,
)
from experiments.simplified_predict_remove_2026_05_13.splits import make_train_test_split
from lib.timestamp_utils import get_current_timestamp

app = typer.Typer(add_completion=False, no_args_is_help=True)

_RUN_ROOT = Path(__file__).resolve().parent
_OUTPUTS_PARENT = _RUN_ROOT / "outputs"
_DEFAULT_CACHE_DIR = _RUN_ROOT.parent / "embedding_cache"


@app.command()
def main(
    train_split: float = typer.Option(0.8, "--train-split", min=0.01, max=0.99),
    seed: int = typer.Option(42, "--seed"),
    use_scale_pos_weight: bool = typer.Option(
        True,
        "--scale-pos-weight/--no-scale-pos-weight",
        help="Set XGBoost scale_pos_weight=n_negative/n_positive.",
    ),
    embedding_normalize: bool = typer.Option(
        True,
        "--embedding-normalize/--no-embedding-normalize",
    ),
    s3_bucket: str | None = typer.Option(None, "--s3-bucket"),
    dynamodb_table: str | None = typer.Option(None, "--ddb-table"),
    embedding_cache_dir: str | None = typer.Option(
        str(_DEFAULT_CACHE_DIR),
        "--embedding-cache-dir",
        help="Local cache directory for embedding vectors.",
    ),
) -> None:
    timestamp = get_current_timestamp()
    out_dir = _OUTPUTS_PARENT / timestamp
    out_dir.mkdir(parents=True, exist_ok=False)
    cmd_parts = sys.argv.copy()

    print("Loading training dataframe...")
    # Canonical training dataframe (one row per post_id/message_id).
    df = Dataloader().load_training_dataframe()
    df = df.copy()
    if "message_id" not in df.columns:
        raise KeyError("Expected `message_id` column from 07_01 dataloader.")
    print(f"Loaded training dataframe: rows={len(df)}")

    # The simplified embedding-join helpers key everything by `post_id`.
    df_post = df.rename(columns={"message_id": "post_id"})

    print("Loading embeddings (local cache + tqdm progress)...")
    embedding_lookup, stats = load_embeddings_via_dynamodb_and_s3_with_cache(
        df_post,
        bucket=s3_bucket,
        table=dynamodb_table,
        normalize=embedding_normalize,
        model_id=BEDROCK_MODEL_ID,
        dimensions=EMBEDDING_DIMENSIONS,
        cache_dir=embedding_cache_dir,
    )
    print(
        "Embedding cache stats: "
        f"instances={stats.total_embedding_instances} hits={stats.cache_hits} misses={stats.cache_misses}"
    )

    print("Joining embeddings onto train/test split...")
    train_raw, test_raw = make_train_test_split(
        df_post,
        train_split=train_split,
        seed=seed,
    )

    train_df = join_embeddings(train_raw.copy(), embedding_lookup)
    test_df = join_embeddings(test_raw.copy(), embedding_lookup)

    print("Building fixed concat+cosine feature matrix...")
    prep = ConcatCosineFeatureBuilder().fit(train_df)
    X_train, y_train, feature_names_fit = build_xy_from_joined(train_df, prep)
    X_test, y_test, _ = build_xy_from_joined(test_df, prep)

    pos = max(1, int((y_train == 1).sum()))
    neg = max(1, int((y_train == 0).sum()))
    spw = float(neg / pos) if use_scale_pos_weight else None

    model = XGBoostKeepRemoveModel(
        random_state=seed,
        scale_pos_weight=spw,
    )
    print("Training the XGBoost model...")
    model.fit(X_train, y_train)
    print("Finished training the XGBoost model.")

    preds_train = model.predict(X_train)
    prob_train_rm = model.predict_proba(X_train)[:, 1]
    preds_test = model.predict(X_test)
    prob_test_rm = model.predict_proba(X_test)[:, 1]

    print("Computing train/test metrics...")
    train_metrics = classification_metrics_summary(y_train, preds_train, prob_train_rm)
    test_metrics = classification_metrics_summary(y_test, preds_test, prob_test_rm)

    print("Writing model artifacts and predictions...")
    joblib.dump(prep, out_dir / "preprocessor.pkl")
    model.save(out_dir / "model.pkl")

    fi = model.feature_importances()
    if len(fi) != len(feature_names_fit):
        raise RuntimeError(f"Feature importance length mismatch: fi={len(fi)} names={len(feature_names_fit)}")

    fi_df = pd.DataFrame({"feature": feature_names_fit, "importance": fi}).sort_values(
        "importance", ascending=False
    )
    fi_df.to_csv(out_dir / "feature_importances.csv", index=False)

    pred_df = test_df[["post_id", "keep_remove_label"]].copy()
    pred_df["predicted_label"] = preds_test.astype(int)
    pred_df["predicted_remove_probability"] = prob_test_rm
    pred_df.to_csv(out_dir / "test_predictions.csv", index=False)

    metadata = {
        "timestamp": timestamp,
        "seed": seed,
        "train_split": train_split,
        "train_rows": int(len(train_df)),
        "test_rows": int(len(test_df)),
        "xgboost_hyperparameters": {
            "scale_pos_weight": spw if use_scale_pos_weight else None,
            "computed_from_train_counts_positive": pos,
            "computed_from_train_counts_negative": neg,
        },
        "embedding_source": {
            "s3_bucket_default": S3_BUCKET,
            "ddb_table_default": DYNAMODB_TABLE_NAME,
            "embedding_model_id": BEDROCK_MODEL_ID,
            "embedding_dimensions": EMBEDDING_DIMENSIONS,
            "normalize_embeddings": embedding_normalize,
            "s3_override": s3_bucket,
            "ddb_override": dynamodb_table,
        },
        "feature_set_description": (
            "Fixed dense concat+cosine features: [orig_emb(d), mirror_emb(d), cosine_similarity(1)]."
        ),
        "label_encoding": {"keep_remove_label_0": "keep", "keep_remove_label_1": "remove"},
        "command": cmd_parts,
    }
    (out_dir / "metrics.json").write_text(
        json.dumps({"train_metrics": train_metrics, "test_metrics": test_metrics}, indent=2),
        encoding="utf-8",
    )
    (out_dir / "metadata.json").write_text(
        json.dumps(metadata, indent=2),
        encoding="utf-8",
    )

    print(f"Output directory: {out_dir}")
    print("Test metrics:", json.dumps(test_metrics, indent=2))


if __name__ == "__main__":
    app()

