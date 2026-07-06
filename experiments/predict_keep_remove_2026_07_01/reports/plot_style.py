"""Shared styling and label helpers for results figures."""

from __future__ import annotations

from dataclasses import dataclass

METRIC_ORDER = ["Accuracy", "Precision", "Recall", "F1"]

MODEL_CLASS_COLORS = {
    "Baseline": "#1f77b4",
    "Logistic regression": "#ff7f0e",
    "XGBoost": "#2ca02c",
}
DEFAULT_MODEL_COLOR = "#7f7f7f"

ABLATION_BAR_COLORS = {
    "baseline": "#9e9e9e",
    "only original post embedding": "#2ca02c",
    "difference embedding": "#ff7f0e",
}
DEFAULT_ABLATION_COLOR = "#7f7f7f"


@dataclass(frozen=True)
class SeriesPoint:
    metric: str
    value: float


@dataclass(frozen=True)
class PlotSeries:
    label: str
    model_class: str
    training_type: str
    linestyle: str
    color: str
    points: tuple[SeriesPoint, ...]

    def y_values_in_order(self) -> list[float]:
        m_to_v = {p.metric: p.value for p in self.points}
        return [float(m_to_v[m]) for m in METRIC_ORDER]


def model_class_from_model_name(model_name: str) -> str:
    n = model_name.lower()
    if n.startswith("baseline"):
        return "Baseline"
    if "logistic regression" in n:
        return "Logistic regression"
    if "xgboost" in n:
        return "XGBoost"
    return model_name


def ablation_model_class_from_model_name(model_name: str) -> str:
    n = model_name.lower()
    if "logistic regression" in n:
        return "Logistic regression"
    if "xgboost" in n:
        return "XGBoost"
    return model_name


def ablation_variant_from_model_name(model_name: str) -> str:
    n = model_name.lower()
    if "difference embedding" in n:
        return "difference embedding"
    if "only original" in n:
        return "only original post embedding"
    if "baseline" in n:
        return "baseline"
    if "original post" in n and "mirrored post" in n and "embedding" in n:
        return "baseline"
    return "variant"


def ablation_bar_color(variant: str) -> str:
    return ABLATION_BAR_COLORS.get(variant, DEFAULT_ABLATION_COLOR)


def ablation_variant_label(variant: str) -> str:
    if variant == "baseline":
        return "Original post + mirrored post embeddings"
    if variant == "only original post embedding":
        return "Only original post embedding"
    if variant == "difference embedding":
        return "Difference embedding (orig_emb - mirror_emb)"
    return variant


def training_type_linestyle(training_type: str) -> str:
    if training_type == "feature_engineering":
        return "dashed"
    if training_type == "text_embeddings":
        return "solid"
    raise ValueError(f"Unknown training_type: {training_type}")
