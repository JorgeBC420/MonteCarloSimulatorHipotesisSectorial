"""
figures/observed_overlay.py — Superposición observacional JADES/TNG/SIMBA
SMCHS v0.5.5
"""
from __future__ import annotations

import logging
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from config import PALETTE, Z_CUT, LOG_M_THRESH

logger = logging.getLogger(__name__)


def _sample_df(df: pd.DataFrame, n: int = 5000, seed: int = 123) -> pd.DataFrame:
    if len(df) <= n:
        return df
    return df.sample(n=n, random_state=seed)


def fig_observed_overlay(
    pop_base: dict,
    pop_sect: dict,
    observed_df: pd.DataFrame,
    out: str,
    filename: str = "fig12_observed_overlay.png",
) -> None:
    """
    Superpone catálogos observacionales/externos sobre nubes SMCHS.

    Panel A: z vs logM* si observed_df contiene log_m_star.
    Panel B: z vs MUV si observed_df contiene MUV.
    """
    out_path = Path(out) / filename
    base_df = pd.DataFrame({"z": pop_base["z"], "log_m_star": pop_base["log_m"], "MUV": pop_base["M_UV"], "visible": pop_base["visible"]})
    sect_df = pd.DataFrame({"z": pop_sect["z"], "log_m_star": pop_sect["log_m"], "MUV": pop_sect["M_UV"], "visible": pop_sect["visible"]})
    base_df = _sample_df(base_df[base_df["visible"] & (base_df["z"] > Z_CUT)], 5000)
    sect_df = _sample_df(sect_df[sect_df["visible"] & (sect_df["z"] > Z_CUT)], 5000)
    obs = observed_df[observed_df["z"] > Z_CUT].copy()

    fig, axes = plt.subplots(1, 2, figsize=(14, 5))
    fig.suptitle("Superposición observacional/externa sobre SMCHS", fontsize=13, fontweight="bold")

    ax = axes[0]
    ax.scatter(base_df["z"], base_df["log_m_star"], s=7, alpha=0.16, color=PALETTE["lcdm"], label="SMCHS ΛCDM proxy")
    ax.scatter(sect_df["z"], sect_df["log_m_star"], s=7, alpha=0.16, color=PALETTE["sect"], label="SMCHS sectorial")
    if "log_m_star" in obs.columns and obs["log_m_star"].notna().any():
        ax.scatter(obs["z"], obs["log_m_star"], s=42, marker="*", color="black", label="Datos externos")
    ax.axhline(LOG_M_THRESH, color="gray", ls="--", lw=1)
    ax.set_xlabel("redshift z")
    ax.set_ylabel("log₁₀(M★/M☉)")
    ax.set_title("Cola de masa estelar")
    ax.legend(fontsize=8, framealpha=0.4)

    ax = axes[1]
    ax.scatter(base_df["z"], base_df["MUV"], s=7, alpha=0.16, color=PALETTE["lcdm"], label="SMCHS ΛCDM proxy")
    ax.scatter(sect_df["z"], sect_df["MUV"], s=7, alpha=0.16, color=PALETTE["sect"], label="SMCHS sectorial")
    if "MUV" in obs.columns and obs["MUV"].notna().any():
        ax.scatter(obs["z"], obs["MUV"], s=42, marker="*", color="black", label="Datos externos")
    ax.invert_yaxis()
    ax.set_xlabel("redshift z")
    ax.set_ylabel("MUV (AB)")
    ax.set_title("Cola UV brillante")
    ax.legend(fontsize=8, framealpha=0.4)

    plt.tight_layout()
    fig.savefig(out_path, dpi=130, bbox_inches="tight")
    plt.close(fig)
    logger.info("Figura guardada: %s", out_path.name)
