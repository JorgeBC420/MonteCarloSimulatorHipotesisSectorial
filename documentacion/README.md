# Simulador Monte Carlo de Hipótesis Sectorial (SMCHS)
### Monte Carlo Simulator for the Sectorial Hypothesis (MCSSH)

**Autor:** Jorge Eduardo Bravo Chaves  
**Hipótesis base:** Transición Sectorial Cosmológica — [HTSC v3.2.2](./HTSC_v3_2_1_Paper_Extendido_JorgeBravoChaves.pdf)  
**Versión del simulador:** 0.5.7-hotfix1  
**Cosmología:** Planck18 (astropy)  
**Licencia:** CC BY-NC-SA 4.0

---

## Descripción

Pipeline de 5 fases que compara dos modelos cosmológicos sobre la misma población base:

- **Modelo A (ΛCDM base):** galaxias cuya madurez depende solo del tiempo disponible desde el Big Bang sectorial.
- **Modelo B (Sectorial):** mismo ΛCDM, pero una fracción `f_rem` de objetos recibe una edad estructural previa `Δt_heredada`:

```
t_eff = t_ΛCDM + Δt_heredada
```

El análisis mide si el modelo sectorial produce exceso estadístico de galaxias tempranamente maduras sin destruir la distribución global.

> **Nota:** SMCHS es un experimento de **inyección-recuperación**, no evidencia directa de herencia sectorial.  
> `Δt_signal` se inyecta por construcción; el simulador prueba si esa señal hipotética sobrevive a filtros adversarios.  
> Ver [HTSC v3.2.2](./HTSC_v3_2_1_Paper_Extendido_JorgeBravoChaves.pdf) sección 6.

---

## Distinción de versiones

| Componente                                    | Versión        |
| --------------------------------------------- | -------------- |
| Hipótesis de Transición Sectorial Cosmológica | v3.2.2         |
| Simulador Monte Carlo (SMCHS / MCSSH)         | v0.5.7-hotfix1 |

El simulador implementa la hipótesis, pero su versión es independiente.  
Ver historial completo en [CHANGELOG.md](./CHANGELOG.md) y sección [Changelog](#changelog).

---

## Resultados técnicos — Batería post-hotfix

Batería limpia: N=400,000 · 5 semillas (42, 101, 202, 303, 404) · 3 escenarios.

| Escenario        | Runs | ΔQ99 > 0 | SNR ≥ 2 | SNR ≥ 3 | R medio | Exceso medio | ΔQ99 medio | SNR medio |
| ---------------- | ---- | -------- | ------- | ------- | ------- | ------------ | ---------- | --------- |
| flat             | 5    | 5/5      | 5/5     | 2/5     | 1.113×  | 11.3%        | 1.0870 Gyr | 2.936     |
| flat+quench_uv   | 5    | 5/5      | 5/5     | 0/5     | 1.101×  | 10.1%        | 0.8105 Gyr | 2.393     |
| metric+quench_uv | 5    | 5/5      | 5/5     | 0/5     | 1.129×  | 12.9%        | 0.9102 Gyr | 2.686     |

**Lectura:** la señal inyectada no se borra bajo ninguno de los tres escenarios. Esto no confirma HTSC; muestra resiliencia de la señal hipotética ante filtros adversarios. El paso decisivo es la comparación contra catálogos externos con criterios pre-registrados (ver [Predicción P4](#predicción-p4--falsabilidad-externa)).

---

## Estructura del proyecto

```
smchs/
├── config.py                            # Parámetros globales
├── main.py                              # Punto de entrada
├── requirements.txt
├── core/
│   ├── cosmologia.py                    # Tablas Planck18, muestreo z, Schechter
│   ├── poblacion.py                     # Pipeline Fases A–D + quench_uv (v0.5.7)
│   ├── run_archive.py                   # Archivo rotativo de corridas (v0.5.6)
│   ├── parallel.py                      # ThreadPoolExecutor adaptativo (v0.5.6)
│   ├── geometric_remnants.py            # Modo geometric: f_rem emergente (v0.5.6)
│   └── metric_dilution.py              # f_rem_eff(z) opcional (v0.5.5)
├── analysis/
│   ├── estadistica.py                   # KS, KL, ratio R, scan, heatmap
│   ├── exportar.py                      # Exportación CSV
│   └── p4_permutation.py               # Permutation test P4 (v3.2.2)
├── baselines/
│   ├── external_loader.py              # Carga CSV/FITS/parquet normalizado (v0.5.5)
│   ├── metrics.py                       # P_massive, D_tail, percentiles (v0.5.5)
│   ├── aligner.py                       # Cortes comunes z/masa/MUV (v0.5.5)
│   ├── tng_loader.py                    # Wrapper IllustrisTNG
│   └── simba_loader.py                 # Wrapper SIMBA
├── data_loader/
│   └── jades_loader.py                 # JADES DR5 FITS/CSV → smchs_ready.csv (v0.5.5)
├── scripts/
│   ├── verify.py                        # Compilación de sintaxis
│   ├── fetch_tng_baseline.py           # Consulta API TNG (requiere API key)
│   ├── fetch_simba_baseline.py         # SIMBA vía CAESAR (bloqueado, ver nota)
│   ├── run_p4_permutation.py           # Ejecuta test P4 completo
│   └── check_required_data.py         # Verifica data/ antes de P4
├── figures/
│   ├── graficas.py                      # Figuras 1–11
│   └── observed_overlay.py             # Fig 12: overlay JADES/TNG/SIMBA (v0.5.5)
├── documentacion/
│   ├── PRE_REGISTRO_PARAMETROS_SMCHS.md
│   ├── EXTERNAL_BASELINES_OVERLAY_ROADMAP.md
│   ├── P4_V3_2_2_CRITERIO_CUANTITATIVO.md
│   └── SMCHS_Comparativas_Redshift_CMB.pdf
├── tests/
│   └── test_p4_permutation.py
├── paper/
├── runs/
├── logs/                                # ZIPs rotativos (máx 20)
└── outputs/                             # Generado automáticamente
```

---

## Instalación

```bash
pip install -r requirements.txt
```

Python 3.10+, numpy >=1.24,<2.0; scipy >=1.10,<1.12; matplotlib >=3.7,<3.9; astropy >=5.3,<6.1.

---

## Uso

### Verificación rápida

```bash
python scripts/verify.py     # compila todos los .py del proyecto
python -m pytest tests/      # tests mínimos (omite astropy si no está)
```

### Corrida completa

```bash
python main.py
python main.py --quick                           # N=30k, sin heatmap
python main.py --seed 42 --n 400000             # semilla y N explícitos
python main.py --frem 0.02 --tprev 1.0 --zcut 10
python main.py --no-heatmap                     # ahorra ~60s
python main.py --no-archive                     # no empaqueta ZIP al terminar
```

### Modos de remanentes (`--remnant-mode`)

```bash
python main.py --remnant-mode flat              # default: f_rem fijo
python main.py --remnant-mode metric            # dilución métrica por z
python main.py --remnant-mode geometric         # f_rem emergente vía ψ sigmoide
```

El modo `geometric` usa `ψ_i ~ N(0,1)` ponderado por umbral sigmoide. El `f_rem` reportado es el efectivo observado, no el input. Parámetros: `--geo-psi-c`, `--geo-s-psi`. Ver [PRE_REGISTRO_PARAMETROS_SMCHS.md](./documentacion/PRE_REGISTRO_PARAMETROS_SMCHS.md).

### Supresión UV por quenching (`--quench-uv`)

```bash
python main.py --remnant-mode flat --quench-uv
python main.py --remnant-mode metric --quench-uv
```

Objetos con `Z_obs > 0.18` y `log_m > 9.5` reciben desplazamiento positivo en M_UV vía sigmoide suavizada:

```
ΔM_UV = delta_uv_quench × sigmoid(10 × (Z_obs − Z_QUENCH_THRESH))
```

Supresión máxima: +2.5 mag. Captura AGN feedback sin corte binario duro.

### Paralelismo

```bash
python main.py --workers 4    # limitar threads manualmente
```

Por defecto: `max(1, n_cores - 1)`. `scan_frems` y `heatmap_grid` corren en paralelo con catálogos independientes.

### Baselines externos

```bash
# Cargar JADES DR5
python -m data_loader.jades_loader --input data/raw/JADES_DR5_z_gt_8_Catalog_Hainline.fits

# Correr con baseline externo
python main.py --seed 42 --n 200000 --external-baseline data/processed/jades_dr5_smchs_ready.csv

# Dilución métrica opcional (desactivada por defecto)
python main.py --seed 42 --n 200000 --metric-dilution --w-rem 0 --z-ref 12 --fmax 0.08
```

### TNG API

```bash
python scripts/fetch_tng_baseline.py \
  --mode api \
  --api-key "TU_API_KEY" \
  --simulation TNG100-1 \
  --snapshot 4 \
  --max-objects 1000 \
  --out data/processed/tng_z12_ready.csv
```

> TNG API produce `log_m_star`, SFR y metalicidad. Para P4_MUV se requiere baseline fotométrico/mock sintético adicional.

---

## Parámetros CLI

| Argumento          | Default | Descripción                                           |
| ------------------ | ------- | ----------------------------------------------------- |
| `--frem`           | 0.01    | Fracción de remanentes (0.01 = 1%)                    |
| `--tprev`          | 0.7     | Madurez heredada promedio (Gyr)                       |
| `--zcut`           | 12.0    | Redshift de corte para análisis de anomalías          |
| `--n`              | 120000  | Número de objetos                                     |
| `--seed`           | 42      | Semilla global (SHA-256, estable entre sesiones)      |
| `--quick`          | False   | N=30k, sin heatmap                                    |
| `--no-heatmap`     | False   | Omite heatmap 2D (~60s)                               |
| `--no-archive`     | False   | No empaqueta ZIP al terminar                          |
| `--remnant-mode`   | flat    | `flat` / `metric` / `geometric`                       |
| `--quench-uv`      | False   | Activa supresión UV por quenching bariónico           |
| `--workers`        | auto    | Threads para scan/heatmap                             |
| `--geo-psi-c`      | 0.0     | Centro sigmoide modo geometric                        |
| `--geo-s-psi`      | 1.0     | Escala sigmoide modo geometric                        |
| `--metric-dilution`| False   | Activa f_rem_eff(z) variable                          |
| `--out`            | outputs | Directorio de salida                                  |
| `--fail-fast`      | False   | Detiene ejecución ante primer error                   |

---

## Salidas

### Figuras (PNG)

| Archivo                            | Contenido                                          |
| ---------------------------------- | -------------------------------------------------- |
| `fig1_distribucion_masa.png`       | Distribución log M★ con/sin filtro proxy           |
| `fig2_exceso_redshift.png`         | Fracción de galaxias masivas por bin de z          |
| `fig3_ks_colas.png`                | CDF comparativa + KS-test en cola                  |
| `fig4_correlacion_zm.png`          | Correlación Z–M★ (estructura diferencial)          |
| `fig5_delta_t.png`                 | Δtᵢ = t_chem − t_ΛCDM (Predicción P2)              |
| `fig6_scan_frems.png`              | P(anomalía), ratio R y KS-stat vs f_rem            |
| `fig7_heatmap.png`                 | Heatmap R(f_rem × t_previo)                        |
| `fig8_objetos_jwst.png`            | 13 objetos JWST/ALMA sobre nube simulada           |
| `fig9_signal_vs_observed.png`      | Separación Δt_signal vs Δt_observed                |
| `fig10_distribucion_dt_signal.png` | Distribución completa y cola positiva Δt_signal    |
| `fig11_snr_detectabilidad.png`     | ΔP_tail, SNR_tail_Q99 y Q99(dt_signal) vs f_rem    |
| `fig12_observed_overlay.png`       | Overlay JADES/TNG/SIMBA vs SMCHS (si hay baseline) |

### CSV

| Archivo                                  | Contenido                                         |
| ---------------------------------------- | ------------------------------------------------- |
| `metricas_por_f_rem.csv`                 | Métricas por valor de f_rem                       |
| `poblacion_muestra.csv`                  | Muestra de objetos individuales base + sectorial  |
| `heatmap_sensitivity_ratio.csv`          | Grilla R(f_rem, t_previo)                         |
| `external_baseline_tail_metrics.csv`     | Comparación cola vs baseline externo              |

### Archivo rotativo (`logs/`)

`core/run_archive.py` empaqueta `outputs/` + log en ZIP con timestamp UTC al terminar cada corrida. Máximo 20 ZIPs (FIFO). Cada ZIP incluye `MANIFEST.json` con todos los parámetros y tiempo de ejecución. Desactivable con `--no-archive`.

---

## Métricas principales

Para masa/anomalía global:

```
R(f_rem) = P(log M★ > 10.5 | z > 12, visible, sectorial)
           ────────────────────────────────────────────────
           P(log M★ > 10.5 | z > 12, visible, ΛCDM)
```

Para señal de madurez heredada (métricas de cola):

```
ΔP_tail      = P(Δt_signal > τ | sectorial) − P(Δt_signal > τ | ΛCDM)
SNR_tail_Q99 = (Q99_sectorial − Q99_base) / σ_ruido

D_tail_mass  = Q99(log M★)_obs − Q99(log M★)_baseline   ← P4 externo
D_tail_MUV   = Q1(MUV)_baseline − Q1(MUV)_obs           ← P4 externo
```

**Zona de interés:** R ≈ 1.5–3 o SNR_tail_Q99 > 2 con f_rem bajo/moderado.  
**Zona de riesgo:** R >> 3 con f_rem > 5%.

---

## Predicción P4 — Falsabilidad externa

Predicción operacional pre-registrada (HTSC v3.2.2, sección 9). Ver [P4_V3_2_2_CRITERIO_CUANTITATIVO.md](./documentacion/P4_V3_2_2_CRITERIO_CUANTITATIVO.md).

| Elemento            | Valor pre-registrado                                              |
| ------------------- | ----------------------------------------------------------------- |
| Dataset             | JADES DR5, ASTRODEEP-JWST, IllustrisTNG, SIMBA                   |
| Variables           | z, log_m_star, MUV, metalicidad proxy si disponible              |
| Cortes              | z_cut=12, masa mínima, límite MUV/completeness, flags confianza  |
| Estadístico masa    | D_tail_mass > 0.15 dex, permutation test unilateral N=10,000     |
| Estadístico MUV     | D_tail_MUV > 0.5 mag, permutation test unilateral N=10,000       |
| Significancia       | p < 0.05                                                         |
| Criterio de pérdida | Si ΛCDM refinado o TNG/SIMBA explican el exceso sin residuos     |

**Implementación:** `analysis/p4_permutation.py` + `scripts/run_p4_permutation.py`.

```bash
python scripts/run_p4_permutation.py \
  --jades data/processed/jades_dr5_smchs_ready.csv \
  --baseline data/processed/tng_z12_ready.csv \
  --n-iter 10000
```

> **Estado actual:** JADES DR5 conectado para MUV. TNG/SIMBA pendientes de baseline comparable. P4 real bloqueado hasta baseline externo válido.

---

## Estado de baselines externos

| Baseline      | Estado                                       | Nota                                                   |
| ------------- | -------------------------------------------- | ------------------------------------------------------ |
| JADES DR5     | ✅ Conectado                                 | `data/processed/jades_dr5_smchs_ready.csv`             |
| IllustrisTNG  | ⏳ Pendiente aprobación cuenta               | Solicitar en illustris-project.org                     |
| SIMBA/CAESAR  | ⚠️ Bloqueado                                 | `caesar` no compila en Python 3.11/Windows; requiere Python 3.10/Conda |
| P4_MUV        | ⚠️ Pendiente baseline fotométrico            | TNG group catalog da masa/SFR, no MUV directo          |

---

## Diseño: catálogo base pareado + ruido compartido

```python
# El catálogo almacena z, t_lcdm, log_m_seed, eps_Z, eps_M
catalogo = inicializar_catalogo(N)

# Todos los modelos usan los MISMOS objetos Y el MISMO ruido
pop_lcdm = construir_poblacion(catalogo, f_rem=0.0)
pop_sect = construir_poblacion(catalogo, f_rem=0.01)

# La única diferencia es f_rem → análisis contrafactual limpio
```

---

## Objetos observacionales de referencia

`OBS_OBJECTS` en `config.py` incluye 13 entradas (ampliado en v0.5.6):

```
JADES-GS-z14-0, JADES-GS-z13-0, MoM-z14, Maisie's Galaxy, Gz9p3,
Red Monsters (RUBIES-EGS/UDS), RUBIES-UDS-QG-z7, ZF-UDS-7329, Cosmic Vine
```

> **Advertencia:** valores **ilustrativos aproximados**, no base de datos calibrada. Los objetos son motivadores, no pruebas individuales de HTSC. Ver notas por objeto en `config.py`.

---

## Reproducibilidad

- Semillas derivadas con `hashlib.sha256`, no `hash()` de Python (inestable por `PYTHONHASHSEED`).
- El mismo `--seed` y parámetros producen siempre resultados idénticos.
- `MANIFEST.json` en cada ZIP documenta todos los parámetros de la corrida.

---

## Qué NO afirma este simulador

> *"La simulación muestra que una fracción pequeña de madurez heredada puede producir una cola estadística de objetos tempranamente maduros, convirtiendo la hipótesis sectorial en un escenario computacionalmente explorable."*

El simulador no demuestra la existencia de sectores previos. La comparación correcta es:

```
ΛCDM base  vs  ΛCDM + término de madurez heredada controlado
```

No: *SMCHS contra el Big Bang*.

---

## Changelog

El historial completo vive en [CHANGELOG.md](./CHANGELOG.md). Resumen:

| Versión          | Resumen                                                                    |
| ---------------- | -------------------------------------------------------------------------- |
| `v0.5.3`         | Baseline público anterior. Métricas de cola (Q95/Q99/SNR_tail) reemplazan mediana. |
| `v0.5.4+`        | Anexo metodológico: programa de comparativas graduadas con redshift, objetos JWST/ALMA, CMB. |
| `v0.5.5`         | Baselines externos: JADES loader, `external_loader`, `metrics`, `aligner`, `metric_dilution`, overlay fig12. |
| `v0.5.6`         | Archivado rotativo, `--remnant-mode` (flat/metric/geometric), paralelismo adaptativo, pre-registro, 13 objetos. |
| `v0.5.7`         | `--quench-uv`: supresión UV por quenching bariónico vía sigmoide en `poblacion.py`. |
| `v0.5.7-hotfix1` | Cableado de `--quench-uv` a `scan_frems_parallel()` y `heatmap_parallel()`. |
| `P4-v3.2.2`      | Permutation test externo; JADES conectado para MUV; TNG/SIMBA pendientes. |

---

## Roadmap técnico

| Fase | Acción                                                              | Depende de | Estado                             |
| ---- | ------------------------------------------------------------------- | ---------- | ---------------------------------- |
| A    | Metadata actualizada v0.5.7-hotfix1 / HTSC v3.2.2                  | —          | ✅ Completado                      |
| B    | JADES DR5 conectado a external_loader                               | A          | ✅ Completado                      |
| C1   | TNG API baseline (masa/SFR/metalicidad)                             | A          | ⏳ Pendiente aprobación cuenta     |
| C2   | SIMBA/CAESAR baseline                                               | A          | ⚠️ Bloqueado (Python 3.10/Conda)  |
| D    | Completeness NIRCam/MUV simplificado                                | C1         | ⏳ Pendiente                       |
| E    | Permutation test P4: D_tail vs TNG/SIMBA, N=10,000 iteraciones     | C1, D      | ⏳ Bloqueado hasta baseline        |
| F    | Apéndice C (SMBH fugitivos) como test paramétrico independiente     | Desacoplado| Continuo                           |

---

## Documentación interna

| Archivo                                                             | Contenido                                               |
| ------------------------------------------------------------------- | ------------------------------------------------------- |
| [HTSC v3.2.2 (PDF)](./HTSC_v3_2_1_Paper_Extendido_JorgeBravoChaves.pdf) | Paper completo con jerarquía epistemológica y predicciones |
| [HYPOTHESIS_v3.1.md](./HYPOTHESIS_v3.1.md)                          | Núcleo formal t(S₀) ≠ t(U)                              |
| [CHANGELOG.md](./CHANGELOG.md)                                      | Historial técnico completo                              |
| [AUDIT_REPORT.md](./AUDIT_REPORT.md)                                | Auditoría técnica v0.5.2                                |
| [STREAMLIT_DASHBOARD.md](./STREAMLIT_DASHBOARD.md)                  | Guía del dashboard interactivo                          |
| [STREAMLIT_CLOUD_HOTFIX.md](./STREAMLIT_CLOUD_HOTFIX.md)            | Hotfix para Streamlit Cloud                             |
| [documentacion/PRE_REGISTRO_PARAMETROS_SMCHS.md](./documentacion/PRE_REGISTRO_PARAMETROS_SMCHS.md) | Pre-registro formal de parámetros |
| [documentacion/EXTERNAL_BASELINES_OVERLAY_ROADMAP.md](./documentacion/EXTERNAL_BASELINES_OVERLAY_ROADMAP.md) | Roadmap baselines externos |
| [documentacion/P4_V3_2_2_CRITERIO_CUANTITATIVO.md](./documentacion/P4_V3_2_2_CRITERIO_CUANTITATIVO.md) | Criterios numéricos P4 pre-registrados |
| [documentacion/SMCHS_Comparativas_Redshift_CMB.pdf](./documentacion/SMCHS_Comparativas_Redshift_CMB.pdf) | Comparativas graduadas redshift/CMB |

---

## Referencias

- Aghanim et al. (Planck Collaboration, 2018). *A&A* 641, A6.
- ALMA Observatory (2025). Oxygen in most distant known galaxy JADES-GS-z14-0.
- Bravo Chaves, J. E. (2026). *HTSC v3.2.2*. Investigación independiente, San José, Costa Rica.
- Hainline et al. (2026). JADES Data Release 5: Galaxy Candidates at z > 8. arXiv:2601.15959.
- Merlin et al. (2024). ASTRODEEP-JWST. *A&A* 691, A240.
- Nelson et al. (2019). IllustrisTNG public data release.
- Davé et al. (2019). SIMBA: cosmological simulations with BH growth and feedback.
- Bento, Dowker & Zalel (2021). Past-infinite causal sets. arXiv:2109.10749.
