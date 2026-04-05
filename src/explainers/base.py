"""Common interface for explanation components."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class BaseExplainer:
    """Base class for typed explainers."""

    name: str

    def explain(self, payload: dict) -> str:
        """Return a human-readable explanation from a payload."""
        return f"[{self.name}] explanation unavailable for payload keys={list(payload.keys())}"
