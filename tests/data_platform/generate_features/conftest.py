from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any, Literal
from unittest.mock import MagicMock

import pandas as pd
import pytest
from pydantic import BaseModel

from data_platform.generate_features.is_news_or_opinion.generate_feature import (
    IsNewsOrOpinionModel,
    LlmIsNewsOrOpinionModel,
    SYSTEM_PROMPT as IS_NEWS_OR_OPINION_SYSTEM_PROMPT,
)
from data_platform.generate_features.models import (
    FeatureGenerationConfig,
    FeatureRunConfig,
    FeatureSpec,
)
from data_platform.utils.feature_labels import FeatureLabelQuery
from data_platform.utils.storage import BlueskyStorageManager, StorageManager
from tests.data_platform.constants import (
    FEATURES_DATASET_ID,
    LABEL_TIMESTAMP,
    PREPROCESSED_RUN_DIR,
    URI_POST_A,
    URI_POST_B,
)

HTTP_OK_STATUS_CODE = 200
DEFAULT_PROMPT_TOKENS = 10
DEFAULT_COMPLETION_TOKENS = 2


class DummyModel:
    @staticmethod
    def model_fields() -> dict:
        return {"source_record_id": None, "label_timestamp": None, "x": None}

    @staticmethod
    def model_validate(row: dict) -> DummyModel:
        return DummyModel()


class TinyLlmOut(BaseModel):
    score: bool


class TinyRowModel(BaseModel):
    source_record_id: str
    label_timestamp: str
    score: bool


def make_openai_news_spec() -> FeatureSpec:
    return FeatureSpec(
        name="is_news_or_opinion",
        model=IsNewsOrOpinionModel,
        engine_type="openai",
        system_prompt=IS_NEWS_OR_OPINION_SYSTEM_PROMPT,
        llm_output_schema=LlmIsNewsOrOpinionModel,
    )


def make_openai_batch_output_line(
    custom_id: str,
    category: Literal["news", "opinion", "neither"],
    prompt_tokens: int = DEFAULT_PROMPT_TOKENS,
    completion_tokens: int = DEFAULT_COMPLETION_TOKENS,
    status_code: int = HTTP_OK_STATUS_CODE,
    error: str | None = None,
) -> str:
    content = json.dumps({"category": category})
    return json.dumps(
        {
            "custom_id": custom_id,
            "response": {
                "status_code": status_code,
                "body": {
                    "id": f"chatcmpl-{custom_id}",
                    "object": "chat.completion",
                    "created": 1,
                    "model": "gpt-5.4-nano",
                    "choices": [
                        {
                            "index": 0,
                            "finish_reason": "stop",
                            "message": {
                                "role": "assistant",
                                "content": content,
                                "refusal": None,
                            },
                        }
                    ],
                    "usage": {
                        "prompt_tokens": prompt_tokens,
                        "completion_tokens": completion_tokens,
                        "total_tokens": prompt_tokens + completion_tokens,
                    },
                },
            }
            if error is None
            else None,
            "error": None if error is None else {"message": error},
        }
    )


def make_completed_openai_client(
    output_text: str,
    error_text: str | None = None,
) -> MagicMock:
    client = MagicMock()
    uploaded = MagicMock()
    uploaded.id = "file_input"
    created_batch = MagicMock()
    created_batch.id = "batch_1"
    created_batch.status = "validating"
    created_batch.output_file_id = None
    completed_batch = MagicMock()
    completed_batch.id = "batch_1"
    completed_batch.status = "completed"
    completed_batch.output_file_id = "file_output"
    completed_batch.error_file_id = "file_error" if error_text is not None else None
    output_file = MagicMock()
    output_file.text = output_text
    error_file = MagicMock()
    error_file.text = error_text
    client.files.create.return_value = uploaded
    client.files.content.side_effect = (
        lambda file_id: error_file if file_id == "file_error" else output_file
    )
    client.batches.create.return_value = created_batch
    client.batches.retrieve.return_value = completed_batch
    return client


@pytest.fixture
def features_dir(data_root: Path) -> Path:
    path = data_root / "bluesky" / FEATURES_DATASET_ID / "features" / LABEL_TIMESTAMP
    path.mkdir(parents=True, exist_ok=True)
    return path


def make_feature_generation_config(
    features_dir: Path,
    *,
    dataset_id: str = FEATURES_DATASET_ID,
    feature_registry: dict[str, FeatureSpec] | None = None,
    run_config: FeatureRunConfig | None = None,
) -> FeatureGenerationConfig:
    return FeatureGenerationConfig(
        platform="bluesky",
        id_column="uri",
        text_column="text",
        feature_registry=feature_registry or {},
        input_storage=BlueskyStorageManager("preprocessed", dataset_id),
        features_dir=features_dir,
        feature_label_query=FeatureLabelQuery(
            feature_storage=StorageManager(
                "bluesky", "features", BaseModel, dataset_id, records_filename="features"
            )
        ),
        run_config=run_config or FeatureRunConfig(),
    )


def write_preprocessed_posts(
    data_root: Path,
    records: list[Mapping[str, Any]],
    *,
    dataset_id: str = FEATURES_DATASET_ID,
    run_dir_name: str = PREPROCESSED_RUN_DIR,
) -> Path:
    preprocessed_dir = data_root / "bluesky" / dataset_id / "preprocessed" / run_dir_name
    preprocessed_dir.mkdir(parents=True)
    pd.DataFrame(list(records)).to_csv(preprocessed_dir / "posts.csv", index=False)
    (preprocessed_dir / "metadata.json").write_text("{}", encoding="utf-8")
    return preprocessed_dir


@pytest.fixture
def mock_build_engine(monkeypatch: pytest.MonkeyPatch) -> MagicMock:
    mock_engine = MagicMock()
    monkeypatch.setattr(
        "data_platform.generate_features.generate_features.build_engine",
        lambda spec, run_config: mock_engine,
    )
    return mock_engine


def sample_preprocessed_records(
    count: int = 1,
) -> list[dict[str, str]]:
    uris = [URI_POST_A, URI_POST_B]
    texts = ["one", "two"]
    return [{"uri": uris[i], "text": texts[i]} for i in range(min(count, len(uris)))]
