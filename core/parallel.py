"""
core/parallel.py — Paralelismo adaptativo para scan y heatmap
SMCHS v0.5.6 / Hipótesis Sectorial v3.2.1

Estrategia
----------
- Usa ThreadPoolExecutor (no ProcessPool) para evitar overhead de serialización
  de numpy arrays entre procesos. El GIL no es el cuello de botella aquí porque
  numpy libera el GIL en operaciones de array.
- Detecta automáticamente los cores disponibles y usa max(1, n_cores - 1)
  para no saturar el equipo.
- Fallback a ejecución serial si algo falla (no rompe la corrida).
- Límite de RAM estimado: cada worker usa ~50 MB para N=18k; con 4 workers
  son ~200 MB, seguro para equipos con 8+ GB. Para 16 GB (i7 1255U) se puede
  subir a 6-8 workers sin problema.

Uso
---
    from core.parallel import scan_frems_parallel, heatmap_parallel

    # Reemplaza directamente a las funciones seriales de estadistica.py
    resultados = scan_frems_parallel(catalogo, frems, t_mu, z_cut)
    frems, tprevs, grid = heatmap_parallel(z_cut, frems, tprevs, n)
"""

from __future__ import annotations

import logging
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any

import numpy as np

import config as cfg
from core.poblacion import construir_poblacion, inicializar_catalogo
from analysis.estadistica import metricas_completas, p_cola, FREMS_SCAN, HEATMAP_FREMS, HEATMAP_TPREVS

logger = logging.getLogger(__name__)


def _n_workers(max_workers: int | None = None) -> int:
    """
    Detecta cores disponibles y devuelve un número seguro de workers.
    Reserva 1 core para el sistema operativo.
    """
    n_cpu = os.cpu_count() or 1
    safe  = max(1, n_cpu - 1)
    if max_workers is not None:
        safe = min(safe, max_workers)
    return safe


# ── scan_frems paralelo ────────────────────────────────────────────────────────

def _scan_worker(
    fr: float,
    catalogo: dict,
    pop_base: dict,
    t_mu: float,
    z_cut: float,
    metric_dilution: bool,
    w_rem: float,
    z_ref: float,
    f_max: float,
) -> dict:
    """Worker para un único valor de f_rem."""
    pop = construir_poblacion(
        catalogo, f_rem=fr, t_mu=t_mu,
        metric_dilution=metric_dilution,
        w_rem=w_rem, z_ref=z_ref, f_max=f_max,
    )
    return metricas_completas(pop_base, pop, z_cut)


def scan_frems_parallel(
    catalogo: dict,
    frems: list | None = None,
    t_mu: float | None = None,
    z_cut: float = cfg.Z_CUT,
    metric_dilution: bool = False,
    w_rem: float = 0.0,
    z_ref: float = 12.0,
    f_max: float = 0.08,
    max_workers: int | None = None,
) -> list:
    """
    Versión paralela de scan_frems. Mantiene el mismo output que la versión serial.
    El catálogo base y pop_base se construyen una sola vez antes del loop.

    Parámetros
    ----------
    max_workers:
        Número máximo de threads. None = detección automática.

    Retorna
    -------
    Lista de dicts con métricas, en el mismo orden que frems.
    """
    from config import T_PREV_MU

    frems  = frems if frems is not None else list(FREMS_SCAN)
    t_mu   = t_mu  if t_mu  is not None else T_PREV_MU
    n_w    = _n_workers(max_workers)

    logger.info("[parallel] scan_frems con %d workers para %d valores de f_rem", n_w, len(frems))

    # Control ΛCDM construido una sola vez
    pop_base = construir_poblacion(catalogo, f_rem=0.0, t_mu=t_mu)

    # Si hay 1 worker o pocos items, mejor serial para evitar overhead
    if n_w <= 1 or len(frems) <= 2:
        logger.info("[parallel] Usando modo serial (n_workers=%d)", n_w)
        resultados = []
        for fr in frems:
            logger.info("scan f_rem=%.3f%%", fr * 100)
            resultados.append(
                _scan_worker(fr, catalogo, pop_base, t_mu, z_cut,
                             metric_dilution, w_rem, z_ref, f_max)
            )
        return resultados

    # Ejecución paralela con orden preservado
    resultados: list[dict | None] = [None] * len(frems)
    try:
        with ThreadPoolExecutor(max_workers=n_w) as pool:
            futures = {
                pool.submit(
                    _scan_worker, fr, catalogo, pop_base, t_mu, z_cut,
                    metric_dilution, w_rem, z_ref, f_max
                ): i
                for i, fr in enumerate(frems)
            }
            for fut in as_completed(futures):
                idx = futures[fut]
                try:
                    resultados[idx] = fut.result()
                    logger.info("[parallel] scan f_rem=%.3f%% ✓", frems[idx] * 100)
                except Exception:
                    logger.exception("[parallel] Error en scan f_rem=%.3f%%", frems[idx] * 100)
                    # Fallback: calcular en el hilo principal
                    resultados[idx] = _scan_worker(
                        frems[idx], catalogo, pop_base, t_mu, z_cut,
                        metric_dilution, w_rem, z_ref, f_max,
                    )
    except Exception:
        logger.exception("[parallel] Error general en scan paralelo; usando serial")
        return _scan_serial_fallback(catalogo, pop_base, frems, t_mu, z_cut,
                                     metric_dilution, w_rem, z_ref, f_max)

    return [r for r in resultados if r is not None]


def _scan_serial_fallback(
    catalogo, pop_base, frems, t_mu, z_cut, metric_dilution, w_rem, z_ref, f_max
) -> list:
    resultados = []
    for fr in frems:
        resultados.append(
            _scan_worker(fr, catalogo, pop_base, t_mu, z_cut,
                         metric_dilution, w_rem, z_ref, f_max)
        )
    return resultados


# ── heatmap paralelo ──────────────────────────────────────────────────────────

def _heatmap_row_worker(
    i: int,
    tp: float,
    frems: np.ndarray,
    n: int,
    z_cut: float,
) -> tuple[int, np.ndarray]:
    """Worker para una fila del heatmap (un valor de t_prev)."""
    rng_row      = np.random.default_rng(cfg.SEED + 10_000 + i)
    cat_row      = inicializar_catalogo(n, rng_row)
    pop_base_row = construir_poblacion(cat_row, f_rem=0.0, t_mu=tp)
    p0_row       = p_cola(pop_base_row, z_cut)

    fila = np.zeros(len(frems))
    for j, fr in enumerate(frems):
        pop       = construir_poblacion(cat_row, f_rem=fr, t_mu=tp)
        fila[j]   = p_cola(pop, z_cut) / (p0_row + 1e-12)

    return i, fila


def heatmap_parallel(
    z_cut: float = cfg.Z_CUT,
    frems: np.ndarray | None = None,
    tprevs: np.ndarray | None = None,
    n: int = cfg.N_HEATMAP,
    max_workers: int | None = None,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Versión paralela de heatmap_grid. Paraleliza sobre filas (t_prev).
    Cada fila es independiente (catálogo propio), por lo que la paralelización
    es limpia sin condiciones de carrera.

    Retorna (frems, tprevs, ratio_grid) igual que heatmap_grid serial.
    """
    frems  = frems  if frems  is not None else HEATMAP_FREMS
    tprevs = tprevs if tprevs is not None else HEATMAP_TPREVS
    n_w    = _n_workers(max_workers)

    grid  = np.zeros((len(tprevs), len(frems)))
    total = len(tprevs)

    logger.info("[parallel] heatmap %d×%d con %d workers", total, len(frems), n_w)

    if n_w <= 1 or total <= 2:
        # Serial
        for i, tp in enumerate(tprevs):
            _, fila = _heatmap_row_worker(i, tp, frems, n, z_cut)
            grid[i] = fila
            logger.info("[parallel] heatmap fila %d/%d ✓", i + 1, total)
        return frems, tprevs, grid

    try:
        with ThreadPoolExecutor(max_workers=n_w) as pool:
            futures = {
                pool.submit(_heatmap_row_worker, i, tp, frems, n, z_cut): i
                for i, tp in enumerate(tprevs)
            }
            for fut in as_completed(futures):
                i = futures[fut]
                try:
                    row_i, fila = fut.result()
                    grid[row_i] = fila
                    logger.info("[parallel] heatmap fila %d/%d ✓", row_i + 1, total)
                except Exception:
                    logger.exception("[parallel] Error en heatmap fila %d", i)
                    # Fallback serial para esta fila
                    _, fila = _heatmap_row_worker(i, tprevs[i], frems, n, z_cut)
                    grid[i] = fila
    except Exception:
        logger.exception("[parallel] Error general en heatmap paralelo; usando serial")
        for i, tp in enumerate(tprevs):
            _, fila = _heatmap_row_worker(i, tp, frems, n, z_cut)
            grid[i] = fila

    return frems, tprevs, grid
