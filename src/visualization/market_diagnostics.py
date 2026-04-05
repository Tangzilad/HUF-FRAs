from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


def plot_fitted_vs_observed(
    tenors: np.ndarray,
    observed: np.ndarray,
    fitted: np.ndarray,
    output_path: str | Path,
    title: str = "Observed vs Fitted Curve",
) -> Path:
    fig, ax = plt.subplots(figsize=(8, 4.5))
    ax.scatter(tenors, observed, label="Observed", color="#1f77b4")
    ax.plot(tenors, fitted, label="Fitted", color="#ff7f0e", linewidth=2)
    ax.set_xlabel("Tenor (years)")
    ax.set_ylabel("Yield")
    ax.set_title(title)
    ax.legend()
    ax.grid(alpha=0.3)
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(output, dpi=160)
    plt.close(fig)
    return output


def plot_cip_deviation(cip_df: pd.DataFrame, output_path: str | Path) -> Path:
    fig, ax = plt.subplots(figsize=(9, 4.5))
    pivot = cip_df.pivot(index="timestamp", columns="tenor", values="cip_deviation_bp")
    pivot.plot(ax=ax, linewidth=1.2)
    ax.axhline(0.0, color="black", linestyle="--", linewidth=1)
    ax.set_title("CIP Deviations by Tenor")
    ax.set_ylabel("Deviation (bp)")
    ax.set_xlabel("Time")
    ax.grid(alpha=0.25)
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(output, dpi=160)
    plt.close(fig)
    return output


def plot_basis_term_premium_panel(panel_df: pd.DataFrame, output_path: str | Path) -> Path:
    fig, axes = plt.subplots(2, 1, figsize=(10, 7), sharex=True)

    axes[0].plot(panel_df["tenor_years"], panel_df["basis_bp"], marker="o")
    axes[0].set_title("Basis Spread Term Structure")
    axes[0].set_ylabel("Basis (bp)")
    axes[0].grid(alpha=0.25)

    axes[1].bar(panel_df["tenor_years"], panel_df["term_premium_bp"], width=0.25)
    axes[1].set_title("Term Premium Decomposition")
    axes[1].set_ylabel("Term Premium (bp)")
    axes[1].set_xlabel("Tenor (years)")
    axes[1].grid(alpha=0.25)

    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(output, dpi=160)
    plt.close(fig)
    return output
