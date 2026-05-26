# Pre-Registro de Parámetros — SMCHS v0.5.6
**Hipótesis de Transición Sectorial Cosmológica v3.2.1**
**Autor:** Jorge Eduardo Bravo Chaves
**Fecha de congelamiento:** 2026-05-26

---

## Propósito

Este documento registra los parámetros del simulador **antes** de cualquier
comparación sistemática contra catálogos externos (JADES DR5, IllustrisTNG,
SIMBA). Su función es distinguir decisiones tomadas a priori (con justificación
física o de parsimonia) de ajustes realizados a posteriori para mejorar el fit.

Cualquier cambio posterior debe documentarse como **nueva versión experimental**
y no mezclar sus resultados con los de la versión base registrada aquí.

---

## Parámetros Congelados — Validación Inicial

### Corrida principal

| Parámetro      | Valor          | Justificación                                                                                         |
|----------------|----------------|-------------------------------------------------------------------------------------------------------|
| `N`            | 120 000        | Balance entre resolución estadística y tiempo de cómputo en i7 1255U                                |
| `f_rem`        | 0.01 (1%)      | Escenario conservador. Se evaluó 1.2% y se bajó a 1% para evitar sobreajuste visible                |
| `t_prev_mu`    | 0.7 Gyr        | Escenario conservador. 1.2 Gyr producía señal fuerte interpretable como sobreajuste                 |
| `t_prev_sig`   | 0.45           | Dispersión log-normal estándar; no ajustada para mejorar resultados                                 |
| `z_cut`        | 12.0           | Umbral de "alto redshift" consistente con límite de detección efectivo de JADES                     |
| `tau_tail`     | 0.5 Gyr        | Umbral de madurez significativa para P(Δt > τ); elegido antes de ver distribuciones                |
| `SEED`         | 42             | Semilla global reproducible estándar                                                                 |
| `remnant_mode` | flat           | Modelo base sin extensiones; dilución métrica y modo geométrico son experimentales                  |

### Semillas para validación multi-semilla

```
seeds = [1, 2, 3, 4, 5, 42, 99, 123, 777, 2026]
```

La corrida principal usa seed=42. Las corridas de validación cruzada deben usar
todas las semillas del rango arriba sin re-seleccionar basándose en resultados.

---

## Historia de Ajustes (Registro Cronológico)

| Fecha      | Parámetro   | Valor anterior | Valor nuevo | Razón documentada                                                              |
|------------|-------------|----------------|-------------|--------------------------------------------------------------------------------|
| Pre-2026   | `t_prev_mu` | 1.2 Gyr        | 0.7 Gyr     | 1.2 Gyr producía cola fuerte sin poder discriminar entre f_rem pequeños; se bajó para escenario conservador |
| 2026-05-26 | —           | —              | —           | Congelamiento formal para comparación JADES/TNG/SIMBA                          |

---

## Parámetros del Modo Geométrico (Experimental)

> **Estado:** extensión exploratoria. NO reemplaza el modelo base.
> Congelados para evitar sobreajuste en modo geométrico.

| Parámetro  | Valor | Justificación                                                              |
|------------|-------|----------------------------------------------------------------------------|
| `geo_f0`   | 0.01  | Mismo orden que f_rem flat para comparación directa                        |
| `geo_psi_c`| 0.5   | Umbral conservador: solo fluctuaciones > 0.5σ generan remanentes          |
| `geo_s_psi`| 0.3   | Transición suave; no ajustado para maximizar señal                        |
| `geo_z_ref`| 12.0  | Consistente con z_cut de análisis                                          |
| `geo_w_rem`| 0.0   | Materia no relativista (γ=3); caso estándar                               |
| `geo_f_max`| 0.08  | Límite de seguridad; evita fracciones de remanentes físicamente absurdas  |

---

## Criterio de Selección de t_prev_mu = 0.7 Gyr

`t_prev_mu = 0.7 Gyr` **no se interpreta como una constante física estimada empíricamente**.
Es un parámetro conservador de exploración. Su elección satisface simultáneamente:

1. **SNR_tail > 1** en la cola Q99 a z > 12 con N = 120 000 → señal mínimamente detectable.
2. **KS p-value > 0.05** entre base y sectorial en la distribución global → no deforma la población.
3. **No maximización**: 1.2 Gyr fue descartado porque producía señal tan fuerte que cualquier f_rem pequeño "ganaba" sin discriminación.

El rango completo explorado es:

```
t_prev_explorado = [0.3, 0.5, 0.7, 1.0, 1.2, 2.0]  # Gyr
```

Los resultados de este scan deben reportarse completos, no solo el punto base.

---

## Parámetros de Supresión UV por Quenching (v0.5.7)

> **Estado:** desactivado por defecto (`--quench-uv` off). Comparación conservadora.
> Congelados antes de comparar contra JADES DR5.

| Parámetro          | Valor | Justificación física                                                                                   |
|--------------------|-------|--------------------------------------------------------------------------------------------------------|
| `Z_QUENCH_THRESH`  | 0.35  | Galaxias con >35% Z☉ han procesado suficiente gas para autoquench (consistente con RUBIES-UDS-QG-z7) |
| `M_QUENCH_THRESH`  | 9.5   | Por debajo no hay masa suficiente para quenching vía AGN feedback (Bower et al. 2006)                |
| `DELTA_UV_QUENCH`  | 2.5   | Desplazamiento UV máximo conservador; galaxias con SFR≈0 pueden ser 3-5 mag más débiles (Salim 2007) |

### Cómo usar en comparación

```bash
# Filtro base (retrocompatible con todas las corridas anteriores)
python main.py --remnant-mode flat

# Filtro conservador: penaliza galaxias maduras → señal más robusta si persiste
python main.py --remnant-mode flat --quench-uv

# Combinación más estricta
python main.py --remnant-mode metric --quench-uv
```

### Interpretación metodológica

- Si la cola sectorial **persiste** con `--quench-uv`: resultado más robusto (sobrevivió filtro que la penaliza).
- Si la cola **desaparece** con `--quench-uv`: el toy model pierde poder discriminativo bajo observabilidad más realista → señal depende del sesgo de sobredetección.
- En ambos casos el resultado es informativo. El comparador es la misma corrida con `--quench-uv` aplicado también al modelo ΛCDM base (catálogo pareado: mismos objetos, mismo quenching).

1. **Ningún parámetro se modifica después de ver los datos de JADES DR5** sin abrir una nueva versión de este documento.
2. Si un parámetro cambia por justificación física (no por fit visual), se documenta aquí con: fecha, razón física específica, y referencia al paper o datos que lo motivaron.
3. El scan completo de f_rem (`FREMS_SCAN`) se reporta siempre íntegro. No se selecciona el "mejor" punto sin mostrar el rango.
4. Las corridas de modo geométrico se reportan como **experimento separado** con sus propios parámetros congelados. Sus resultados no se mezclan con los del modo flat en tablas de comparación principal.

---

## Frase de Protocolo (para incluir en el paper)

> `t_prev_mu = 0.7 Gyr` representa el escenario conservador donde la señal
> sectorial es mínimamente detectable en la cola estadística (SNR_tail > 1)
> sin deformar la distribución global (KS global p > 0.05). Valores por encima
> de ~1.0 Gyr producen señales más fuertes pero con menor poder discriminativo.
> Valores por debajo de ~0.3 Gyr producen señal indetectable en corridas de
> N = 120 000, estableciendo el límite inferior de sensibilidad del toy model.
> El valor base adoptado fue fijado **antes** de la comparación contra catálogos
> externos, conforme al pre-registro de parámetros de este documento.
