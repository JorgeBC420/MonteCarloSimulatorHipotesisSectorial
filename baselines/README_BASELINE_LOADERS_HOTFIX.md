# SMCHS baseline loaders hotfix — library/API

Archivos incluidos:

```text
baselines/tng_loader.py
baselines/simba_loader.py
scripts/fetch_tng_baseline.py
scripts/fetch_simba_baseline.py
tests/test_baseline_loaders.py
documentacion/BASELINE_LOADERS_LIBRARY_HOTFIX.md
```

## Test rápido

```powershell
python -m pytest tests/test_baseline_loaders.py
```

## TNG desde API

```powershell
python scripts/fetch_tng_baseline.py `
  --mode api `
  --api-key "TU_API_KEY" `
  --simulation TNG100-1 `
  --snapshot 4 `
  --max-objects 1000 `
  --out data/processed/tng_z12_ready.csv
```

## TNG desde groupcat local

```powershell
python scripts/fetch_tng_baseline.py `
  --mode groupcat `
  --base-path "D:/TNG/TNG100-1/output" `
  --snapshot 4 `
  --snapshot-redshift 12.0 `
  --out data/processed/tng_z12_ready.csv
```

## SIMBA desde CAESAR

```powershell
python scripts/fetch_simba_baseline.py `
  --mode caesar `
  --caesar-path data/raw/simba/catalog.hdf5 `
  --snapshot-redshift 12.0 `
  --out data/processed/simba_z12_ready.csv
```

## Nota

Esto corrige la intención original: el loader ya no es solo wrapper de archivos preprocesados. Aun así, P4_MUV requiere un baseline con `MUV`; los group catalogs crudos normalmente no lo traen.
