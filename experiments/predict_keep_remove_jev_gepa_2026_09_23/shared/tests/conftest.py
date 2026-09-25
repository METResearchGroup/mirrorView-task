"""Shared fixtures for predict keep/remove Jev and GEPA tests."""

from __future__ import annotations

import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pandas as pd
import pytest
from typesafe_sdk import Noul

_REPO_ROOT = Path(__file__).resolve().parents[4]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))


def trial_row(
    *,
    trial_type: str = "moderation-trial",
    trial_index: int = 1,
    time_elapsed: float = 10.0,
    post_id: str = "P1",
    prolific_id: str = "W1",
    decision: str = "keep",
    original_text: str = "original",
    mirror_text: str = "mirror",
    sampled_stance: str = "left",
    sample_toxicity_type: str = "low",
    evaluation_mode: str = "linked_fate",
) -> dict[str, object]:
    """Build one Part 3 trial row for unit tests."""
    return {
        "trial_type": trial_type,
        "trial_index": trial_index,
        "time_elapsed": time_elapsed,
        "post_id": post_id,
        "prolific_id": prolific_id,
        "decision": decision,
        "original_text": original_text,
        "mirror_text": mirror_text,
        "sampled_stance": sampled_stance,
        "sample_toxicity_type": sample_toxicity_type,
        "evaluation_mode": evaluation_mode,
    }


@pytest.fixture
def mixed_trials() -> pd.DataFrame:
    """Synthetic trials covering unanimous, majority, tie, and filter edge cases."""
    rows = [
        trial_row(post_id="P1", prolific_id="W1", decision="keep", trial_index=1),
        trial_row(post_id="P1", prolific_id="W2", decision="keep", trial_index=1),
        trial_row(post_id="P1", prolific_id="W3", decision="keep", trial_index=1),
        trial_row(post_id="P1", prolific_id="W4", decision="keep", trial_index=1),
        trial_row(post_id="P2", prolific_id="W1", decision="remove", trial_index=1),
        trial_row(post_id="P2", prolific_id="W2", decision="remove", trial_index=1),
        trial_row(post_id="P2", prolific_id="W3", decision="remove", trial_index=1),
        trial_row(post_id="P2", prolific_id="W4", decision="keep", trial_index=1),
        trial_row(post_id="P3", prolific_id="W1", decision="keep", trial_index=1),
        trial_row(post_id="P3", prolific_id="W2", decision="keep", trial_index=1),
        trial_row(post_id="P3", prolific_id="W3", decision="remove", trial_index=1),
        trial_row(post_id="P3", prolific_id="W4", decision="remove", trial_index=1),
        trial_row(post_id="P4", prolific_id="W1", decision="keep", trial_index=1),
        trial_row(post_id="P4", prolific_id="W2", decision="keep", trial_index=1),
        trial_row(
            post_id="P5",
            prolific_id="W",
            decision="keep",
            trial_index=1,
            time_elapsed=10.0,
        ),
        trial_row(
            post_id="P5",
            prolific_id="W",
            decision="keep",
            trial_index=5,
            time_elapsed=10.0,
        ),
        trial_row(
            trial_type="moderation-practice",
            post_id="P6",
            prolific_id="W9",
            decision="keep",
        ),
        trial_row(post_id="", prolific_id="W10", decision="keep"),
    ]
    return pd.DataFrame(rows)


@dataclass
class FakeUsage:
    input_tokens: int = 0
    output_tokens: int = 0


@dataclass
class FakeAnswer:
    noul: float


@dataclass
class FakeSystemOneResponse:
    answers: dict[str, FakeAnswer]
    usage: FakeUsage
    model: str = "jev-1.13.0"


@dataclass
class FakeTypeSafeClient:
    """Records system_one calls and returns configurable answers without network."""

    answers: dict[int, float] = field(default_factory=dict)
    usage: FakeUsage = field(default_factory=lambda: FakeUsage(input_tokens=100, output_tokens=10))
    calls: list[dict[str, Any]] = field(default_factory=list)
    fail_times: int = 0
    fail_with: Exception | None = None
    call_count: int = 0

    def system_one(
        self,
        state: dict[str, list[str]],
        questions: dict[str, Noul],
        *,
        model: str | None = None,
        **kwargs: Any,
    ) -> FakeSystemOneResponse:
        self.calls.append({"state": state, "questions": questions, "model": model, **kwargs})
        self.call_count += 1
        if self.fail_with is not None and self.call_count <= self.fail_times:
            raise self.fail_with
        built_answers = {}
        for question_id in sorted(questions):
            index = int(question_id.split("_", maxsplit=1)[1])
            built_answers[question_id] = FakeAnswer(noul=self.answers.get(index, 0.5))
        return FakeSystemOneResponse(answers=built_answers, usage=self.usage, model=model or "jev-1.13.0")
