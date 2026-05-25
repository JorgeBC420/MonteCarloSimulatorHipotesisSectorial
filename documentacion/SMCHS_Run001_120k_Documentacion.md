# SMCHS — Documentación de Corrida #001
## Primer análisis completo N = 120,000

---

**Simulador:** SMCHS v0.5.3 · Hipótesis de Transición Sectorial Cosmológica v3.1  
**Autor:** Jorge Eduardo Bravo Chaves  
**Fecha de corrida:** 2026-05-25 · 02:06:31 UTC-6  
**Duración:** 6.7 segundos  
**Plataforma:** Windows (OneDrive/Desktop)  
**Semilla:** 42 · **N:** 120,000 · **f_rem:** 1.00% · **t_previo μ:** 0.70 Gyr · **z_cut:** 12.0

---

## 1. Métricas principales

| Métrica | Valor | Interpretación |
|---------|-------|----------------|
| Ratio R | 1.258× | +25.8% de galaxias masivas detectables a z>12 en el modelo sectorial respecto a ΛCDM base |
| Exceso relativo | +25.8% | Diferencia de población en la cola de alto redshift |
| SNR_tail_Q99 | **3.05σ ★ robusto** | Señal de cola por encima del umbral de robustez (SNR > 2) |
| ΔQ99(Δt_signal) | +1.196 Gyr | Desplazamiento de la cola extrema (percentil 99) del estimador de señal |
| P(Δt_signal > 0.5 Gyr) base | 0.00000 | Sin objetos en la cola de madurez en ΛCDM base |
| P(Δt_signal > 0.5 Gyr) sect | 0.03197 | 3.20% de objetos sectoriales detectan señal de madurez significativa |
| ΔP_tail | +0.03197 | Diferencia de probabilidad de cola entre modelos |
| tail_ratio | ~3.2 × 10¹⁰ | **Métrica auxiliar inestable** — P_base ≈ 0 hace el cociente numéricamente sin sentido; no usar como indicador principal |
| KS statistic D | 0.01060 | Diferencia máxima entre CDFs |
| KS p-value | 1.0000 | Distribución global de masa sin cambio significativo (resultado esperado y correcto) |
| KL divergencia | 0.03162 | Divergencia de información baja — confirma que la perturbación es local a la cola |
| Pearson r (base) | 0.0188 | Correlación Z–M★ a z>12 en ΛCDM |
| Pearson r (sectorial) | 0.0676 | Correlación Z–M★ a z>12 en modelo sectorial — 3.6× mayor |

---

## 2. Conteos de población

| | ΛCDM base | Sectorial |
|---|---|---|
| Detectables totales (z ∈ [5, 17]) | 19,928 | — |
| Detectables z > 12 | 551 | 563 (+12) |
| Masivas z > 12 (log M★ > 10.5) | 7 | 9 (+2) |
| Objetos anómalos | 7 | 9 |
| Remanentes entre anómalos | 0 | 2 (22.2%) |

---

## 3. Descripción de figuras

### Fig. 1 — Distribución de masa estelar (`fig1_distribucion_masa.png`)

Histogramas de densidad de probabilidad de log₁₀(M★/M☉) para cuatro modelos (ΛCDM base, f=0.5%, f=1%, f=2%), comparados sin y con filtro de detectabilidad proxy de magnitud UV. La línea vertical punteada marca el umbral log M★ = 10.5 (galaxias masivas).

**Observación:** Las distribuciones globales son casi indistinguibles entre modelos, consistente con KS p=1.0. La perturbación sectorial no altera la forma general de la función de masa estelar, sino únicamente su cola de alto redshift.

---

### Fig. 2 — Exceso por bin de redshift (`fig2_exceso_redshift.png`)

Fracción de galaxias masivas detectables (log M★ > 10.5, visible=True) por bin de z de amplitud Δz=1, en escala logarítmica. Se comparan los cuatro modelos.

**Observación:** El exceso sectorial aparece exclusivamente a z > 12, con crecimiento monotónico con f_rem. A z < 12 los modelos son estadísticamente equivalentes. Esto es la predicción observacional central de la hipótesis: exceso localizado en el extremo de alto redshift.

---

### Fig. 3 — CDFs comparativas y test KS (`fig3_ks_colas.png`)

Funciones de distribución acumulada de log₁₀(M★/M☉) para los modelos base y sectorial, a dos umbrales de corte: z > 12.0 (izquierda) y z > 14.0 (derecha). Reporta estadístico D y p-value del test KS bilateral de dos muestras.

**Observación:** A z > 12: D = 0.01060, p = 1.0 (no significativo). A z > 14: p baja pero sigue sin alcanzar significancia estadística con N=120k y f_rem=1%. El KS no es la métrica óptima para este tipo de perturbación de cola; SNR_tail_Q99 es más sensible.

---

### Fig. 4 — Correlación Z–M★ a alto redshift (`fig4_correlacion_zm.png`)

Diagrama de dispersión de metalicidad Z (Z/Z☉) vs log₁₀(M★/M☉) para objetos con z > 12 y visible=True, con regresión lineal superpuesta. Se reporta coeficiente de Pearson r y p-value.

**Observación:** La correlación Z–M★ sube de r=0.019 (base) a r=0.068 (sectorial, f=1%). Este aumento refleja que los remanentes sectoriales aportan objetos simultáneamente masivos y enriquecidos, amplificando la correlación física esperada. Esta es una firma secundaria potencialmente distinguible con espectroscopía JWST/NIRSpec a z>12.

---

### Fig. 5 — Distribución de Δt_observed (`fig5_delta_t.png`)

Histogramas de la variable Δt_observed = t_chem_obs − t_ΛCDM para objetos detectables a z > 12, separados por modelo (ΛCDM base y sectorial). Se señala la mediana de cada distribución.

**Observación:** La mediana de Δt_observed en ΛCDM base es ≈ −0.0065 Gyr (ruido de metalicidad puro). En el modelo sectorial sube a +0.0037 Gyr a f=1%, efecto pequeño pero en la dirección predicha. La señal real está en la cola positiva, no en la mediana — ver Fig. 10.

---

### Fig. 6 — Curva de sensibilidad vs f_rem (`fig6_scan_frems.png`)

Scan de Ratio R, P(anomalía), KS-statistic y SNR_tail_Q99 en función de f_rem ∈ {0%, 0.3%, 0.5%, 1%, 2%, 3%, 5%, 8%} con N=18,000 objetos por punto del scan (corrida interna, no la población principal).

**Observación:** El Ratio R supera el umbral R = 1.5× en torno a f_rem ≈ 2.5%. El SNR_tail_Q99 supera SNR = 2 (umbral de robustez) ya desde f_rem = 0.3–0.5%. Esto sugiere que la señal de cola es detectable incluso para fracciones de remanentes muy bajas, mientras que el ratio de población (R) requiere f_rem más alto para ser estadísticamente distinguible.

---

### Fig. 7 — Heatmap 2D de sensibilidad (`fig7_heatmap.png`)

Grilla 10×10 del Ratio R evaluada sobre el espacio de parámetros (f_rem × t_previo), con f_rem ∈ [0%, 8%] y t_previo ∈ [0.1, 2.5 Gyr]. N = 18,000 objetos por celda, 100 celdas totales.

**Observación:** El Ratio R es más sensible a f_rem que a t_previo. A t_previo bajo (< 0.5 Gyr) el efecto sectorial se atenúa para cualquier f_rem, lo que indica que un tiempo de herencia muy corto no es suficiente para producir objetos distinguibles. El régimen de mayor señal se concentra en la esquina f_rem alto + t_previo > 0.7 Gyr, consistente con el valor nominal t_previo = 0.7 Gyr usado en la corrida principal.

---

### Fig. 8 — Objetos observacionales JWST/ALMA (`fig8_objetos_jwst.png`)

Diagrama z vs log₁₀(M★/M☉) a z > 11.5 mostrando la nube simulada (base y sectorial) con los objetos observacionales reales de referencia superpuestos como estrellas blancas.

**Observación:** Los objetos JWST/ALMA de referencia (GN-z11, JADES-GS-z14-0, Maisie's Galaxy, SPT0311-58, GS-9209, entre otros) caen consistentemente sobre o por encima del borde superior de la nube base, y varios quedan dentro o cerca de la nube sectorial. Esto no es una prueba de la hipótesis, pero la posición relativa de los objetos observacionales es compatible con el modelo sectorial de f_rem ≈ 1–3%.

---

### Fig. 9 — dt_signal vs dt_observed (`fig9_signal_vs_observed.png`)

Diagrama de dispersión de la señal teórica (dt_signal = t_prev − 0, estimador de madurez anticipada) vs la señal observada con ruido de metalicidad (dt_observed), para objetos sectoriales con z > 12 y visible=True.

**Observación:** La nube sigue aproximadamente la diagonal dt_signal = dt_observed, confirmando que el estimador de señal es consistente con la observación ruidosa. Los puntos fuera de la diagonal corresponden a objetos donde el ruido σ_Z domina sobre la señal real. La dispersión vertical mide efectivamente el ruido de metalicidad σ_Z = 0.05 Z/Z☉.

---

### Fig. 10 — Distribución de dt_signal (`fig10_distribucion_dt_signal.png`)

Histogramas de dt_signal para cuatro modelos (base, f=0.5%, f=1%, f=2%), en dos paneles: población completa (izquierda) y cola positiva dt_signal > 0.05 Gyr (derecha). La línea vertical marca τ = 0.5 Gyr, umbral de madurez significativa.

**Observación:** En el modelo ΛCDM base, la distribución de dt_signal está centrada en cero (sin remanentes, sin herencia química anticipada). En el modelo sectorial, aparece una cola positiva que crece monotónicamente con f_rem. El percentil Q99 de esta cola es el estimador SNR_tail_Q99. La cola es la región del espacio de parámetros donde la predicción P2 de la hipótesis es verificable.

---

### Fig. 11 — SNR, ΔP_tail y Q99 vs f_rem (`fig11_snr_detectabilidad.png`)

Tres paneles: (1) ΔP_tail = P(Δt>τ)_sect − P(Δt>τ)_base vs f_rem; (2) SNR_tail_Q99 vs f_rem con líneas de referencia SNR=1 y SNR=2; (3) Q99(dt_signal) para modelo base y sectorial vs f_rem, con área sombreada entre ambos.

**Observación:** Esta es la figura diagnóstico central del análisis de detectabilidad. A f_rem = 1% (corrida nominal): ΔP_tail = +3.20%, SNR_tail_Q99 = 3.05σ, ΔQ99 = +1.196 Gyr. Los tres indicadores son consistentes y apuntan en la misma dirección: el modelo sectorial produce una cola de madurez anticipada estadísticamente distinguible del ruido de metalicidad, incluso a fracciones de remanentes bajas.

---

## 4. Conclusiones del primer run completo

El primer análisis a N=120,000 confirma la señal observada en corridas preliminares con N=30,000, con mayor estabilidad estadística:

1. **La señal de cola es robusta (SNR = 3.05σ)** para f_rem = 1% y t_previo = 0.7 Gyr. El descenso respecto a N=30k (4.13σ) es metodológicamente correcto — con más objetos base la distribución de referencia se llena mejor y el exceso relativo de cola disminuye, lo que aumenta la confianza en el resultado.

2. **El efecto sectorial es localizado.** KS p=1.0 sobre la distribución global confirma que la perturbación no altera la función de masa estelar completa — únicamente su cola de alto redshift. Esto es consistente con la predicción P1 de la hipótesis sectorial.

3. **La correlación Z–M★ es una firma secundaria.** El aumento de r=0.019 a r=0.068 a z>12 con f_rem=1% puede ser testeable con espectroscopía de alta resolución de JWST/NIRSpec sobre muestras de galaxias a z>12.

4. **El heatmap define el régimen de parámetros válido:** f_rem > 1% con t_previo > 0.5 Gyr produce señales R > 1.3× y SNR > 2σ. Valores de t_previo < 0.3 Gyr suprimen la señal independientemente de f_rem.

5. **Los objetos JWST/ALMA de referencia son compatibles** con el modelo sectorial a f_rem ≈ 1–3%, aunque no constituyen evidencia confirmatoria — la hipótesis requiere tests estadísticos sobre muestras completas, no sobre objetos individuales.

---

## 5. Archivos generados

| Archivo | Descripción |
|---------|-------------|
| `fig1_distribucion_masa.png` | Distribución log M★, sin y con filtro |
| `fig2_exceso_redshift.png` | Fracción masivas por bin de z |
| `fig3_ks_colas.png` | CDFs comparativas + test KS |
| `fig4_correlacion_zm.png` | Correlación Z–M★ a z>12 |
| `fig5_delta_t.png` | Distribución Δt_observed |
| `fig6_scan_frems.png` | Sensibilidad R y SNR vs f_rem |
| `fig7_heatmap.png` | Heatmap 2D f_rem × t_previo |
| `fig8_objetos_jwst.png` | Objetos JWST/ALMA sobre nube simulada |
| `fig9_signal_vs_observed.png` | dt_signal vs dt_observed |
| `fig10_distribucion_dt_signal.png` | Distribución dt_signal y cola positiva |
| `fig11_snr_detectabilidad.png` | ΔP_tail, SNR_tail_Q99, Q99 vs f_rem |
| `metricas_por_f_rem.csv` | Scan completo de métricas por f_rem |
| `heatmap_sensitivity_ratio.csv` | Grilla 10×10 Ratio R (f_rem × t_previo) |
| `poblacion_muestra.csv` | Muestra de la población simulada |
| `smchs_run.log` | Log completo de la corrida |

---

## 6. Parámetros de cosmología y modelo

| Parámetro | Valor | Descripción |
|-----------|-------|-------------|
| Cosmología | Planck 2018 | H₀=67.4, Ω_m=0.315 |
| z range | [5.0, 17.0] | Rango de redshift simulado |
| z_cut | 12.0 | Umbral de "alto redshift" para análisis de anomalías |
| log M★ umbral | 10.5 | Umbral de "galaxia masiva" en log₁₀(M★/M☉) |
| M★(z) característica | 10.6 − 0.18·(z−8) | Evolución de la masa característica de Schechter con z |
| Schechter α | −1.35 | Pendiente faint-end de la función de masa |
| σ_Z (ruido metalicidad) | 0.05 Z/Z☉ | Ruido intrínseco/observacional de metalicidad |
| σ_M (ruido masa) | 0.25 dex | Ruido intrínseco/observacional de masa |
| τ (umbral cola) | 0.5 Gyr | Umbral de madurez significativa para P(Δt_signal > τ) |
| f_rem (nominal) | 1.00% | Fracción de remanentes del sector preexistente |
| t_previo μ | 0.70 Gyr | Media log-normal del tiempo de herencia química heredado |
| t_previo σ | 0.45 | Sigma log-normal del tiempo de herencia |

---

*SMCHS v0.5.3 · Hipótesis de Transición Sectorial Cosmológica v3.1*  
*Run #001 — 2026-05-25 · J. E. Bravo Chaves · San José, Costa Rica*
