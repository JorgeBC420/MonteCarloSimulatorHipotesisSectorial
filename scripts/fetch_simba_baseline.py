#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Generate data/processed/simba_z12_ready.csv from SIMBA local/CAESAR catalog."""
from __future__ import annotations

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from baselines.simba_loader import export_simba_ready_csv, load_simba_baseline


def main() -> int:
    ap = argparse.ArgumentParser(description="Prepara baseline SIMBA para P4.")
    ap.add_argument("--mode", choices=["local", "caesar"], required=True)
    ap.add_argument("--path", help="CSV/FITS/parquet local ya procesado.")
    ap.add_argument("--caesar-path", help="Catálogo CAESAR HDF5.")
    ap.add_argument("--snapshot-redshift", type=float)
    ap.add_argument("--min-log-m-star", type=float)
    ap.add_argument("--z-min", type=float, default=None)
    ap.add_argument("--z-max", type=float, default=None)
    ap.add_argument("--out", default="data/processed/simba_z12_ready.csv")
    args = ap.parse_args()

    if args.mode == "local":
        if not args.path:
            raise SystemExit("--mode local requiere --path")
        df = load_simba_baseline(args.path)
    else:
        if not args.caesar_path:
            raise SystemExit("--mode caesar requiere --caesar-path")
        df = load_simba_baseline(
            caesar_path=args.caesar_path,
            snapshot_redshift=args.snapshot_redshift,
            min_log_m_star=args.min_log_m_star,
        )

    out = export_simba_ready_csv(df, args.out, z_min=args.z_min, z_max=args.z_max)
    print(f"[OK] SIMBA baseline exportado: {out}")
    print(f"[OK] Filas: {len(df):,}")
    print("Disponibilidad:")
    for col in ["z", "log_m_star", "MUV"]:
        print(f"  {col}: {df[col].notna().sum():,}/{len(df):,}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
