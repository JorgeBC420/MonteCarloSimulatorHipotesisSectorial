# SMCHS TNG API mass hotfix

Archivos:

```text
baselines/tng_loader.py
scripts/fetch_tng_baseline.py
tests/test_tng_api_mass_loader.py
documentacion/TNG_API_MASS_HOTFIX.md
```

Test:

```powershell
python -m pytest tests/test_tng_api_mass_loader.py
```

Prueba:

```powershell
python scripts/fetch_tng_baseline.py --mode api --api-key $env:TNG_API_KEY --simulation TNG300-1 --snapshot 1 --max-objects 20 --out data/processed/tng_z15_test_ready.csv
```
