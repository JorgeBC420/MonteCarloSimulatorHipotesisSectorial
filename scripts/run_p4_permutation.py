#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
scripts/run_p4_permutation.py

CLI para P4-v3.2.2 sobre dos CSVs: observación vs baseline.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path
from typing import Optional

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from analysis.p4_permutation import permutation_test_d_tail, summarize_p4_result


def _load_csv_column(
    path: Path,
    column: str,
    *,
    z_column: Optional[str] = None,
    z_min: Optional[float] = None,
    z_max: Optional[float] = None,
    muv_column: Optional[str] = None,
    muv_max: Optional[float] = None,
    mass_column: Optional[str] = None,
    mass_min: Optional[float] = None,
):
    if not path.exists():
        raise FileNotFoundError(path)
    df = pd.read_csv(path)
    if column not in df.columns:
        raise ValueError(f"Columna '{column}' no existe en {path}. Columnas: {list(df.columns)}")
    if z_column:
        if z_column not in df.columns:
            raise ValueError(f"z_column '{z_column}' no existe en {path}.")
        if z_min is not None:
            df = df[df[z_column] >= z_min]
        if z_max is not None:
            df = df[df[z_column] <= z_max]
    if muv_column and muv_max is not None:
        if muv_column not in df.columns:
            raise ValueError(f"muv_column '{muv_column}' no existe en {path}.")
        df = df[df[muv_column] <= muv_max]
    if mass_column and mass_min is not None:
        if mass_column not in df.columns:
            raise ValueError(f"mass_column '{mass_column}' no existe en {path}.")
        df = df[df[mass_column] >= mass_min]
    values = pd.to_numeric(df[column], errors="coerce").dropna().to_numpy()
    return values, len(df)


def main() -> int:
    ap = argparse.ArgumentParser(description="Ejecuta P4-v3.2.2 con permutation test.")
    ap.add_argument("--obs", required=True)
    ap.add_argument("--baseline", required=True)
    ap.add_argument("--column", required=True)
    ap.add_argument("--direction", choices=["high", "low"], default="high")
    ap.add_argument("--effect-threshold", type=float, default=0.15)
    ap.add_argument("--percentile", type=float, default=99)
    ap.add_argument("--n-iter", type=int, default=10_000)
    ap.add_argument("--alpha", type=float, default=0.05)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--z-column")
    ap.add_argument("--z-min", type=float)
    ap.add_argument("--z-max", type=float)
    ap.add_argument("--muv-column")
    ap.add_argument("--muv-max", type=float)
    ap.add_argument("--mass-column")
    ap.add_argument("--mass-min", type=float)
    ap.add_argument("--statistic-name", default="D_tail")
    ap.add_argument("--out")
    ap.add_argument("--json")

    args = ap.parse_args()

    obs_values, obs_after_filters = _load_csv_column(
        Path(args.obs), args.column,
        z_column=args.z_column, z_min=args.z_min, z_max=args.z_max,
        muv_column=args.muv_column, muv_max=args.muv_max,
        mass_column=args.mass_column, mass_min=args.mass_min,
    )
    base_values, base_after_filters = _load_csv_column(
        Path(args.baseline), args.column,
        z_column=args.z_column, z_min=args.z_min, z_max=args.z_max,
        muv_column=args.muv_column, muv_max=args.muv_max,
        mass_column=args.mass_column, mass_min=args.mass_min,
    )

    result = permutation_test_d_tail(
        obs_values, base_values,
        effect_threshold=args.effect_threshold,
        n_iter=args.n_iter,
        percentile=args.percentile,
        direction=args.direction,
        alpha=args.alpha,
        seed=args.seed,
        statistic_name=args.statistic_name,
    )

    print(summarize_p4_result(result))

    row = result.to_dict()
    row.update({
        "obs_file": args.obs,
        "baseline_file": args.baseline,
        "column": args.column,
        "obs_after_filters": obs_after_filters,
        "baseline_after_filters": base_after_filters,
        "z_column": args.z_column or "",
        "z_min": args.z_min if args.z_min is not None else "",
        "z_max": args.z_max if args.z_max is not None else "",
        "muv_column": args.muv_column or "",
        "muv_max": args.muv_max if args.muv_max is not None else "",
        "mass_column": args.mass_column or "",
        "mass_min": args.mass_min if args.mass_min is not None else "",
    })

    if args.out:
        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        with out.open("w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=list(row.keys()))
            writer.writeheader()
            writer.writerow(row)
        print(f"[OK] CSV: {out}")

    if args.json:
        outj = Path(args.json)
        outj.parent.mkdir(parents=True, exist_ok=True)
        outj.write_text(json.dumps(row, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"[OK] JSON: {outj}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
