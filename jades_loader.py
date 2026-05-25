"""
utils/jades_loader.py — Loader de catálogos JADES (FITS -> CSV)
SMCHS v0.5.4 — Módulo independiente de ingesta de datos.
"""

import logging
from pathlib import Path
import numpy as np
import pandas as pd
from astropy.table import Table
import sys
import os

# Añadir raíz al path para importar config
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import config as cfg

logger = logging.getLogger("jades_loader")

def process_jades_dr5(filename="JADES_DR5_z_gt_8_Catalog_Hainline.fits"):
    """
    Carga FITS, extrae columnas útiles y crea z_best para el simulador.
    """
    input_path = cfg.RAW_DIR / filename
    output_path = cfg.PROCESSED_DIR / "jades_dr5_smchs_ready.csv"
    
    if not input_path.exists():
        logger.error(f"No se encontró el archivo FITS en {input_path}")
        return

    logger.info(f"Procesando {filename}...")
    try:
        table = Table.read(input_path)
        df = table.to_pandas()
        # Limpieza de byte-strings (necesario para FITS leídos en Windows/Linux)
        for col in df.select_dtypes([object]):
            df[col] = df[col].apply(lambda x: x.decode('utf-8') if isinstance(x, bytes) else x)
    except Exception as e:
        logger.error(f"Error al leer FITS: {e}")
        return

    # Mapeo flexible de columnas de JADES DR5
    mapping = {
        'id': ['ID', 'id', 'id_jades'],
        'z_spec': ['z_spec', 'Z_SPEC', 'zspec'],
        'z_phot': ['EAZY_z_a', 'z_phot_eazy', 'Z_PHOT_EAZY', 'z_a'],
        'M_UV': ['MUV', 'M_UV', 'm_uv'],
        'log_m': ['log_m', 'mstar', 'MSTAR', 'logM']
    }

    df_clean = pd.DataFrame()
    for final_name, candidates in mapping.items():
        for cand in candidates:
            if cand in df.columns:
                df_clean[final_name] = df[cand].copy()
                break

    # Lógica de Redshift Best
    if 'z_phot' in df_clean.columns:
        if 'z_spec' in df_clean.columns:
            valid_spec = (df_clean['z_spec'] > 0) & (df_clean['z_spec'].notna())
            df_clean['z_best'] = np.where(valid_spec, df_clean['z_spec'], df_clean['z_phot'])
        else:
            df_clean['z_best'] = df_clean['z_phot']
        
        # Filtrado para SMCHS
        df_final = df_clean[df_clean['z_best'] > 8.0].copy()
        df_final.to_csv(output_path, index=False)
        logger.info(f"Éxito: {len(df_final)} fuentes guardadas en {output_path}")
    else:
        logger.error("No se encontraron columnas de redshift compatibles.")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    process_jades_dr5()