# DOWNLOAD_MANIFEST — datasets externos SMCHS/HTSC

Este manifiesto debe vivir en GitHub junto con los datos en Git LFS.

## JADES DR5 z>8 — Hainline et al.

- Carpeta local: `data/JADES_DDR_Z_GT_8_CATALOG_HAINLINE/`
- Archivo principal: `JADES_DR5_z_gt_8_Catalog_Hainline.fits`
- Uso: observación principal para P4-v3.2.2 por MUV.
- Salida canónica: `data/processed/jades_dr5_smchs_ready.csv`
- Columnas esperadas: `z`, `MUV`.
- Nota: este catálogo no trae `log_m_star`.

## JADES Candidates

- Carpeta local: `data/JADES_DDR_Z_GT_8_CATALOG_HAINLINE/`
- Archivo principal: `JADES_z_gt_8_Candidates_Hainline_et_al.fits`
- Uso: muestra secundaria/histórica para P4_MUV.
- Salida canónica: `data/processed/jades_candidates_smchs_ready.csv`.

## CEERS PR1.1

- Carpeta local: `data/CEERS_PR/`
- Uso: fotometría cruda/base.
- Nota: los FITS inspeccionados no traen directamente `MUV` ni `log_m_star`.
- Estado: no usar para P4 directo hasta tener photo-z/MUV/masas derivadas.

## Baselines TNG/SIMBA

- Estado: pendiente.
- Salidas esperadas:
  - `data/processed/tng_z12_ready.csv`
  - `data/processed/simba_z12_ready.csv`
- Columnas mínimas:
  - `z`
  - `MUV` para P4_MUV
  - `log_m_star` para P4_mass
