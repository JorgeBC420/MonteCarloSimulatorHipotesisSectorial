# SMCHS v0.5.7-hotfix1

Archivos incluidos:

- `main.py`
- `core/parallel.py`
- `config_version_patch.diff` opcional para sincronizar metadata de versión

## Qué corrige

1. `--quench-uv` ahora se aplica también a la población base `ΛCDM` cuando el flag está activo.
2. `scan_frems_parallel()` ahora recibe y propaga:
   - `quench_uv`
   - `z_quench_thresh`
   - `m_quench_thresh`
   - `delta_uv_quench`
3. `heatmap_parallel()` también recibe los parámetros de quenching para evitar figuras inconsistentes.
4. La comparación sigue siendo pareada: mismo catálogo, misma semilla, mismo filtro observacional.

## Prueba de control recomendada

Antes de correr las 5 seeds completas:

```bash
python main.py --n 400000 --seed 42 --remnant-mode flat --no-heatmap
python main.py --n 400000 --seed 42 --remnant-mode flat --quench-uv --no-heatmap
python main.py --n 400000 --seed 42 --remnant-mode metric --quench-uv --no-heatmap
```

Luego comparar `outputs/metricas_por_f_rem.csv` entre flat y flat+quench. Ya no deberían ser idénticos si el filtro UV afecta detectabilidad/colas.

## Nota

No incluí un `config.py` completo para evitar sobreescribir accidentalmente la lista larga de objetos observacionales. El archivo `config_version_patch.diff` solo actualiza encabezado y constantes de versión.
