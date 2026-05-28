#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
scripts/prepare_external_observations.py

Hotfix 2 — Conector de catálogos JWST para SMCHS/P4.

Corrige:
- JADES prioriza EAZY_z_a / EAZY_z500 antes que z_spec.
- Source_Name / JADES_ID tienen prioridad sobre ID numérico.
- Permite forzar columnas manualmente:
  --z-source, --name-source, --muv-source, --mass-source,
  --confirmed-source, --ref-source.
"""

from __future__ import annotations

import argparse
import glob
import sys
from pathlib import Path
from typing import Iterable, Optional

import numpy as np
import pandas as pd


ALIASES = {
    "name": [
        "Source_Name", "JADES_ID", "name", "Name", "object_id", "source_id",
        "SOURCE_ID", "ID", "id", "NUMBER", "NUMBER_1"
    ],
    "z": [
        "EAZY_z_a", "EAZY_z500", "z_best", "zbest", "z_phot", "zphot",
        "ZPHOT", "photoz", "phot_z", "EAZY_Z", "z_50", "z_median",
        "redshift", "z", "Z", "z_spec", "zspec", "ZBEST"
    ],
    "log_m_star": [
        "log_m_star", "log_Mstar", "logMstar", "logM", "log_m", "log_mass",
        "logmass", "lmass", "LMASS", "LOGMSTAR", "stellar_mass", "mass",
        "Mstar", "mstar", "MSTAR"
    ],
    "MUV": [
        "MUV", "M_UV", "Muv", "muv", "UVmag", "M_1500", "M1500",
        "abs_MUV", "M_UV_1500", "MUV_1500"
    ],
    "confirmed": [
        "flag_confirmed", "confirmed", "spec_confirmed", "is_spec",
        "has_specz", "z_type", "CONFIRMED"
    ],
    "ref": [
        "Survey_Area", "survey", "field", "FIELD", "ref", "reference",
        "SOURCE"
    ],
}


def _decode_value(x):
    if isinstance(x, bytes):
        return x.decode("utf-8", errors="replace")
    return x


def _find_column(df: pd.DataFrame, aliases: list[str]) -> Optional[str]:
    cols = {str(c).strip(): c for c in df.columns}
    lower = {str(c).strip().lower(): c for c in df.columns}
    for a in aliases:
        if a in cols:
            return cols[a]
        if a.lower() in lower:
            return lower[a.lower()]
    return None


def _manual_col(df: pd.DataFrame, col: Optional[str], label: str) -> Optional[str]:
    if not col:
        return None
    if col in df.columns:
        return col
    lower = {str(c).lower(): c for c in df.columns}
    if col.lower() in lower:
        return lower[col.lower()]
    raise ValueError(
        f"La columna manual '{col}' para {label} no existe. "
        f"Columnas disponibles: {list(df.columns)}"
    )


def read_table(path: Path) -> pd.DataFrame:
    suffix = path.suffix.lower()
    if suffix == ".csv":
        return pd.read_csv(path)
    if suffix in {".fits", ".fit"}:
        try:
            from astropy.table import Table
        except ImportError as exc:
            raise RuntimeError("Falta astropy. Instala con: pip install astropy") from exc
        table = Table.read(path)
        df = table.to_pandas()
        for col in df.columns:
            if df[col].dtype == object:
                df[col] = df[col].map(_decode_value)
        return df
    raise ValueError(f"Formato no soportado: {path}")


def inspect_file(path: Path, max_cols: int = 260) -> None:
    df = read_table(path)
    print("\n" + "=" * 90)
    print(f"Archivo: {path}")
    print(f"Filas: {len(df):,} | Columnas: {len(df.columns):,}")
    print("-" * 90)
    for i, col in enumerate(df.columns[:max_cols], start=1):
        s = df[col]
        nonnull = int(s.notna().sum())
        try:
            sample = ", ".join(str(v)[:70] for v in s.dropna().head(3).tolist())
        except Exception:
            sample = ""
        print(f"{i:03d}. {col} | {s.dtype} | non-null={nonnull:,} | {sample}")
    print("-" * 90)
    print("Detección automática:")
    for canon, aliases in ALIASES.items():
        print(f"  {canon:12s} <- {_find_column(df, aliases) or 'NO DETECTADA'}")


def _normalize_confirmed(series: pd.Series) -> pd.Series:
    if series.dtype == bool:
        return series.fillna(False)
    vals = series.astype(str).str.strip().str.lower()
    confirmed = vals.isin([
        "1", "true", "yes", "y", "spec", "spectroscopic", "confirmed",
        "specz", "zspec", "secure"
    ])
    return (confirmed | vals.str.contains("spec", na=False)).fillna(False)


def canonicalize(
    path: Path,
    dataset: str,
    *,
    name_source: Optional[str] = None,
    z_source: Optional[str] = None,
    mass_source: Optional[str] = None,
    muv_source: Optional[str] = None,
    confirmed_source: Optional[str] = None,
    ref_source: Optional[str] = None,
    z_min: Optional[float] = None,
    z_max: Optional[float] = None,
    drop_invalid_redshift: bool = True,
) -> pd.DataFrame:
    df = read_table(path)

    manual = {
        "name": _manual_col(df, name_source, "name"),
        "z": _manual_col(df, z_source, "z"),
        "log_m_star": _manual_col(df, mass_source, "log_m_star"),
        "MUV": _manual_col(df, muv_source, "MUV"),
        "confirmed": _manual_col(df, confirmed_source, "confirmed"),
        "ref": _manual_col(df, ref_source, "ref"),
    }
    detected = {k: manual[k] or _find_column(df, ALIASES[k]) for k in ALIASES}

    out = pd.DataFrame()
    out["name"] = df[detected["name"]].astype(str) if detected["name"] else [f"{dataset}_{i}" for i in range(len(df))]
    out["source"] = dataset

    out["z"] = pd.to_numeric(df[detected["z"]], errors="coerce") if detected["z"] else np.nan
    out.loc[out["z"] <= -100, "z"] = np.nan

    if detected["log_m_star"]:
        mass = pd.to_numeric(df[detected["log_m_star"]], errors="coerce")
        mass = mass.mask(mass <= -100)
        finite = mass[np.isfinite(mass)]
        if len(finite) and finite.median() > 100:
            mass = np.log10(mass.where(mass > 0))
        out["log_m_star"] = mass
    else:
        out["log_m_star"] = np.nan

    if detected["MUV"]:
        muv = pd.to_numeric(df[detected["MUV"]], errors="coerce")
        out["MUV"] = muv.mask(muv <= -1000)
    else:
        out["MUV"] = np.nan

    if detected["confirmed"]:
        out["confirmed"] = _normalize_confirmed(df[detected["confirmed"]])
    else:
        spec_col = "z_spec" if "z_spec" in df.columns else ("zspec" if "zspec" in df.columns else None)
        if spec_col:
            spec = pd.to_numeric(df[spec_col], errors="coerce")
            out["confirmed"] = np.isfinite(spec) & (spec > 0)
        else:
            out["confirmed"] = False

    out["ref"] = df[detected["ref"]].astype(str) if detected["ref"] else dataset
    out["input_file"] = str(path)
    out["notes"] = ""

    if z_min is not None:
        out = out[out["z"] >= z_min]
    if z_max is not None:
        out = out[out["z"] <= z_max]
    if drop_invalid_redshift:
        out = out[np.isfinite(out["z"])].copy()

    return out[["name", "source", "z", "log_m_star", "MUV", "confirmed", "ref", "input_file", "notes"]]


def expand_inputs(patterns: Iterable[str]) -> list[Path]:
    paths = []
    for raw in patterns:
        matches = glob.glob(raw)
        if matches:
            paths.extend(Path(m) for m in matches)
        else:
            p = Path(raw)
            if p.exists():
                paths.append(p)
            else:
                print(f"[WARN] No existe o no matchea: {raw}", file=sys.stderr)
    return sorted(set(paths))


def write_manifest(out_csv: Path, input_paths: list[Path], dataset: str, rows: int) -> None:
    manifest_dir = Path("data/manifests")
    manifest_dir.mkdir(parents=True, exist_ok=True)
    manifest = manifest_dir / "DATA_CONNECTION_LOG.md"
    block = [
        "",
        f"## {dataset} -> {out_csv}",
        "",
        f"- Rows exported: {rows}",
        "- Inputs:",
        *[f"  - `{p}`" for p in input_paths],
        "- Canonical columns: `name, source, z, log_m_star, MUV, confirmed, ref`",
        "- Note: missing physical columns are exported as blank/NaN; check before P4.",
        "",
    ]
    with manifest.open("a", encoding="utf-8") as f:
        f.write("\n".join(block))


def main() -> int:
    ap = argparse.ArgumentParser(description="Prepara catálogos JWST externos para SMCHS/P4.")
    ap.add_argument("--inspect", nargs="+")
    ap.add_argument("--dataset", choices=["jades", "jades_candidates", "ceers", "astrodeep", "other"], default="other")
    ap.add_argument("--input", nargs="+")
    ap.add_argument("--out")

    ap.add_argument("--name-source")
    ap.add_argument("--z-source")
    ap.add_argument("--mass-source")
    ap.add_argument("--muv-source")
    ap.add_argument("--confirmed-source")
    ap.add_argument("--ref-source")

    ap.add_argument("--z-min", type=float)
    ap.add_argument("--z-max", type=float)
    ap.add_argument("--keep-invalid-redshift", action="store_true")
    ap.add_argument("--union", nargs="+")

    args = ap.parse_args()

    if args.inspect:
        for p in expand_inputs(args.inspect):
            inspect_file(p)
        return 0

    if args.union:
        if not args.out:
            raise SystemExit("--union requiere --out")
        frames = [pd.read_csv(p) for p in expand_inputs(args.union)]
        if not frames:
            raise SystemExit("No hay CSVs para unir.")
        out = pd.concat(frames, ignore_index=True)
        out_path = Path(args.out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out.to_csv(out_path, index=False)
        print(f"[OK] Unión guardada: {out_path} | filas={len(out):,}")
        return 0

    if not args.input or not args.out:
        raise SystemExit("Usa --inspect o bien --dataset --input --out")

    paths = expand_inputs(args.input)
    if not paths:
        raise SystemExit("No encontré archivos de entrada.")

    frames = []
    for p in paths:
        print(f"[INFO] Procesando {p}")
        frames.append(canonicalize(
            p,
            dataset=args.dataset,
            name_source=args.name_source,
            z_source=args.z_source,
            mass_source=args.mass_source,
            muv_source=args.muv_source,
            confirmed_source=args.confirmed_source,
            ref_source=args.ref_source,
            z_min=args.z_min,
            z_max=args.z_max,
            drop_invalid_redshift=not args.keep_invalid_redshift,
        ))

    out = pd.concat(frames, ignore_index=True)
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(out_path, index=False)

    print(f"[OK] Guardado: {out_path}")
    print(f"[OK] Filas exportadas: {len(out):,}")
    print("[OK] Columnas:", ", ".join(out.columns))
    print("\nResumen de disponibilidad:")
    for col in ["z", "log_m_star", "MUV"]:
        n = int(out[col].notna().sum())
        print(f"  {col:12s}: {n:,}/{len(out):,}")
    print("\nPrimeras filas:")
    print(out.head(8).to_string(index=False))

    write_manifest(out_path, paths, args.dataset, len(out))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
