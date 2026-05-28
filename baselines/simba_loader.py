"""SIMBA baseline loader for SMCHS/P4.

Hotfix library-aware version.

Supported workflows:

1. Local ready/preprocessed CSV/FITS/parquet:
       load_simba_baseline(path="data/raw/simba/catalog.csv")

2. Local CAESAR catalog through the optional `caesar` library:
       load_simba_from_caesar(caesar_path="m100n1024_151.hdf5")

No public one-line remote API is assumed here. If a remote SIMBA source is used,
first download/cache it externally or add a project-specific fetcher.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Iterable, Optional

import numpy as np
import pandas as pd


SOURCE_NAME = "SIMBA"


def _fallback_load_external_catalog(path: str | Path, source_name: str = SOURCE_NAME) -> pd.DataFrame:
    path = Path(path)
    suffix = path.suffix.lower()
    if suffix == ".csv":
        df = pd.read_csv(path)
    elif suffix in {".parquet", ".pq"}:
        df = pd.read_parquet(path)
    elif suffix in {".fits", ".fit"}:
        try:
            from astropy.table import Table
        except ImportError as exc:
            raise RuntimeError("Falta astropy para leer FITS: pip install astropy") from exc
        df = Table.read(path).to_pandas()
    else:
        raise ValueError(f"Formato no soportado para baseline externo: {path}")
    return normalize_simba_dataframe(df, source_name=source_name)


def _load_external_catalog(path: str | Path, source_name: str = SOURCE_NAME) -> pd.DataFrame:
    try:
        from .external_loader import load_external_catalog
        return load_external_catalog(path, source_name=source_name)
    except Exception:
        return _fallback_load_external_catalog(path, source_name=source_name)


def _first_existing(df: pd.DataFrame, names: Iterable[str]) -> Optional[str]:
    lower = {str(c).lower(): c for c in df.columns}
    for name in names:
        if name in df.columns:
            return name
        if name.lower() in lower:
            return lower[name.lower()]
    return None


def normalize_simba_dataframe(df: pd.DataFrame, source_name: str = SOURCE_NAME) -> pd.DataFrame:
    out = pd.DataFrame()

    name_col = _first_existing(df, ["name", "id", "ID", "galaxy_id", "GroupID"])
    z_col = _first_existing(df, ["z", "redshift", "snapshot_redshift"])
    logm_col = _first_existing(df, ["log_m_star", "logMstar", "log_Mstar", "log_mass", "stellar_logmass"])
    mstar_col = _first_existing(df, ["mstar", "stellar_mass", "Mstar", "mass_stars"])
    muv_col = _first_existing(df, ["MUV", "M_UV", "M1500", "M_1500", "muv"])

    out["name"] = df[name_col].astype(str) if name_col else [f"SIMBA_{i}" for i in range(len(df))]
    out["source"] = source_name
    out["z"] = pd.to_numeric(df[z_col], errors="coerce") if z_col else np.nan

    if logm_col:
        out["log_m_star"] = pd.to_numeric(df[logm_col], errors="coerce")
    elif mstar_col:
        m = pd.to_numeric(df[mstar_col], errors="coerce")
        out["log_m_star"] = np.log10(m.where(m > 0))
    else:
        out["log_m_star"] = np.nan

    out["MUV"] = pd.to_numeric(df[muv_col], errors="coerce") if muv_col else np.nan

    sfr_col = _first_existing(df, ["sfr", "SFR"])
    out["sfr"] = pd.to_numeric(df[sfr_col], errors="coerce") if sfr_col else np.nan

    snap_col = _first_existing(df, ["snapshot", "snap", "snapnum", "Snapshot"])
    out["snapshot"] = df[snap_col] if snap_col else np.nan
    out["volume_Mpc3"] = np.nan
    out["notes"] = ""

    return out[["name", "source", "z", "log_m_star", "MUV", "sfr", "snapshot", "volume_Mpc3", "notes"]]


def load_simba_baseline(path: str | Path | None = None, **kwargs: Any) -> pd.DataFrame:
    if path is not None:
        return _load_external_catalog(path, source_name=SOURCE_NAME)

    if kwargs.get("caesar_path") is not None:
        return load_simba_from_caesar(
            caesar_path=kwargs["caesar_path"],
            snapshot_redshift=kwargs.get("snapshot_redshift"),
            min_log_m_star=kwargs.get("min_log_m_star"),
        )

    raise ValueError(
        "load_simba_baseline requiere path='catalog.csv' o caesar_path='catalog.hdf5'. "
        "No se asume una API remota genérica para SIMBA."
    )


def _to_float_msun(value) -> float:
    """Best-effort conversion for unyt/astropy-like quantities."""
    try:
        if hasattr(value, "to"):
            return float(value.to("Msun").value)
        if hasattr(value, "in_units"):
            return float(value.in_units("Msun"))
        return float(value)
    except Exception:
        return np.nan


def load_simba_from_caesar(
    caesar_path: str | Path,
    *,
    snapshot_redshift: Optional[float] = None,
    min_log_m_star: Optional[float] = None,
) -> pd.DataFrame:
    """Load a SIMBA CAESAR catalog if the optional `caesar` package is installed."""
    try:
        import caesar
    except ImportError as exc:
        raise RuntimeError("Falta caesar. Instala la librería CAESAR para leer catálogos SIMBA.") from exc

    sim = caesar.load(str(caesar_path))
    redshift = snapshot_redshift
    if redshift is None:
        redshift = getattr(getattr(sim, "simulation", None), "redshift", np.nan)

    rows = []
    galaxies = getattr(sim, "galaxies", [])
    for i, gal in enumerate(galaxies):
        masses = getattr(gal, "masses", {}) or {}
        stellar = masses.get("stellar", np.nan)
        mstar = _to_float_msun(stellar)
        log_m_star = np.log10(mstar) if np.isfinite(mstar) and mstar > 0 else np.nan

        sfr = getattr(gal, "sfr", np.nan)
        try:
            sfr = float(sfr)
        except Exception:
            pass

        rows.append({
            "name": f"SIMBA_galaxy_{getattr(gal, 'GroupID', i)}",
            "source": SOURCE_NAME,
            "z": redshift,
            "log_m_star": log_m_star,
            "MUV": np.nan,
            "sfr": sfr,
            "snapshot": np.nan,
            "volume_Mpc3": np.nan,
            "notes": "Loaded from CAESAR SIMBA catalog; MUV unavailable.",
        })

    df = pd.DataFrame(rows)
    if min_log_m_star is not None and not df.empty:
        df = df[df["log_m_star"] >= float(min_log_m_star)].copy()
    return df.reset_index(drop=True)


def export_simba_ready_csv(df: pd.DataFrame, out_path: str | Path, *, z_min: Optional[float] = None, z_max: Optional[float] = None) -> Path:
    out = df.copy()
    if z_min is not None:
        out = out[out["z"] >= z_min]
    if z_max is not None:
        out = out[out["z"] <= z_max]
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(out_path, index=False)
    return out_path
