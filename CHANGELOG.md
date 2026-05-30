# CHANGELOG — SMCHS / MCSSH

Este archivo centraliza el historial que antes estaba distribuido entre README, documentación interna, logs y notas de auditoría.

---

## v0.5.7-hotfix1 — Quench UV conectado al scan/heatmap

**Estado:** validado por logs y pruebas multi-seed.

### Cambios

- `--quench-uv` se propaga a `scan_frems_parallel()`.
- `--quench-uv` se propaga a `heatmap_parallel()`.
- La base ΛCDM puede recibir el mismo filtro observacional cuando el flag está activo.
- Se evita que `flat` y `flat --quench-uv` produzcan métricas idénticas por fallo de cableado.
- Se mantiene compatibilidad con corridas anteriores.

### Motivación

Antes del hotfix, `metricas_por_f_rem.csv` podía salir idéntico con y sin `--quench-uv` porque el scan ignoraba el flag. El hotfix convierte `quench_uv` en parte real del pipeline estadístico.

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

Se implementa `quench_uv=False` como filtro adversario opcional. Cuando está activo, objetos que cumplen:

```text
Z_obs > Z_QUENCH_THRESH
log_m > M_QUENCH_THRESH
```

reciben una supresión positiva en magnitud UV:

```text
ΔM_UV = delta_uv_quench × sigmoid(10 × (Z_obs − Z_QUENCH_THRESH))
```

La sigmoide evita cortes binarios duros y permite supresión parcial cerca del umbral.

### Parámetros

| Parámetro | Valor | Nota |
|---|---:|---|
| `Z_QUENCH_THRESH` | `0.18` | Umbral interno en escala proxy Z del simulador. |
| `M_QUENCH_THRESH` | `9.5` | Masa mínima proxy para quenching/feedback. |
| `DELTA_UV_QUENCH` | `2.5 mag` | Supresión conservadora. |

### Propagación

```text
construir_poblacion()
construir_poblacion_geometric()
_construir_sect() en main.py
```

---

## v0.5.6 — Archivado, modos remanentes y paralelismo

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
| `metric` | Dilución métrica. |
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

## v0.5.5 — Versión puente

**Estado documental:** pendiente de reconstrucción.

Esta versión queda marcada como puente entre el baseline público `v0.5.3` y la refactorización documentada en `v0.5.6`.

No se atribuyen cambios específicos hasta revisar commits, notas internas o logs antiguos.

---

## v0.5.4 — Versión puente

**Estado documental:** pendiente de reconstrucción.

Esta versión queda marcada como puente posterior a `v0.5.3`.

No se atribuyen cambios específicos hasta revisar commits, notas internas o logs antiguos.

---

## v0.5.3 — Baseline público anterior

**Estado:** README público anterior.

Representa el estado previo del simulador antes de:

- archivado automático;
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
