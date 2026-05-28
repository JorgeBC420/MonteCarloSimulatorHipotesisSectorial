# CHANGELOG — SMCHS / MCSSH

Este archivo centraliza el historial técnico de SMCHS que quedó distribuido entre README, documentos internos, logs, anexos metodológicos y notas de auditoría.

---

## v0.5.7-hotfix1 — Quench UV conectado al scan/heatmap

**Estado:** validado por logs y pruebas multi-semilla.

### Cambios

- `--quench-uv` se propaga correctamente a `scan_frems_parallel()`.
- `--quench-uv` se propaga correctamente a `heatmap_parallel()`.
- La base ΛCDM puede recibir el mismo filtro observacional cuando el flag está activo.
- Se evita que `flat` y `flat --quench-uv` produzcan `metricas_por_f_rem.csv` idéntico por fallo de cableado.
- Se conserva compatibilidad con corridas anteriores.

### Motivación

Antes del hotfix, el `metricas_por_f_rem.csv` podía salir idéntico con y sin `--quench-uv` porque el scan ignoraba el flag. El hotfix convierte `quench_uv` en parte real del pipeline estadístico.

---

## v0.5.7 — Supresión UV por quenching

**Estado:** implementado.

### Archivo principal

```text
core/poblacion.py
```

### Función afectada

```text
calcular_observables()
```

### Descripción

Se implementa `quench_uv=False` como filtro adversario opcional. Cuando está activo, objetos que cumplen simultáneamente:

```text
Z_obs > Z_QUENCH_THRESH
log_m > M_QUENCH_THRESH
```

reciben una supresión positiva en magnitud UV:

```text
ΔM_UV = delta_uv_quench × sigmoid(10 × (Z_obs − Z_QUENCH_THRESH))
```

La sigmoide evita un corte binario duro y permite supresión parcial cerca del umbral.

### Parámetros calibrados

| Parámetro | Valor | Nota |
|---|---:|---|
| `Z_QUENCH_THRESH` | `0.18` | Calibrado contra la distribución real del simulador; captura top de Z proxy y fracción relevante de remanentes. |
| `M_QUENCH_THRESH` | `9.5` | Masa mínima proxy para quenching / feedback. |
| `DELTA_UV_QUENCH` | `2.5 mag` | Supresión conservadora. |

### Propagación

```text
construir_poblacion()
construir_poblacion_geometric()
_construir_sect() en main.py
```

### Interpretación

El quenching UV penaliza precisamente las galaxias maduras que podrían sesgar la cola sectorial. Si la señal persiste bajo este filtro, el resultado es más robusto; si desaparece, el toy model pierde poder discriminativo bajo observabilidad más realista.

---

## v0.5.6 — Archivado, remnant-mode, geometric, paralelismo y pre-registro

**Estado:** implementado.

### 1. Archivo rotativo de corridas

Archivo:

```text
core/run_archive.py
```

Al terminar cada corrida, empaqueta:

```text
outputs/
smchs_run.log
MANIFEST.json
```

en:

```text
logs/smchs_run_YYYYMMDDTHHMMSSZ.zip
```

Reglas:

- máximo 20 ZIPs;
- eliminación FIFO del más antiguo al superar el límite;
- activado por defecto;
- desactivable con `--no-archive`;
- incluye parámetros y tiempo de ejecución.

### 2. `--remnant-mode`

Comandos:

```bash
python main.py --remnant-mode flat
python main.py --remnant-mode metric
python main.py --remnant-mode geometric
```

Modos:

| Modo | Descripción |
|---|---|
| `flat` | `f_rem` fijo. |
| `metric` | Dilución métrica, formalizada como modo explícito. |
| `geometric` | Fracción efectiva emergente desde fluctuación latente `ψ`. |

El modo `geometric` vive en:

```text
core/geometric_remnants.py
```

La fracción efectiva emerge de:

```text
ψ_i ~ N(0,1)
```

filtrada por umbral sigmoide y ponderada por dilución métrica.

### 3. Paralelismo adaptativo

Archivo:

```text
core/parallel.py
```

`scan_frems` y `heatmap_grid` usan `ThreadPoolExecutor` con:

```text
max_workers = max(1, n_cores - 1)
```

Puede limitarse con:

```bash
python main.py --workers N
```

### 4. Pre-registro

Archivo:

```text
documentacion/PRE_REGISTRO_PARAMETROS_SMCHS.md
```

Incluye:

- justificación de `t_prev_mu = 0.7 Gyr`;
- reducción desde `1.2 Gyr` por parsimonia;
- semillas de validación;
- reglas para cambios futuros.

### 5. Objetos observacionales ampliados

`OBS_OBJECTS` en `config.py` pasa de 4 a 13 entradas, incorporando objetos JWST/ALMA motivadores como:

```text
JADES-GS-z14-0
JADES-GS-z13-0
MoM-z14
RUBIES Red Monsters
RUBIES-UDS-QG-z7
ZF-UDS-7329
Gz9p3
Maisie's Galaxy
Cosmic Vine
```

Estos objetos son motivadores, no pruebas individuales de HTSC.

---

## v0.5.5 — Baselines externos, overlay observacional y dilución métrica

**Estado:** implementado como base técnica de comparación externa.

### Objetivo

Separar tres capas:

1. **SMCHS core:** Monte Carlo interno base / sectorial.
2. **Baselines externos:** JADES, IllustrisTNG, SIMBA u otros catálogos preprocesados.
3. **Comparación de colas:** métricas comunes como `D_tail`, `P_massive`, percentiles y overlay visual.

### Nuevos módulos

```text
baselines/
  external_loader.py   # carga CSV/FITS/parquet y normaliza columnas
  metrics.py           # tail_summary, D_tail, P_massive, percentiles
  aligner.py           # cortes comunes z, masa, MUV
  tng_loader.py        # wrapper semántico TNG
  simba_loader.py      # wrapper semántico SIMBA

data_loader/
  jades_loader.py      # JADES FITS/CSV -> data/processed/jades_dr5_smchs_ready.csv

core/
  metric_dilution.py   # f_rem_eff(z), gamma=3(1+w)

figures/
  observed_overlay.py  # fig12: superposición observacional/externa
```

### Columnas canónicas externas

```text
name
source
z
log_m_star
MUV
metallicity_proxy
sfr
volume_Mpc3
confirmed
```

No todas son obligatorias. Para comparación de masa se requiere `z` y `log_m_star`; para overlay UV se requiere `z` y `MUV`.

### Uso previsto

```bash
python main.py --seed 42 --n 200000 --external-baseline data/processed/jades_dr5_smchs_ready.csv
```

Salidas esperadas:

```text
outputs/fig12_observed_overlay.png
outputs/external_baseline_tail_metrics.csv
```

### Métricas nuevas

```text
P_massive = P(M_star > M_cut | z > z_cut)
D_tail^X = Q99_X(M_star | z > z_cut) - Q99_baseline(M_star | z > z_cut)
ΔP_massive^X = P_massive^X - P_massive^baseline
percentil_modelo(x_obs) = posición de x_obs en la CDF simulada
```

### Interpretación

v0.5.5 no convierte a JADES/TNG/SIMBA en confirmación de HTSC. Crea una capa común para preguntar si las colas observadas o externas son más compatibles con el modelo base, con el sectorial o con simulaciones externas bajo cortes comparables.

---

## v0.5.4+ — Anexo metodológico de comparativas redshift/CMB reales

**Estado:** anexo metodológico / programa de comparación por etapas.

### Documento asociado

```text
SMCHS_Comparativas_Redshift_CMB.pdf
```

### Propósito

Definir un programa de comparación graduada para que SMCHS deje de ser solo un toy model interno y empiece a dialogar con restricciones reales:

```text
redshift
objetos JWST/ALMA
edad cosmológica
CMB térmico
CMB anisotropías
supernovas/BAO
```

### Principio rector

La hipótesis sectorial no modifica el redshift observado ni la expansión dentro de `S₀`. Usa ΛCDM/Planck18 como fondo efectivo del sector observable y pregunta si una pequeña madurez heredada puede engrosar la cola de objetos tempranos maduros.

La comparación correcta queda formulada como:

```text
ΛCDM base
vs
ΛCDM + término de madurez heredada controlado
```

no como:

```text
SMCHS contra el Big Bang
```

### Etapas de comparación

| Etapa | Comparativa | Qué evalúa | Prioridad |
|---|---|---|---|
| 1 | Objetos JWST/ALMA | Superposición en z, masa proxy y metalicidad proxy | inmediata |
| 2 | Edad-redshift | Verificar que `t_LCDM(z)` se conserva y la señal entra solo como `t_eff` | inmediata |
| 3 | CMB térmico | Usar `T(z)=T0(1+z)` como restricción que no debe romperse | corto plazo |
| 4 | CMB anisotropías | No simular todavía `C_l`; requiere CLASS/CAMB o colaboración | futuro |
| 5 | Supernovas/BAO | Comparar expansión tardía si el modelo crece | futuro |

### Interpretación

v0.5.4+ establece el marco metodológico de compatibilidad con observables, especialmente redshift y CMB. No introduce todavía una prueba externa final; prepara el terreno conceptual y metodológico para v0.5.5.

---

## v0.5.3 — Baseline público anterior

**Estado:** README público anterior.

Representa el estado previo del simulador antes de:

- anexo metodológico redshift/CMB;
- baselines externos;
- overlay observacional;
- `--remnant-mode`;
- modo `geometric`;
- paralelismo adaptativo;
- quench UV;
- P4 externo;
- conexión JADES.

---

## P4-v3.2.2 — Prueba externa de cola

**Estado:** implementado como test estadístico; bloqueado hasta baseline externo comparable.

### Archivos

```text
analysis/p4_permutation.py
scripts/run_p4_permutation.py
tests/test_p4_permutation.py
documentacion/P4_V3_2_2_CRITERIO_CUANTITATIVO.md
```

### Estadísticos

```text
D_tail_mass = Q99(log M*)_obs − Q99(log M*)_baseline
D_tail_MUV  = Q1(MUV)_baseline − Q1(MUV)_obs
```

### Criterios iniciales

```text
D_tail_mass > 0.15 dex
D_tail_MUV > 0.5 mag
p < 0.05 por permutation test unilateral
```

### Estado de datos

```text
JADES DR5: conectado para MUV
TNG/SIMBA: pendientes de baseline comparable
```
