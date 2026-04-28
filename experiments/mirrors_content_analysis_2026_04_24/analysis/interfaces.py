"""Protocols/interfaces shared by analysis modules."""

from __future__ import annotations

from abc import ABC, abstractmethod


class CalculateMetric(ABC):
    """Single-text scalar metric: stable ``name``, prose ``describe()``, and ``calculate()``."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Identifier used in column names (e.g. ``char_count``)."""

    @abstractmethod
    def describe(self) -> str:
        """What the metric measures and exactly how it is computed from the input string."""

    @abstractmethod
    def calculate(self, text: str) -> float:
        """Return the metric value for one normalized post string."""
