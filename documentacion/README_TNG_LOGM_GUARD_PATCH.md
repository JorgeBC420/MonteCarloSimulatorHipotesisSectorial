# SMCHS TNG log_m_star guard patch

Archivos:

```text
baselines/tng_loader.py
tests/test_tng_logm_guard.py
documentacion/TNG_LOGM_GUARD_PATCH.md
```

Este parche debe aplicarse encima del hotfix TNG API mass.

Comandos:

```powershell
Expand-Archive smchs_tng_logm_guard_patch.zip -DestinationPath . -Force
python -m pytest tests/test_tng_logm_guard.py
python scripts/fetch_tng_baseline.py --mode api --api-key $env:TNG_API_KEY --simulation TNG300-1 --snapshot 1 --max-objects 20 --out data/processed/tng_z15_test_ready.csv
```
