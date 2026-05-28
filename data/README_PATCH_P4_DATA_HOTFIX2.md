# SMCHS patch — P4 + Data Hotfix2 completo

Archivos incluidos:

```text
analysis/p4_permutation.py
scripts/run_p4_permutation.py
scripts/prepare_external_observations.py
scripts/check_required_data.py
tests/test_p4_permutation.py
documentacion/P4_V3_2_2_CRITERIO_CUANTITATIVO.md
documentacion/ROADMAP_OPERATIVO_DAG_V3_2_2.md
data/manifests/DOWNLOAD_MANIFEST.md
.gitattributes
README_PATCH_P4_DATA_HOTFIX2.md
```

## 1. Reemplazar/copiar

Descomprimir encima de la raíz del repo.

## 2. Probar P4

```powershell
python -m pytest tests/test_p4_permutation.py
```

## 3. Reconstruir JADES DR5

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

## 4. Reconstruir JADES Candidates

```powershell
python scripts/prepare_external_observations.py `
  --dataset jades_candidates `
  --input "data/JADES_DDR_Z_GT_8_CATALOG_HAINLINE/JADES_z_gt_8_Candidates_Hainline_et_al.fits" `
  --name-source JADES_ID `
  --z-source EAZY_z_a `
  --muv-source MUV `
  --out data/processed/jades_candidates_smchs_ready.csv
```

## 5. Revisar datos requeridos

```powershell
python scripts/check_required_data.py
```

## 6. Git LFS

```powershell
git lfs install
git add .gitattributes
git add data scripts analysis tests documentacion
git commit -m "Add P4 external test and JWST data connectors"
```
