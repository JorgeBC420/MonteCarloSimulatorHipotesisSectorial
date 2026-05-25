"""
baselines/external_loader.py — Carga de baselines externos CSV/FITS
SMCHS v0.5.5

Carga catálogos tabulares de JADES, IllustrisTNG, SIMBA u otros baselines ya
preprocesados. No corre simulaciones hidrodinámicas ni descarga datos: solo
normaliza columnas para comparar colas con SMCHS.

Columnas canónicas esperadas:
    name, source, z, log_m_star, MUV, metallicity_proxy, sfr, volume_Mpc3, confirmed

Se aceptan aliases comunes para facilitar catálogos heterogéneos.
"""
from __future__ import annotations

from pathlib import Path
from typing import Mapping
import numpy as np
import pandas as pd

try:  # astropy es opcional: solo se necesita para FITS
    from astropy.table import Table
except Exception:  # pragma: no cover
    Table = None

_COLUMN_ALIASES: dict[str, list[str]] = {
    "name": ["name", "source", "Source_Name", "Source Name", "object", "ID", "id"],
    "z": ["z", "z_best", "redshift", "z_spec", "z_phot", "EAZY_z_a", "EAZY z_a"],
    "log_m_star": ["log_m_star", "logMstar", "log_m", "stellar_mass_log", "log10Mstar", "SubhaloMassStars"],
    "MUV": ["MUV", "M_UV", "muv", "Muv"],
    "metallicity_proxy": ["metallicity_proxy", "Z_met", "Z", "stellar_metallicity", "SubhaloStarMetallicity"],
    "sfr": ["sfr", "SFR", "SubhaloSFR"],
    "volume_Mpc3": ["volume_Mpc3", "volume", "box_volume"],
    "confirmed": ["confirmed", "is_spec", "spectroscopic", "flag_confirmed"],
    "source": ["simulation", "survey", "source_catalog", "dataset"],
}


def _read_table(path: str | Path) -> pd.DataFrame:
    path = Path(path)
    suffix = path.suffix.lower()
    if suffix in {".csv", ".txt"}:
        return pd.read_csv(path)
    if suffix in {".parquet"}:
        return pd.read_parquet(path)
    if suffix in {".fits", ".fit", ".fz"}:
        if Table is None:
            raise ImportError("astropy es requerido para leer FITS")
        df = Table.read(path).to_pandas()
        # FITS puede traer strings como bytes
        for col in df.select_dtypes(include=[object]).columns:
            df[col] = df[col].map(lambda x: x.decode("utf-8") if isinstance(x, bytes) else x)
        return df
    raise ValueError(f"Formato no soportado: {path.suffix}")


def _first_existing(df: pd.DataFrame, aliases: list[str]) -> str | None:
    # match exacto primero
    for a in aliases:
        if a in df.columns:
            return a
    # match normalizado básico
    norm = {str(c).lower().replace(" ", "_"): c for c in df.columns}
    for a in aliases:
        key = a.lower().replace(" ", "_")
        if key in norm:
            return norm[key]
    return None


def normalize_external_catalog(
    df: pd.DataFrame,
    source_name: str = "external",
    extra_aliases: Mapping[str, list[str]] | None = None,
) -> pd.DataFrame:
    """Normaliza un DataFrame externo a columnas canónicas comparables con SMCHS."""
    aliases = {k: list(v) for k, v in _COLUMN_ALIASES.items()}
    if extra_aliases:
        for key, vals in extra_aliases.items():
            aliases.setdefault(key, [])
            aliases[key] = list(vals) + aliases[key]

    out = pd.DataFrame(index=df.index)
    for canonical, cand in aliases.items():
        found = _first_existing(df, cand)
        if found is not None:
            out[canonical] = df[found]

    if "z" not in out.columns:
        raise ValueError("El catálogo externo no tiene una columna de redshift reconocible")

    out["z"] = pd.to_numeric(out["z"], errors="coerce")
    for col in ["log_m_star", "MUV", "metallicity_proxy", "sfr", "volume_Mpc3"]:
        if col in out.columns:
            out[col] = pd.to_numeric(out[col], errors="coerce")

    if "source" not in out.columns:
        out["source"] = source_name
    else:
        out["source"] = out["source"].fillna(source_name)

    if "name" not in out.columns:
        out["name"] = [f"{source_name}_{i}" for i in range(len(out))]

    # Eliminar filas sin redshift válido
    out = out[np.isfinite(out["z"])].copy()
    return out.reset_index(drop=True)


def load_external_catalog(
    path: str | Path,
    source_name: str | None = None,
    extra_aliases: Mapping[str, list[str]] | None = None,
) -> pd.DataFrame:
    """Carga y normaliza CSV/FITS/parquet externo."""
    path = Path(path)
    df = _read_table(path)
    return normalize_external_catalog(df, source_name or path.stem, extra_aliases=extra_aliases)


def save_normalized_catalog(df: pd.DataFrame, output_path: str | Path) -> Path:
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_path, index=False)
    return output_path
