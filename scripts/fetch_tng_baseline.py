#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import annotations

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from baselines.tng_loader import export_tng_ready_csv, load_tng_baseline


def main() -> int:
    ap = argparse.ArgumentParser(description="Prepara baseline IllustrisTNG para P4.")
    ap.add_argument("--mode", choices=["local", "groupcat", "api"], required=True)
    ap.add_argument("--path")
    ap.add_argument("--base-path")
    ap.add_argument("--snapshot", type=int)
    ap.add_argument("--snapshot-redshift", type=float)
    ap.add_argument("--api-key")
    ap.add_argument("--simulation", default="TNG300-1")
    ap.add_argument("--max-objects", type=int, default=1000)
    ap.add_argument("--min-log-m-star", type=float)
    ap.add_argument("--min-len-stars", type=int)
    ap.add_argument("--h", type=float, default=0.6774)
    ap.add_argument("--sleep-s", type=float, default=0.02)
    ap.add_argument("--no-detail", action="store_true")
    ap.add_argument("--z-min", type=float)
    ap.add_argument("--z-max", type=float)
    ap.add_argument("--out", default="data/processed/tng_ready.csv")
    args = ap.parse_args()

    if args.mode == "local":
        if not args.path:
            raise SystemExit("--mode local requiere --path")
        df = load_tng_baseline(args.path)
    elif args.mode == "groupcat":
        if not args.base_path or args.snapshot is None:
            raise SystemExit("--mode groupcat requiere --base-path y --snapshot")
        df = load_tng_baseline(
            base_path=args.base_path,
            snapshot=args.snapshot,
            snapshot_redshift=args.snapshot_redshift,
            min_log_m_star=args.min_log_m_star,
            min_len_stars=args.min_len_stars,
            h=args.h,
        )
    else:
        if not args.api_key or args.snapshot is None:
            raise SystemExit("--mode api requiere --api-key y --snapshot")
        df = load_tng_baseline(
            api_key=args.api_key,
            simulation=args.simulation,
            snapshot=args.snapshot,
            max_objects=args.max_objects,
            min_log_m_star=args.min_log_m_star,
            min_len_stars=args.min_len_stars,
            h=args.h,
            sleep_s=args.sleep_s,
            detail=not args.no_detail,
        )

    out = export_tng_ready_csv(df, args.out, z_min=args.z_min, z_max=args.z_max)
    print(f"[OK] TNG baseline exportado: {out}")
    print(f"[OK] Filas: {len(df):,}")
    print("Disponibilidad:")
    for col in ["z", "log_m_star", "MUV", "sfr", "mass_stars_msun", "mass_dm_msun", "len_stars"]:
        if col in df.columns:
            print(f"  {col}: {df[col].notna().sum():,}/{len(df):,}")
    if len(df):
        print("\nVista rápida:")
        cols = [c for c in ["name", "z", "log_m_star", "MUV", "sfr", "mass_stars_msun", "mass_dm_msun", "len_stars"] if c in df.columns]
        print(df[cols].head(8).to_string(index=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
