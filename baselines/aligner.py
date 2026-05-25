"""
baselines/aligner.py — Alineación de cortes SMCHS/JADES/TNG/SIMBA
SMCHS v0.5.5
"""
from __future__ import annotations

import pandas as pd


def apply_common_cuts(
    df: pd.DataFrame,
    z_cut: float = 12.0,
    mass_cut: float | None = None,
    muv_cut: float | None = None,
    mass_col: str = "log_m_star",
    muv_col: str = "MUV",
) -> pd.DataFrame:
    """Aplica cortes comunes por redshift, masa y/o magnitud UV."""
    if "z" not in df.columns:
        raise ValueError("apply_common_cuts requiere columna 'z'")
    mask = df["z"] > z_cut
    if mass_cut is not None and mass_col in df.columns:
        mask &= df[mass_col] > mass_cut
    if muv_cut is not None and muv_col in df.columns:
        mask &= df[muv_col] < muv_cut
    return df[mask].copy().reset_index(drop=True)
