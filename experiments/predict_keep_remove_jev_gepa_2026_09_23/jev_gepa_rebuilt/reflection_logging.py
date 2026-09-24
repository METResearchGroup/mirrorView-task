"""Reflection LM wrapper with per-call USD and token logging.

Run from the repo root:

    PYTHONPATH=. uv run pytest experiments/predict_keep_remove_jev_gepa_2026_09_23/jev_gepa_rebuilt/tests/test_reflection_logging.py -q
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from gepa.lm import LM

from experiments.predict_keep_remove_jev_gepa_2026_09_23.jev_gepa_rebuilt.constants import (
    REFLECTION_USD_PER_MILLION,
)
from experiments.predict_keep_remove_jev_gepa_2026_09_23.shared.pricing import estimate_reflection_cost_usd


class UsageLoggingLM(LM):
    """GEPA LM that appends per-call usage to JSONL and optional Wandb."""

    def __init__(
        self,
        model: str,
        *,
        usage_jsonl_path: Path,
        wandb_run: Any | None,
        **kwargs: Any,
    ) -> None:
        super().__init__(model, **kwargs)
        self._usage_jsonl_path = usage_jsonl_path
        self._wandb_run = wandb_run
        self._call_idx = 0
        self._last_tokens_in = 0
        self._last_tokens_out = 0
        self._cumulative_usd = 0.0

    def __call__(self, prompt: str | list[dict[str, Any]]) -> str:
        cost_before = self.total_cost
        response = super().__call__(prompt)
        delta_in = self.total_tokens_in - self._last_tokens_in
        delta_out = self.total_tokens_out - self._last_tokens_out
        self._last_tokens_in = self.total_tokens_in
        self._last_tokens_out = self.total_tokens_out
        call_usd = estimate_reflection_cost_usd(self.model, delta_in, delta_out)
        if self.model in REFLECTION_USD_PER_MILLION:
            with self._cost_lock:
                self._total_cost = cost_before + call_usd
        self._cumulative_usd += call_usd
        record = {
            "call_idx": self._call_idx,
            "model": self.model,
            "input_tokens": delta_in,
            "output_tokens": delta_out,
            "usd": call_usd,
            "cumulative_usd": self._cumulative_usd,
        }
        self._usage_jsonl_path.parent.mkdir(parents=True, exist_ok=True)
        with self._usage_jsonl_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record) + "\n")
        if self._wandb_run is not None:
            self._wandb_run.log(
                {
                    "reflection/call_usd": call_usd,
                    "reflection/cumulative_usd": self._cumulative_usd,
                    "reflection/input_tokens": delta_in,
                    "reflection/output_tokens": delta_out,
                }
            )
        self._call_idx += 1
        return response


def make_reflection_lm_with_usage_log(
    model: str,
    *,
    usage_jsonl_path: Path,
    wandb_run: Any | None,
) -> LM:
    """Build a GEPA LM with per-call reflection usage logging."""
    return UsageLoggingLM(
        model,
        usage_jsonl_path=usage_jsonl_path,
        wandb_run=wandb_run,
    )
