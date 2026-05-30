# TNG API mass hotfix

El endpoint resumido de subhalos trae SFR, pero no siempre trae `mass_stars`.
El detalle `/subhalos/{id}/` sí trae `mass_stars`, `mass_dm`, `mass_gas`, `len_stars`.

Este hotfix calcula:

```text
M_star = mass_stars * 1e10 / h
log_m_star = log10(M_star)
```

Uso:

```powershell
python scripts/fetch_tng_baseline.py --mode api --api-key $env:TNG_API_KEY --simulation TNG300-1 --snapshot 1 --max-objects 20 --out data/processed/tng_z15_test_ready.csv
```

Con filtro de calidad:

```powershell
python scripts/fetch_tng_baseline.py --mode api --api-key $env:TNG_API_KEY --simulation TNG300-1 --snapshot 1 --max-objects 1000 --min-len-stars 10 --out data/processed/tng_z15_ready.csv
```

Nota: `MUV` seguirá vacío en este endpoint. Este baseline sirve para masa/SFR, no para P4_MUV contra JADES.
