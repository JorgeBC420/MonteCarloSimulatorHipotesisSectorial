"""IllustrisTNG baseline loader for SMCHS/P4.

Hotfix library-aware version.

This module supports three workflows:

1. Local ready/preprocessed CSV/FITS/parquet:
       load_tng_baseline(path="data/raw/tng/some_catalog.csv")

2. Local IllustrisTNG group catalog through the optional `illustris_python`
   library:
       load_tng_from_groupcat(base_path="...", snapshot=4, snapshot_redshift=12.0)

3. IllustrisTNG public API, if the user provides an API key:
       fetch_tng_api_baseline(api_key="...", simulation="TNG100-1", snapshot=4)

Important:
- The group catalog/API path can usually provide stellar mass proxies.
- It does NOT guarantee a physically comparable MUV column.
- P4_MUV should not be claimed until the baseline has a comparable synthetic UV
  magnitude or mock photometric product.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Iterable, Optional

import math
import time

import numpy as np
import pandas as pd


SOURCE_NAME = "IllustrisTNG"


def _fallback_load_external_catalog(path: str | Path, source_name: str = SOURCE_NAME) -> pd.DataFrame:
    """Minimal fallback if baselines.external_loader is unavailable."""
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

    return normalize_tng_dataframe(df, source_name=source_name)


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


def normalize_tng_dataframe(df: pd.DataFrame, source_name: str = SOURCE_NAME) -> pd.DataFrame:
    """Normalize common TNG-like columns into SMCHS/P4 canonical schema."""
    out = pd.DataFrame()

    name_col = _first_existing(df, ["name", "id", "ID", "subhalo_id", "SubhaloID", "SubfindID"])
    z_col = _first_existing(df, ["z", "redshift", "snapshot_redshift"])
    logm_col = _first_existing(df, ["log_m_star", "logMstar", "log_Mstar", "log_mass", "stellar_logmass"])
    mstar_col = _first_existing(df, ["mstar", "stellar_mass", "SubhaloMassStars", "mass_stars", "Mstar"])
    muv_col = _first_existing(df, ["MUV", "M_UV", "M1500", "M_1500", "muv"])

    if name_col:
        out["name"] = df[name_col].astype(str)
    else:
        out["name"] = [f"TNG_{i}" for i in range(len(df))]

    out["source"] = source_name

    if z_col:
        out["z"] = pd.to_numeric(df[z_col], errors="coerce")
    else:
        out["z"] = np.nan

    if logm_col:
        out["log_m_star"] = pd.to_numeric(df[logm_col], errors="coerce")
    elif mstar_col:
        m = pd.to_numeric(df[mstar_col], errors="coerce")
        out["log_m_star"] = np.log10(m.where(m > 0))
    else:
        out["log_m_star"] = np.nan

    if muv_col:
        out["MUV"] = pd.to_numeric(df[muv_col], errors="coerce")
    else:
        out["MUV"] = np.nan

    sfr_col = _first_existing(df, ["sfr", "SFR", "SubhaloSFR"])
    out["sfr"] = pd.to_numeric(df[sfr_col], errors="coerce") if sfr_col else np.nan

    snap_col = _first_existing(df, ["snapshot", "snap", "snapnum", "Snapshot"])
    out["snapshot"] = df[snap_col] if snap_col else np.nan

    out["volume_Mpc3"] = np.nan
    out["notes"] = ""

    return out[["name", "source", "z", "log_m_star", "MUV", "sfr", "snapshot", "volume_Mpc3", "notes"]]


def load_tng_baseline(path: str | Path | None = None, **kwargs: Any) -> pd.DataFrame:
    """Load a TNG baseline.

    If `path` is provided, loads a local preprocessed catalog.
    If `base_path` and `snapshot` are provided, uses illustris_python.
    If `api_key` is provided, queries the public API.

    This keeps backward compatibility with the old wrapper while allowing
    library/API based loading.
    """
    if path is not None:
        return _load_external_catalog(path, source_name=SOURCE_NAME)

    if kwargs.get("base_path") is not None and kwargs.get("snapshot") is not None:
        return load_tng_from_groupcat(
            base_path=kwargs["base_path"],
            snapshot=int(kwargs["snapshot"]),
            snapshot_redshift=kwargs.get("snapshot_redshift"),
            h=float(kwargs.get("h", 0.6774)),
            min_log_m_star=kwargs.get("min_log_m_star"),
        )

    if kwargs.get("api_key") is not None:
        return fetch_tng_api_baseline(
            api_key=kwargs["api_key"],
            simulation=kwargs.get("simulation", "TNG100-1"),
            snapshot=int(kwargs["snapshot"]) if kwargs.get("snapshot") is not None else None,
            max_objects=int(kwargs.get("max_objects", 1000)),
            min_log_m_star=kwargs.get("min_log_m_star"),
            sleep_s=float(kwargs.get("sleep_s", 0.05)),
        )

    raise ValueError(
        "load_tng_baseline requiere una de estas opciones: "
        "(1) path='catalog.csv', "
        "(2) base_path='...'/snapshot=N para illustris_python, "
        "(3) api_key='...' y snapshot=N para API."
    )


def load_tng_from_groupcat(
    base_path: str | Path,
    snapshot: int,
    *,
    snapshot_redshift: Optional[float] = None,
    h: float = 0.6774,
    min_log_m_star: Optional[float] = None,
) -> pd.DataFrame:
    """Load TNG subhalos using the optional illustris_python library.

    Requires:
        pip install illustris_python
    and local TNG groupcat files at base_path.

    Stellar mass conversion:
        SubhaloMassType[:,4] is commonly in 1e10 Msun/h.
        log_m_star = log10(SubhaloMassType[:,4] * 1e10 / h)

    MUV is not produced here.
    """
    try:
        import illustris_python as il
    except ImportError as exc:
        raise RuntimeError(
            "Falta illustris_python. Instala/añade la librería oficial de IllustrisTNG "
            "o usa --mode api con API key."
        ) from exc

    fields = ["SubhaloMassType", "SubhaloSFR"]
    subhalos = il.groupcat.loadSubhalos(str(base_path), snapshot, fields=fields)

    mass_type = np.asarray(subhalos["SubhaloMassType"])
    sfr = np.asarray(subhalos["SubhaloSFR"])

    stellar_mass = mass_type[:, 4] * 1.0e10 / h
    log_m_star = np.full(stellar_mass.shape, np.nan, dtype=float)
    mask = stellar_mass > 0
    log_m_star[mask] = np.log10(stellar_mass[mask])

    df = pd.DataFrame({
        "name": [f"TNG_snap{snapshot}_subhalo{i}" for i in range(len(log_m_star))],
        "source": SOURCE_NAME,
        "z": snapshot_redshift if snapshot_redshift is not None else np.nan,
        "log_m_star": log_m_star,
        "MUV": np.nan,
        "sfr": sfr,
        "snapshot": snapshot,
        "volume_Mpc3": np.nan,
        "notes": "Loaded from local IllustrisTNG group catalog; MUV unavailable.",
    })

    if min_log_m_star is not None:
        df = df[df["log_m_star"] >= float(min_log_m_star)].copy()

    return df.reset_index(drop=True)


def _api_get_json(url: str, api_key: str, params: Optional[Dict[str, Any]] = None) -> Any:
    try:
        import requests
    except ImportError as exc:
        raise RuntimeError("Falta requests: pip install requests") from exc

    headers = {"api-key": api_key}
    response = requests.get(url, headers=headers, params=params, timeout=60)
    if response.status_code == 401:
        raise RuntimeError("API key inválida o no autorizada para IllustrisTNG.")
    response.raise_for_status()
    return response.json()


def fetch_tng_api_baseline(
    *,
    api_key: str,
    simulation: str = "TNG100-1",
    snapshot: Optional[int] = None,
    max_objects: int = 1000,
    min_log_m_star: Optional[float] = None,
    sleep_s: float = 0.05,
) -> pd.DataFrame:
    """Fetch a minimal baseline from the IllustrisTNG public API.

    This is intentionally conservative because API schemas can vary.
    It attempts to read subhalo summaries and normalize common keys.

    MUV is not guaranteed and is exported as NaN unless present in the API result.
    """
    if snapshot is None:
        raise ValueError("snapshot es requerido para la API TNG.")

    base = f"https://www.tng-project.org/api/{simulation}/snapshots/{snapshot}"
    snap_info = _api_get_json(base, api_key)
    redshift = snap_info.get("redshift", np.nan)

    subhalos_url = base.rstrip("/") + "/subhalos/"
    rows = []
    limit = min(100, max_objects)
    offset = 0

    while len(rows) < max_objects:
        params = {"limit": limit, "offset": offset}
        page = _api_get_json(subhalos_url, api_key, params=params)

        results = page.get("results", page if isinstance(page, list) else [])
        if not results:
            break

        for item in results:
            row = {
                "name": f"TNG_snap{snapshot}_subhalo{item.get('id', len(rows))}",
                "source": SOURCE_NAME,
                "z": redshift,
                "snapshot": snapshot,
                "MUV": item.get("MUV", item.get("M_UV", item.get("M1500", np.nan))),
                "sfr": item.get("sfr", item.get("SubhaloSFR", np.nan)),
                "volume_Mpc3": np.nan,
                "notes": "Fetched from IllustrisTNG API; MUV may be unavailable.",
            }

            logm = item.get("log_m_star", item.get("logMstar", None))
            if logm is not None:
                row["log_m_star"] = logm
            else:
                mstar = item.get("mass_stars", item.get("stellar_mass", item.get("SubhaloMassStars", None)))
                try:
                    row["log_m_star"] = math.log10(float(mstar)) if mstar and float(mstar) > 0 else np.nan
                except Exception:
                    row["log_m_star"] = np.nan

            rows.append(row)
            if len(rows) >= max_objects:
                break

        next_url = page.get("next") if isinstance(page, dict) else None
        if next_url:
            subhalos_url = next_url
            offset = 0
        else:
            offset += limit

        time.sleep(sleep_s)

    df = pd.DataFrame(rows)
    if df.empty:
        return pd.DataFrame(columns=["name", "source", "z", "log_m_star", "MUV", "sfr", "snapshot", "volume_Mpc3", "notes"])

    if min_log_m_star is not None and "log_m_star" in df.columns:
        df = df[pd.to_numeric(df["log_m_star"], errors="coerce") >= float(min_log_m_star)].copy()

    return normalize_tng_dataframe(df, source_name=SOURCE_NAME)


def export_tng_ready_csv(df: pd.DataFrame, out_path: str | Path, *, z_min: Optional[float] = None, z_max: Optional[float] = None) -> Path:
    out = df.copy()
    if z_min is not None:
        out = out[out["z"] >= z_min]
    if z_max is not None:
        out = out[out["z"] <= z_max]

    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(out_path, index=False)
    return out_path
