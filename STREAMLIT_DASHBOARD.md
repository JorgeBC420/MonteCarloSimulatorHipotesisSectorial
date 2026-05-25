# Dashboard Streamlit - SMCHS / MCSSH

Este dashboard permite explorar interactivamente el **Simulador Monte Carlo de Hipótesis Sectorial**.

## Ejecutar

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Qué muestra

- Métricas principales: `Ratio R`, `ΔP_tail`, `SNR_tail,Q99`, `KS p-value`.
- Distribuciones de masa y exceso por redshift.
- Separación `Δt_signal`, `Δt_observed` y `Δt_noise`.
- Tabla ilustrativa de objetos JWST/ALMA.
- Roadmap de comparativas con redshift real y CMB.

## Advertencia metodológica

El dashboard **no confirma** la Hipótesis de Transición Sectorial. Es una herramienta exploratoria para evaluar si una fracción pequeña de madurez heredada puede producir colas estadísticas en galaxias tempranas sin desplazar toda la distribución poblacional.

La señal esperada no está en la mediana: está en la cola. Por eso el dashboard prioriza `Q99`, `ΔP_tail` y `SNR_tail,Q99`.

## Uso recomendado

- Exploración: `N=30,000`.
- Corrida final: usar `python main.py --seed 42` con `N=120,000`.
- No usar los objetos observacionales incluidos como datos calibrados. Son referencias aproximadas para visualización.
