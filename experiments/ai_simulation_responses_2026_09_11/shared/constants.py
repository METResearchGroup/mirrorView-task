"""Pinned constants for the AI simulation responses experiment."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Literal

POSTS_PER_USER = 20
COHORT_CAP = 1000
SMOKE_USER_COUNT = 10
BEDROCK_MAX_TOKENS = 256

STUDY_S3_BUCKET = "jspsych-mirror-view-2026-09-09"
STUDY_S3_PREFIX = "data/prolific/"
STUDY_SINCE_DATE = date(2026, 9, 9)

OUTPUT_S3_BUCKET = "mirrorview-experimental-artifacts"
EXPERIMENT_S3_PREFIX = "experiments/ai_simulation_responses_2026_09_11/"

COHORT_USERS_KEY = f"{EXPERIMENT_S3_PREFIX}shared/cohort_users.parquet"
COHORT_TRIALS_KEY = f"{EXPERIMENT_S3_PREFIX}shared/cohort_trials.parquet"

OPENAI_MODEL_ID = "gpt-5.4-nano"
BEDROCK_MICRO_NOVA_MODEL_ID = "us.amazon.nova-micro-v1:0"
BEDROCK_QWEN_MODEL_ID = "qwen.qwen3-32b-v1:0"
BEDROCK_CLAUDE_MODEL_ID = "us.anthropic.claude-sonnet-4-6"

MODEL_FOLDER_OPENAI = "openai"
MODEL_FOLDER_BEDROCK_MICRO_NOVA = "bedrock_micro_nova"
MODEL_FOLDER_BEDROCK_QWEN = "bedrock_qwen"
MODEL_FOLDER_BEDROCK_CLAUDE = "bedrock_claude"

EngineKind = Literal["openai", "bedrock"]


@dataclass(frozen=True)
class CohortUser:
    """One complete participant in the shared cohort."""

    prolific_id: str
    participant_id: str
    source_file_epoch_ms: int
    party_group: str
    age: str
    gender: str
    education: str
    political_affiliation: str
    party_lean: str
    political_ideology: str
    political_follow: str
    rep_id: str
    dem_id: str
    attitude_reduce_abortion: str
    attitude_citizenship_undocumented: str
    attitude_restrict_guns: str
    attitude_regulate_environment: str
    attitude_raise_wealth_taxes: str
    attitude_expand_medicaid: str
    phase1_pair_reflection_text: str
    phase1_pair_influence_rating: int


@dataclass(frozen=True)
class CohortTrial:
    """One linked-fate trial row for a cohort participant."""

    prolific_id: str
    pair_index: int
    post_id: str
    original_text: str
    mirror_text: str
    pair_order: tuple[str, str]
    gold_remove: int
    sampled_stance: str
    sample_toxicity_type: str
    trial_index: int


@dataclass(frozen=True)
class ModelSpec:
    """One labeling model configuration."""

    folder: str
    engine_kind: EngineKind
    model_id: str


@dataclass(frozen=True)
class CostRow:
    """One row in the cost estimate table."""

    model: str
    estimated_tokens_in: int
    estimated_tokens_out: int
    median_cost_usd: float
    low_cost_usd: float
    high_cost_usd: float
