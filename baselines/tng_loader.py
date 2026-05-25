"""Wrapper semántico para catálogos IllustrisTNG preprocesados a CSV/FITS."""
from __future__ import annotations
from pathlib import Path
import pandas as pd
from .external_loader import load_external_catalog


def load_tng_baseline(path: str | Path) -> pd.DataFrame:
    return load_external_catalog(path, source_name="IllustrisTNG")
