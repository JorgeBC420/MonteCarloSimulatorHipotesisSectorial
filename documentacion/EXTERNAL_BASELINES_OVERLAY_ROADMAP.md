# SMCHS v0.5.5 — Baselines externos, overlay observacional y dilución métrica

Este patch agrega la base técnica para comparar SMCHS con catálogos observacionales o simulaciones externas **sin correr simulaciones hidrodinámicas completas**.

## Objetivo

Separar tres capas:

1. **SMCHS core**: Monte Carlo interno base/sectorial.
2. **Baselines externos**: JADES, IllustrisTNG, SIMBA u otros catálogos preprocesados.
3. **Comparación de colas**: métricas comunes como `D_tail`, `P_massive`, percentiles y overlay visual.

## Nuevos módulos

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

## Columnas canónicas para CSV externos

Los CSV de JADES/TNG/SIMBA pueden tener muchas columnas, pero el comparador espera convertirlas a:

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

No todas son obligatorias. Para comparar masa se requiere `z` y `log_m_star`. Para overlay UV se requiere `z` y `MUV`.

## Loader JADES

Ejemplo:

```bash
python -m data_loader.jades_loader --input data/raw/JADES_DR5_z_gt_8_Catalog_Hainline.fits
```

Salida:

```text
data/processed/jades_dr5_smchs_ready.csv
```

## Baseline externo en main.py

Puedes correr SMCHS y superponer un CSV/FITS externo:

```bash
python main.py --seed 42 --n 200000 --external-baseline data/processed/jades_dr5_smchs_ready.csv
```

Esto genera:

```text
outputs/fig12_observed_overlay.png
outputs/external_baseline_tail_metrics.csv
```

## Métricas nuevas

### P_massive

```math
P_{massive}=P(M_\star>M_{cut}\mid z>z_{cut})
```

### D_tail

```math
D_{tail}^{X}=Q99_X(M_\star\mid z>z_{cut})-Q99_{baseline}(M_\star\mid z>z_{cut})
```

### ΔP_massive

```math
\Delta P_{massive}^{X}=P_{massive}^{X}-P_{massive}^{baseline}
```

### Percentil de objetos observados

Para cada objeto observado:

```math
p_{model}(x_i)=\frac{\#\{M_{\star,model}<M_{\star,i},z>z_{cut}\}}{N_{model}(z>z_{cut})}
```

Sirve para preguntar si un objeto real cae en una cola menos extrema bajo el modelo sectorial que bajo el proxy ΛCDM.

## Dilución métrica opcional

La extensión opcional implementa:

```math
f_{rem}^{eff}(z)=\min\left[f_{max}, f_{rem,0}\left(\frac{1+z}{1+z_{ref}}\right)^{3(1+w)}\right]
```

Se activa con:

```bash
python main.py --seed 42 --n 200000 --metric-dilution --w-rem 0 --z-ref 12 --fmax 0.08
```

Interpretación:

- `w_rem=0`: remanentes tipo materia no relativista.
- `w_rem=1/3`: componente tipo radiación.
- `w_rem=-1`: componente aproximadamente constante.

**Importante:** está desactivado por defecto. El comportamiento histórico de SMCHS no cambia si no pasas `--metric-dilution`.

## Comparación con IllustrisTNG/SIMBA

No se descargan ni corren simulaciones completas. El flujo esperado es:

1. Preprocesar TNG/SIMBA a CSV pequeño con `z`, `log_m_star`, `MUV` si existe.
2. Cargar con `--external-baseline`.
3. Comparar `D_tail`, `P_massive`, `Q99` y overlay.

Ejemplo:

```bash
python main.py --seed 42 --n 200000 --external-baseline data/external/tng_highz_baseline.csv
```

## Criterio de prudencia

Estas métricas no demuestran la HTSC. Solo permiten preguntar:

> ¿La cola observada o simulada externamente se parece más al proxy ΛCDM interno, al SMCHS sectorial, o a baselines hidrodinámicos como TNG/SIMBA?

Si TNG/SIMBA/JADES explican la cola sin residuos persistentes, la necesidad explicativa de SMCHS disminuye. Si persisten residuos cuantificables, SMCHS gana interés fenomenológico, no confirmación.
