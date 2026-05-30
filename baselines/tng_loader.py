"""IllustrisTNG baseline loader for SMCHS/P4.

Hotfix chain:
- API detail mode extracts stellar mass from /subhalos/{id}/.
- log_m_star guard patch: only trusts an existing log-mass column if it has
  valid values; otherwise falls back to mass_stars conversion.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Iterable, Optional
from urllib.parse import urljoin
import time
import numpy as np
import pandas as pd

SOURCE_NAME = "IllustrisTNG"
DEFAULT_H = 0.6774


def _first_existing(df: pd.DataFrame, names: Iterable[str]) -> Optional[str]:
    lower = {str(c).lower(): c for c in df.columns}
    for name in names:
        if name in df.columns:
            return name
        if name.lower() in lower:
            return lower[name.lower()]
    return None


def _component_to_msun(value: Any, h: float = DEFAULT_H) -> float:
    try:
        x = float(value)
    except Exception:
        return np.nan
    if not np.isfinite(x) or x < 0:
        return np.nan
    return float(x * 1.0e10 / h)


def _component_to_log_msun(value: Any, h: float = DEFAULT_H) -> float:
    m = _component_to_msun(value, h=h)
    if not np.isfinite(m) or m <= 0:
        return np.nan
    return float(np.log10(m))


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
    return normalize_tng_dataframe(df, source_name=source_name)


def _load_external_catalog(path: str | Path, source_name: str = SOURCE_NAME) -> pd.DataFrame:
    try:
        from .external_loader import load_external_catalog
        return load_external_catalog(path, source_name=source_name)
    except Exception:
        return _fallback_load_external_catalog(path, source_name=source_name)


def normalize_tng_dataframe(df: pd.DataFrame, source_name: str = SOURCE_NAME, h: float = DEFAULT_H) -> pd.DataFrame:
    out = pd.DataFrame()

    id_col = _first_existing(df, ["id", "ID", "subhalo_id", "SubhaloID", "SubfindID"])
    name_col = _first_existing(df, ["name"])
    z_col = _first_existing(df, ["z", "redshift", "snapshot_redshift"])

    # Do not include mass_log_msun here: in the TNG API it is total subhalo mass,
    # not stellar mass.
    logm_col = _first_existing(df, ["log_m_star", "logMstar", "log_Mstar", "stellar_logmass"])
    mstar_col = _first_existing(df, ["mass_stars", "SubhaloMassStars", "mstar", "stellar_mass", "Mstar"])
    muv_col = _first_existing(df, ["MUV", "M_UV", "M1500", "M_1500", "muv"])

    if name_col:
        out["name"] = df[name_col].astype(str)
    elif id_col:
        out["name"] = df[id_col].astype(str).map(lambda x: f"TNG_subhalo{x}")
    else:
        out["name"] = [f"TNG_{i}" for i in range(len(df))]

    out["source"] = source_name
    out["z"] = pd.to_numeric(df[z_col], errors="coerce") if z_col else np.nan

    # Guard patch: use log column only if it has valid values; otherwise fall
    # back to mass_stars.
    if logm_col is not None:
        logm = pd.to_numeric(df[logm_col], errors="coerce")
        if int(logm.notna().sum()) > 0:
            out["log_m_star"] = logm
        elif mstar_col is not None:
            m_raw = pd.to_numeric(df[mstar_col], errors="coerce")
            out["log_m_star"] = m_raw.map(lambda x: _component_to_log_msun(x, h=h) if pd.notna(x) else np.nan)
        else:
            out["log_m_star"] = np.nan
    elif mstar_col is not None:
        m_raw = pd.to_numeric(df[mstar_col], errors="coerce")
        finite = m_raw[np.isfinite(m_raw)]
        if len(finite) and finite.median() < 1e6:
            out["log_m_star"] = m_raw.map(lambda x: _component_to_log_msun(x, h=h) if pd.notna(x) else np.nan)
        else:
            out["log_m_star"] = np.log10(m_raw.where(m_raw > 0))
    else:
        out["log_m_star"] = np.nan

    out["MUV"] = pd.to_numeric(df[muv_col], errors="coerce") if muv_col else np.nan

    sfr_col = _first_existing(df, ["sfr", "SFR", "SubhaloSFR"])
    snap_col = _first_existing(df, ["snapshot", "snap", "snapnum", "Snapshot"])
    out["sfr"] = pd.to_numeric(df[sfr_col], errors="coerce") if sfr_col else np.nan
    out["snapshot"] = df[snap_col] if snap_col else np.nan

    for raw, canon in [
        ("mass", "mass_total_msun"),
        ("mass_dm", "mass_dm_msun"),
        ("mass_gas", "mass_gas_msun"),
        ("mass_stars", "mass_stars_msun"),
        ("mass_bhs", "mass_bhs_msun"),
    ]:
        out[canon] = pd.to_numeric(df[raw], errors="coerce").map(lambda x: _component_to_msun(x, h=h)) if raw in df.columns else np.nan

    for col in ["len_stars", "len_dm", "len_gas"]:
        out[col] = pd.to_numeric(df[col], errors="coerce") if col in df.columns else np.nan

    out["volume_Mpc3"] = np.nan
    out["notes"] = df["notes"].astype(str) if "notes" in df.columns else ""

    return out[[
        "name", "source", "z", "log_m_star", "MUV", "sfr", "snapshot",
        "mass_total_msun", "mass_dm_msun", "mass_gas_msun", "mass_stars_msun", "mass_bhs_msun",
        "len_stars", "len_dm", "len_gas", "volume_Mpc3", "notes"
    ]]


def load_tng_baseline(path: str | Path | None = None, **kwargs: Any) -> pd.DataFrame:
    if path is not None:
        return _load_external_catalog(path, source_name=SOURCE_NAME)

    if kwargs.get("api_key") is not None:
        return fetch_tng_api_baseline(
            api_key=kwargs["api_key"],
            simulation=kwargs.get("simulation", "TNG300-1"),
            snapshot=int(kwargs["snapshot"]) if kwargs.get("snapshot") is not None else None,
            max_objects=int(kwargs.get("max_objects", 1000)),
            min_log_m_star=kwargs.get("min_log_m_star"),
            min_len_stars=kwargs.get("min_len_stars"),
            h=float(kwargs.get("h", DEFAULT_H)),
            sleep_s=float(kwargs.get("sleep_s", 0.02)),
            detail=bool(kwargs.get("detail", True)),
        )

    if kwargs.get("base_path") is not None and kwargs.get("snapshot") is not None:
        return load_tng_from_groupcat(
            base_path=kwargs["base_path"],
            snapshot=int(kwargs["snapshot"]),
            snapshot_redshift=kwargs.get("snapshot_redshift"),
            h=float(kwargs.get("h", DEFAULT_H)),
            min_log_m_star=kwargs.get("min_log_m_star"),
            min_len_stars=kwargs.get("min_len_stars"),
        )

    raise ValueError("load_tng_baseline requiere path, api_key+snapshot, o base_path+snapshot.")


def load_tng_from_groupcat(base_path: str | Path, snapshot: int, *, snapshot_redshift=None, h: float = DEFAULT_H,
                           min_log_m_star=None, min_len_stars=None) -> pd.DataFrame:
    try:
        import illustris_python as il
    except ImportError as exc:
        raise RuntimeError("Falta illustris_python; usa API o instala la librería oficial.") from exc

    fields = ["SubhaloMassType", "SubhaloSFR", "SubhaloLenType"]
    subhalos = il.groupcat.loadSubhalos(str(base_path), snapshot, fields=fields)
    mass_type = np.asarray(subhalos["SubhaloMassType"])
    sfr = np.asarray(subhalos["SubhaloSFR"])
    len_type = np.asarray(subhalos["SubhaloLenType"])

    stellar_mass = mass_type[:, 4] * 1.0e10 / h
    log_m_star = np.where(stellar_mass > 0, np.log10(stellar_mass), np.nan)
    df = pd.DataFrame({
        "name": [f"TNG_snap{snapshot}_subhalo{i}" for i in range(len(log_m_star))],
        "source": SOURCE_NAME,
        "z": snapshot_redshift if snapshot_redshift is not None else np.nan,
        "log_m_star": log_m_star,
        "MUV": np.nan,
        "sfr": sfr,
        "snapshot": snapshot,
        "mass_stars_msun": stellar_mass,
        "len_stars": len_type[:, 4],
        "volume_Mpc3": np.nan,
        "notes": "Loaded from local IllustrisTNG group catalog; MUV unavailable.",
    })
    if min_log_m_star is not None:
        df = df[df["log_m_star"] >= float(min_log_m_star)].copy()
    if min_len_stars is not None:
        df = df[pd.to_numeric(df["len_stars"], errors="coerce") >= int(min_len_stars)].copy()
    return df.reset_index(drop=True)


def _api_get_json(url: str, api_key: str, params: Optional[Dict[str, Any]] = None) -> Any:
    import requests
    headers = {"api-key": api_key}
    r = requests.get(url, headers=headers, params=params, timeout=90)
    if r.status_code == 401:
        raise RuntimeError("API key inválida o no autorizada para IllustrisTNG.")
    r.raise_for_status()
    return r.json()


def fetch_tng_api_baseline(*, api_key: str, simulation: str = "TNG300-1", snapshot: Optional[int] = None,
                           max_objects: int = 1000, min_log_m_star=None, min_len_stars=None,
                           h: float = DEFAULT_H, sleep_s: float = 0.02, detail: bool = True) -> pd.DataFrame:
    if snapshot is None:
        raise ValueError("snapshot es requerido para la API TNG.")

    base = f"https://www.tng-project.org/api/{simulation}/snapshots/{snapshot}/"
    snap_info = _api_get_json(base, api_key)
    redshift = snap_info.get("redshift", np.nan)
    list_url = urljoin(base, "subhalos/")

    rows = []
    limit = min(100, max_objects)
    offset = 0

    while len(rows) < max_objects:
        page = _api_get_json(list_url, api_key, params={"limit": limit, "offset": offset})
        results = page if isinstance(page, list) else page.get("results", [])
        next_url = None if isinstance(page, list) else page.get("next")
        if not results:
            break

        for item in results:
            if len(rows) >= max_objects:
                break
            sid = item.get("id", item.get("ID", item.get("subhalo_id")))
            try:
                sid = int(sid)
            except Exception:
                sid = len(rows)

            d = dict(item)
            if detail:
                try:
                    d = _api_get_json(urljoin(list_url, f"{sid}/"), api_key)
                    time.sleep(sleep_s)
                except Exception as exc:
                    d = dict(item)
                    d["notes"] = f"detail fetch failed: {exc}"

            rows.append({
                "id": sid,
                "name": f"TNG_snap{snapshot}_subhalo{sid}",
                "z": redshift,
                "snapshot": snapshot,
                "sfr": d.get("sfr", np.nan),
                "MUV": d.get("MUV", d.get("M_UV", d.get("M1500", np.nan))),
                "mass": d.get("mass", np.nan),
                "mass_dm": d.get("mass_dm", np.nan),
                "mass_gas": d.get("mass_gas", np.nan),
                "mass_stars": d.get("mass_stars", np.nan),
                "mass_bhs": d.get("mass_bhs", np.nan),
                "len_stars": d.get("len_stars", np.nan),
                "len_dm": d.get("len_dm", np.nan),
                "len_gas": d.get("len_gas", np.nan),
                "notes": d.get("notes", ""),
            })

        if next_url and len(rows) < max_objects:
            list_url = next_url
            offset = 0
        else:
            offset += limit

    df = normalize_tng_dataframe(pd.DataFrame(rows), source_name=SOURCE_NAME, h=h) if rows else pd.DataFrame()
    if len(df) == 0:
        return df

    if min_log_m_star is not None:
        df = df[pd.to_numeric(df["log_m_star"], errors="coerce") >= float(min_log_m_star)].copy()
    if min_len_stars is not None:
        df = df[pd.to_numeric(df["len_stars"], errors="coerce") >= int(min_len_stars)].copy()
    return df.reset_index(drop=True)


def export_tng_ready_csv(df: pd.DataFrame, out_path: str | Path, *, z_min=None, z_max=None) -> Path:
    out = df.copy()
    if z_min is not None and "z" in out.columns:
        out = out[out["z"] >= z_min]
    if z_max is not None and "z" in out.columns:
        out = out[out["z"] <= z_max]
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(out_path, index=False)
    return out_path
