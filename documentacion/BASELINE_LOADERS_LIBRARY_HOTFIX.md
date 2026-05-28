# Baseline loaders TNG/SIMBA — hotfix biblioteca/API

## Qué se corrigió

Los loaders anteriores solo aceptaban un archivo local ya preprocesado:

```python
load_external_catalog(path, source_name="IllustrisTNG")
```

Ahora los loaders conservan compatibilidad local, pero agregan rutas de biblioteca/API:

## IllustrisTNG

Opciones:

1. Archivo local ya preparado:

```powershell
python scripts/fetch_tng_baseline.py --mode local --path data/raw/tng/catalog.csv
```

2. Group catalog local con `illustris_python`:

```powershell
python scripts/fetch_tng_baseline.py `
  --mode groupcat `
  --base-path "D:/TNG/TNG100-1/output" `
  --snapshot 4 `
  --snapshot-redshift 12.0 `
  --out data/processed/tng_z12_ready.csv
```

3. API con key:

```powershell
python scripts/fetch_tng_baseline.py `
  --mode api `
  --api-key "TU_API_KEY" `
  --simulation TNG100-1 `
  --snapshot 4 `
  --max-objects 1000 `
  --out data/processed/tng_z12_ready.csv
```

## SIMBA

Opciones:

1. Archivo local ya preparado:

```powershell
python scripts/fetch_simba_baseline.py --mode local --path data/raw/simba/catalog.csv
```

2. Catálogo CAESAR local:

```powershell
python scripts/fetch_simba_baseline.py `
  --mode caesar `
  --caesar-path data/raw/simba/m100n1024_XXX.hdf5 `
  --snapshot-redshift 12.0 `
  --out data/processed/simba_z12_ready.csv
```

## Advertencia científica

Estos loaders pueden producir `log_m_star` si la biblioteca/catálogo lo permite.

No prometen `MUV`. Para P4_MUV se necesita un baseline con magnitudes UV sintéticas o comparables. Si `MUV` queda vacío, no usar ese baseline para P4_MUV.
