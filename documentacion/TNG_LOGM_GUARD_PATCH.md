# TNG log_m_star guard patch

Este parche aplica la mejora sugerida:

- Si existe una columna logarítmica (`log_m_star`, `logMstar`, etc.) pero está vacía/all-NaN, no bloquea el fallback.
- Si existe `mass_stars`, se convierte directamente a masa estelar física:

```text
M_star = mass_stars * 1e10 / h
log_m_star = log10(M_star)
```

- `mass_log_msun` no se usa como masa estelar porque en TNG API representa masa total del subhalo, no `M_star`.

Prueba:

```powershell
python -m pytest tests/test_tng_logm_guard.py
python scripts/fetch_tng_baseline.py --mode api --api-key $env:TNG_API_KEY --simulation TNG300-1 --snapshot 1 --max-objects 20 --out data/processed/tng_z15_test_ready.csv
```
