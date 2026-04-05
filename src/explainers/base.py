from __future__ import annotations

from abc import ABC, abstractmethod


class BaseExplainer(ABC):
    """Common interface for markdown-based explainers."""

    @property
    @abstractmethod
    def title(self) -> str:
        """Human-readable section title for the explainer."""

    @abstractmethod
    def explain_concepts(self) -> str:
        """Explain the core concepts and intuition."""

    @abstractmethod
    def explain_inputs(self) -> str:
        """Describe required and optional inputs."""

    @abstractmethod
    def explain_calibration(self) -> str:
        """Describe how model parameters are calibrated/estimated."""

    @abstractmethod
    def explain_outputs(self) -> str:
        """Describe key outputs and interpretation."""

    @abstractmethod
    def explain_trading_implications(self) -> str:
        """Explain trading and risk-management implications."""

    def render_full_markdown(self) -> str:
        """Render a complete markdown explainer payload."""
        sections = [
            f"# {self.title}",
            "## Concepts\n" + self.explain_concepts().strip(),
            "## Inputs\n" + self.explain_inputs().strip(),
            "## Calibration\n" + self.explain_calibration().strip(),
            "## Outputs\n" + self.explain_outputs().strip(),
            "## Trading implications\n" + self.explain_trading_implications().strip(),
        ]
        return "\n\n".join(sections).strip() + "\n"

    def explain(self) -> str:
        """Backward-compatible alias used by tests and scripts."""
        return self.render_full_markdown()
