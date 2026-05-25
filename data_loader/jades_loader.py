"""
data_loader/jades_loader.py — Loader JADES DR5 FITS/CSV → SMCHS-ready CSV
SMCHS v0.5.5

Uso:
    python -m data_loader.jades_loader --input data/raw/JADES_DR5_z_gt_8_Catalog_Hainline.fits

Salida default:
    data/processed/jades_dr5_smchs_ready.csv
"""
from __future__ import annotations

import argparse
from pathlib import Path
import numpy as np
import pandas as pd

import config as cfg
from baselines.external_loader import load_external_catalog, save_normalized_catalog


def prepare_jades_catalog(input_path: str | Path, output_path: str | Path | None = None) -> Path:
    df = load_external_catalog(input_path, source_name="JADES")

    # z_best ya queda como z en la normalización. Mantener aliases útiles.
    if "MUV" in df.columns and "log_m_star" not in df.columns:
        # No inferir masa real desde MUV: solo dejar la columna ausente.
        pass

    # Filtrar a z>8 para respetar el catálogo DR5 del paper.
    df = df[df["z"] > 8.0].copy().reset_index(drop=True)
    if "confirmed" not in df.columns:
        df["confirmed"] = False

    out = Path(output_path) if output_path else (cfg.PROCESSED_DIR / "jades_dr5_smchs_ready.csv")
    return save_normalized_catalog(df, out)


def main() -> int:
    p = argparse.ArgumentParser(description="Convierte JADES DR5 a CSV compatible con SMCHS")
    p.add_argument("--input", required=True, help="Ruta a FITS/CSV JADES")
    p.add_argument("--output", default=None, help="CSV de salida")
    args = p.parse_args()
    out = prepare_jades_catalog(args.input, args.output)
    print(f"CSV JADES listo: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
