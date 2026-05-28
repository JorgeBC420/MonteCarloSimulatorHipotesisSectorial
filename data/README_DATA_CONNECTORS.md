# SMCHS data connectors

Archivos:

```text
scripts/prepare_external_observations.py
data/manifests/DOWNLOAD_MANIFEST.md
```

## 1. Instalar dependencia si hace falta

```powershell
pip install astropy
```

## 2. Inspeccionar JADES

```powershell
python scripts/prepare_external_observations.py --inspect "data/JADES_DDR_Z_GT_8_CATALOG_HAINLINE/*.fits"
```

## 3. Inspeccionar CEERS

```powershell
python scripts/prepare_external_observations.py --inspect "data/CEERS_PR/*.fits"
```

## 4. Convertir JADES a formato SMCHS

```powershell
python scripts/prepare_external_observations.py `
  --dataset jades `
  --input "data/JADES_DDR_Z_GT_8_CATALOG_HAINLINE/JADES_DR5_z_gt_8_Catalog_Hainline.fits" `
  --out data/processed/jades_dr5_smchs_ready.csv
```

## 5. Convertir CEERS PR1.1 a formato SMCHS

```powershell
python scripts/prepare_external_observations.py `
  --dataset ceers `
  --input "data/CEERS_PR/CEERS_PR1.1_LW_SUPER_CATALOG.fits" `
  --out data/processed/ceers_pr11_smchs_ready.csv
```

## 6. Unir observaciones

```powershell
python scripts/prepare_external_observations.py `
  --union data/processed/jades_dr5_smchs_ready.csv data/processed/ceers_pr11_smchs_ready.csv `
  --out data/processed/observational_union_smchs_ready.csv
```

## 7. Revisar columnas antes de P4

```powershell
python -c "import pandas as pd; df=pd.read_csv('data/processed/jades_dr5_smchs_ready.csv'); print(df.head()); print(df.notna().sum())"
```

Para P4 mass necesitás `log_m_star`.
Para P4 MUV necesitás `MUV`.
