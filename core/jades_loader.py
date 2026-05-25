"""
core/jades_loader.py — Loader de catálogos JADES (FITS -> CSV)
SMCHS v0.5.4

Este módulo procesa los datos reales de JADES DR5 para su uso en el dashboard,
manteniendo la lógica de datos observacionales separada del núcleo Monte Carlo.
"""

import os
import logging
from pathlib import Path
import numpy as np
import pandas as pd
from astropy.table import Table

# Configuración de Rutas Universales
BASE_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = BASE_DIR / "data"
RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"

# Asegurar estructura de directorios
PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger("jades_loader")

def process_jades_dr5(filename="JADES_DR5_z_gt_8_Catalog_Hainline.fits"):
    """
    Carga el catálogo FITS de JADES DR5, extrae columnas clave,
    calcula z_best y exporta a un CSV compatible con SMCHS.
    """
    input_path = RAW_DIR / filename
    output_path = PROCESSED_DIR / "jades_dr5_smchs_ready.csv"
    
    # Búsqueda alternativa en data/jades/ si no está en raw/
    if not input_path.exists():
        input_path = DATA_DIR / "jades" / filename

    if not input_path.exists():
        logger.error(f"Archivo no encontrado: {input_path}")
        return None

    try:
        table = Table.read(input_path)
        df = table.to_pandas()
        # Decodificar strings si vienen como bytes (común en FITS)
        for col in df.select_dtypes([object]):
            df[col] = df[col].apply(lambda x: x.decode('utf-8') if isinstance(x, bytes) else x)
    except Exception as e:
        logger.error(f"Error al leer el FITS: {e}")
        return None

    # 1. Mapeo flexible de columnas para JADES DR5
    mapping = {
        'id': ['ID', 'id', 'id_jades'],
        'ra': ['RA', 'ra'],
        'dec': ['DEC', 'dec'],
        'z_spec': ['z_spec', 'Z_SPEC', 'zspec'],
        'z_phot': ['EAZY_z_a', 'z_phot_eazy', 'z_a_eazy', 'Z_PHOT_EAZY'],
        'M_UV': ['MUV', 'M_UV', 'm_uv'],
        'M_UV_err': ['MUV_err', 'M_UV_err', 'muv_err'],
        'beta': ['beta', 'BETA'],
        'beta_err': ['beta_err', 'BETA_ERR'],
        'area': ['Survey_Area', 'SURVEY_AREA', 'area']
    }
    
    df_clean = pd.DataFrame()
    for final_name, candidates in mapping.items():
        for cand in candidates:
            if cand in df.columns:
                df_clean[final_name] = df[cand]
                break

    # 2. Lógica z_best (z_spec tiene prioridad)
    if 'z_spec' in df_clean.columns and 'z_phot' in df_clean.columns:
        z_spec_valid = (df_clean['z_spec'] > 0) & (df_clean['z_spec'].notna())
        df_clean['z_best'] = np.where(
            z_spec_valid,
            df_clean['z_spec'],
            df_clean['z_phot']
        )
    else:
        logger.warning("Faltan columnas de redshift. Verifique los nombres en el FITS.")

    # 3. Filtrado (z_best > 8 según requerimiento)
    df_final = df_clean[df_clean['z_best'] > 8.0].copy()
    
    logger.info(f"Procesadas {len(df_final)} fuentes con z > 8")
    df_final.to_csv(output_path, index=False)
    logger.info(f"Guardado CSV listo para SMCHS en: {output_path}")

if __name__ == "__main__":
    process_jades_dr5()