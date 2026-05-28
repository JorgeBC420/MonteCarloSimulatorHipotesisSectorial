#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
scripts/check_required_data.py

Chequea datasets mínimos para SMCHS/P4.
"""

from pathlib import Path
import pandas as pd

REQUIRED = {
    "JADES DR5 ready": ("data/processed/jades_dr5_smchs_ready.csv", ["z", "MUV"]),
    "TNG z12 ready": ("data/processed/tng_z12_ready.csv", ["z"]),
    "SIMBA z12 ready": ("data/processed/simba_z12_ready.csv", ["z"]),
}

def main() -> int:
    ok_all = True
    for label, (path, cols) in REQUIRED.items():
        p = Path(path)
        if not p.exists():
            print(f"[MISSING] {label}: {path}")
            ok_all = False
            continue
        try:
            df = pd.read_csv(p, nrows=5)
            missing_cols = [c for c in cols if c not in df.columns]
            if missing_cols:
                print(f"[WARN] {label}: existe, pero faltan columnas {missing_cols}")
                ok_all = False
            else:
                print(f"[OK] {label}: {path}")
        except Exception as exc:
            print(f"[ERROR] {label}: {exc}")
            ok_all = False
    if not ok_all:
        print("\nVer data/manifests/DOWNLOAD_MANIFEST.md y DATA_CONNECTION_LOG.md")
        return 1
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
