# Paquete P4-v3.2.2 — Permutation Test + Roadmap DAG

Archivos incluidos:

```text
analysis/p4_permutation.py
scripts/run_p4_permutation.py
tests/test_p4_permutation.py
documentacion/P4_V3_2_2_CRITERIO_CUANTITATIVO.md
documentacion/ROADMAP_OPERATIVO_DAG_V3_2_2.md
```

## Instalación manual

Copiar cada carpeta sobre la raíz del repositorio:

```bash
copy analysis\p4_permutation.py analysis\
copy scripts\run_p4_permutation.py scripts\
copy tests\test_p4_permutation.py tests\
copy documentacion\*.md documentacion\
```

En PowerShell desde la carpeta descomprimida:

```powershell
Copy-Item .\analysis\p4_permutation.py ..\analysis\
Copy-Item .\scripts\run_p4_permutation.py ..\scripts\
Copy-Item .\tests\test_p4_permutation.py ..\tests\
Copy-Item .\documentacion\*.md ..\documentacion\
```

## Test rápido

```bash
python -m pytest tests/test_p4_permutation.py
```

## Uso ejemplo: masa estelar

```bash
python scripts/run_p4_permutation.py ^
  --obs data/processed/jades_dr5_smchs_ready.csv ^
  --baseline data/processed/tng_z12_ready.csv ^
  --column log_m_star ^
  --direction high ^
  --effect-threshold 0.15 ^
  --z-column z --z-min 12 ^
  --n-iter 10000 ^
  --out outputs/p4_jades_vs_tng_mass.csv
```

## Uso ejemplo: MUV

```bash
python scripts/run_p4_permutation.py ^
  --obs data/processed/jades_dr5_smchs_ready.csv ^
  --baseline data/processed/tng_z12_ready.csv ^
  --column MUV ^
  --direction low ^
  --effect-threshold 0.5 ^
  --z-column z --z-min 12 ^
  --n-iter 10000 ^
  --out outputs/p4_jades_vs_tng_muv.csv
```

## Interpretación

`htsc_interest=True` significa:

```text
HTSC gana interés fenomenológico frente a ese baseline.
```

No significa confirmación de HTSC.
