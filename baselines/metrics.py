"""
baselines/metrics.py — Métricas externas de cola
SMCHS v0.5.5

Métricas diseñadas para comparar SMCHS contra JADES/TNG/SIMBA sin asumir que
los catálogos externos tengan la misma física interna del toy model.
"""
from __future__ import annotations

import numpy as np
import pandas as pd


def tail_summary(
    df: pd.DataFrame,
    z_cut: float = 12.0,
    mass_cut: float = 10.5,
    mass_col: str = "log_m_star",
    muv_col: str = "MUV",
    muv_cut: float = -20.0,
) -> dict[str, float]:
    """Resumen de cola para catálogos externos u observacionales."""
    if "z" not in df.columns:
        raise ValueError("tail_summary requiere columna 'z'")
    sub = df[df["z"] > z_cut].copy()

    out: dict[str, float] = {"n_z": float(len(sub)), "z_cut": float(z_cut)}
    if mass_col in sub.columns:
        m = pd.to_numeric(sub[mass_col], errors="coerce").dropna().to_numpy(dtype=float)
        out.update({
            "n_mass_valid": float(len(m)),
            "p_massive": float(np.mean(m > mass_cut)) if len(m) else np.nan,
            "q95_log_m": float(np.percentile(m, 95)) if len(m) else np.nan,
            "q99_log_m": float(np.percentile(m, 99)) if len(m) else np.nan,
        })
    else:
        out.update({"n_mass_valid": 0.0, "p_massive": np.nan, "q95_log_m": np.nan, "q99_log_m": np.nan})

    if muv_col in sub.columns:
        muv = pd.to_numeric(sub[muv_col], errors="coerce").dropna().to_numpy(dtype=float)
        out.update({
            "n_muv_valid": float(len(muv)),
            "p_uv_bright": float(np.mean(muv < muv_cut)) if len(muv) else np.nan,
            "q01_muv": float(np.percentile(muv, 1)) if len(muv) else np.nan,   # extremo brillante
            "q05_muv": float(np.percentile(muv, 5)) if len(muv) else np.nan,
        })
    else:
        out.update({"n_muv_valid": 0.0, "p_uv_bright": np.nan, "q01_muv": np.nan, "q05_muv": np.nan})

    return out


def population_to_dataframe(pop: dict, model_name: str) -> pd.DataFrame:
    """Convierte una población SMCHS a DataFrame canónico para comparación externa."""
    return pd.DataFrame({
        "source": model_name,
        "z": pop["z"],
        "log_m_star": pop["log_m"],
        "MUV": pop["M_UV"],
        "metallicity_proxy": pop["Z_met"],
        "visible": pop["visible"].astype(bool),
        "dt_signal": pop.get("dt_signal", np.zeros_like(pop["z"])),
        "dt_observed": pop.get("dt_observed", np.zeros_like(pop["z"])),
    })


def visible_smchs_df(pop: dict, model_name: str) -> pd.DataFrame:
    df = population_to_dataframe(pop, model_name)
    return df[df["visible"]].copy().reset_index(drop=True)


def compare_tail_to_baseline(
    model_df: pd.DataFrame,
    baseline_df: pd.DataFrame,
    z_cut: float = 12.0,
    mass_cut: float = 10.5,
) -> dict[str, float]:
    """
    Compara la cola de un modelo/catálogo contra un baseline externo o interno.

    D_tail_log_m = Q99_model(logM*) - Q99_baseline(logM*)
    delta_P_massive = P_model(M>Mcut) - P_baseline(M>Mcut)
    """
    m = tail_summary(model_df, z_cut=z_cut, mass_cut=mass_cut)
    b = tail_summary(baseline_df, z_cut=z_cut, mass_cut=mass_cut)
    return {
        "z_cut": float(z_cut),
        "mass_cut": float(mass_cut),
        "model_n_z": m["n_z"],
        "baseline_n_z": b["n_z"],
        "model_p_massive": m["p_massive"],
        "baseline_p_massive": b["p_massive"],
        "delta_P_massive": m["p_massive"] - b["p_massive"] if np.isfinite(m["p_massive"]) and np.isfinite(b["p_massive"]) else np.nan,
        "model_q99_log_m": m["q99_log_m"],
        "baseline_q99_log_m": b["q99_log_m"],
        "D_tail_log_m": m["q99_log_m"] - b["q99_log_m"] if np.isfinite(m["q99_log_m"]) and np.isfinite(b["q99_log_m"]) else np.nan,
    }


def percentile_rank(values: np.ndarray, x: float) -> float:
    """Percentil empírico de x respecto a values."""
    values = np.asarray(values, dtype=float)
    values = values[np.isfinite(values)]
    if len(values) == 0 or not np.isfinite(x):
        return np.nan
    return float(np.mean(values <= x))


def observed_percentiles(
    observed_df: pd.DataFrame,
    model_df: pd.DataFrame,
    z_cut: float = 12.0,
    value_col: str = "log_m_star",
) -> pd.DataFrame:
    """Calcula percentil de cada objeto observado bajo una distribución modelo."""
    if value_col not in observed_df.columns or value_col not in model_df.columns:
        raise ValueError(f"Columna requerida no disponible: {value_col}")
    model_values = model_df.loc[model_df["z"] > z_cut, value_col].to_numpy(dtype=float)
    rows = []
    for _, row in observed_df[observed_df["z"] > z_cut].iterrows():
        rows.append({
            "name": row.get("name", "observed"),
            "source": row.get("source", "observed"),
            "z": float(row["z"]),
            value_col: float(row[value_col]) if pd.notna(row[value_col]) else np.nan,
            f"percentile_{value_col}": percentile_rank(model_values, row[value_col]),
        })
    return pd.DataFrame(rows)
