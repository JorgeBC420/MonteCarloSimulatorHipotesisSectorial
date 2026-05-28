# Hotfix 2 — prepare_external_observations.py

## Qué corrige

- JADES ya no usa `z_spec` como primera opción.
- Prioriza `EAZY_z_a`, `EAZY_z500`, `Source_Name`, `JADES_ID`.
- Permite forzar columnas manualmente.

## Reemplazar archivo

Copia:

```text
scripts/prepare_external_observations.py
```

encima del archivo actual.

## JADES DR5

```powershell
python scripts/prepare_external_observations.py `
  --dataset jades `
  --input "data/JADES_DDR_Z_GT_8_CATALOG_HAINLINE/JADES_DR5_z_gt_8_Catalog_Hainline.fits" `
  --name-source Source_Name `
  --z-source EAZY_z_a `
  --muv-source MUV `
  --ref-source Survey_Area `
  --out data/processed/jades_dr5_smchs_ready.csv
```

Esperado:

```text
Filas exportadas: 2,081
z: 2,081/2,081
MUV: 2,081/2,081
log_m_star: 0/2,081
```

## JADES Candidates

```powershell
python scripts/prepare_external_observations.py `
  --dataset jades_candidates `
  --input "data/JADES_DDR_Z_GT_8_CATALOG_HAINLINE/JADES_z_gt_8_Candidates_Hainline_et_al.fits" `
  --name-source JADES_ID `
  --z-source EAZY_z_a `
  --muv-source MUV `
  --out data/processed/jades_candidates_smchs_ready.csv
```

## P4 con JADES actual

Como no hay `log_m_star`, este JADES sirve para P4 por MUV:

```powershell
python scripts/run_p4_permutation.py `
  --obs data/processed/jades_dr5_smchs_ready.csv `
  --baseline data/processed/tng_z12_ready.csv `
  --column MUV `
  --direction low `
  --effect-threshold 0.5 `
  --z-column z --z-min 12 `
  --n-iter 10000 `
  --out outputs/p4_jades_vs_tng_muv.csv
```
