"""
core/parallel.py — Paralelismo adaptativo para scan y heatmap
SMCHS v0.5.7-hotfix1 / Hipótesis Sectorial v3.2.1

Hotfix v0.5.7-hotfix1
----------------------
- Propaga quench_uv y sus parámetros al scan_frems_parallel().
- Construye pop_base con los mismos filtros observacionales que la población sectorial.
- Propaga quench_uv al heatmap_parallel() para que los mapas sean consistentes
  con corridas que usan --quench-uv.

Estrategia
----------
- Usa ThreadPoolExecutor para evitar overhead de serialización de numpy arrays.
- Detecta automáticamente cores disponibles y reserva 1 core para el sistema.
- Fallback serial si algo falla.
"""

from __future__ import annotations

import logging
import os
from concurrent.futures import ThreadPoolExecutor, as_completed

import numpy as np

import config as cfg
from analysis.estadistica import (
    FREMS_SCAN,
    HEATMAP_FREMS,
    HEATMAP_TPREVS,
    metricas_completas,
    p_cola,
)
from core.poblacion import construir_poblacion, inicializar_catalogo

logger = logging.getLogger(__name__)


def _n_workers(max_workers: int | None = None) -> int:
    """Detecta cores disponibles y devuelve un número seguro de workers."""
    n_cpu = os.cpu_count() or 1
    safe = max(1, n_cpu - 1)
    if max_workers is not None:
        safe = min(safe, max_workers)
    return safe


def _quench_kwargs(
    quench_uv: bool = False,
    z_quench_thresh: float = cfg.Z_QUENCH_THRESH,
    m_quench_thresh: float = cfg.M_QUENCH_THRESH,
    delta_uv_quench: float = cfg.DELTA_UV_QUENCH,
) -> dict:
    """Empaqueta parámetros de quenching para evitar divergencia entre paths."""
    return {
        "quench_uv": quench_uv,
        "z_quench_thresh": z_quench_thresh,
        "m_quench_thresh": m_quench_thresh,
        "delta_uv_quench": delta_uv_quench,
    }


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
    quench_uv: bool = False,
    z_quench_thresh: float = cfg.Z_QUENCH_THRESH,
    m_quench_thresh: float = cfg.M_QUENCH_THRESH,
    delta_uv_quench: float = cfg.DELTA_UV_QUENCH,
) -> dict:
    """Worker para un único valor de f_rem."""
    pop = construir_poblacion(
        catalogo,
        f_rem=fr,
        t_mu=t_mu,
        metric_dilution=metric_dilution,
        w_rem=w_rem,
        z_ref=z_ref,
        f_max=f_max,
        **_quench_kwargs(
            quench_uv=quench_uv,
            z_quench_thresh=z_quench_thresh,
            m_quench_thresh=m_quench_thresh,
            delta_uv_quench=delta_uv_quench,
        ),
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
    quench_uv: bool = False,
    z_quench_thresh: float = cfg.Z_QUENCH_THRESH,
    m_quench_thresh: float = cfg.M_QUENCH_THRESH,
    delta_uv_quench: float = cfg.DELTA_UV_QUENCH,
) -> list:
    """
    Versión paralela de scan_frems.

    Mantiene el mismo output que la versión serial, pero ahora respeta
    --quench-uv. La población base y cada población sectorial se construyen
    con el mismo filtro observacional cuando quench_uv=True.
    """
    from config import T_PREV_MU

    frems = frems if frems is not None else list(FREMS_SCAN)
    t_mu = t_mu if t_mu is not None else T_PREV_MU
    n_w = _n_workers(max_workers)

    logger.info(
        "[parallel] scan_frems con %d workers para %d valores de f_rem | quench_uv=%s",
        n_w,
        len(frems),
        "ON" if quench_uv else "off",
    )

    # Control ΛCDM construido una sola vez, con el mismo filtro observacional.
    pop_base = construir_poblacion(
        catalogo,
        f_rem=0.0,
        t_mu=t_mu,
        **_quench_kwargs(
            quench_uv=quench_uv,
            z_quench_thresh=z_quench_thresh,
            m_quench_thresh=m_quench_thresh,
            delta_uv_quench=delta_uv_quench,
        ),
    )

    worker_args = dict(
        catalogo=catalogo,
        pop_base=pop_base,
        t_mu=t_mu,
        z_cut=z_cut,
        metric_dilution=metric_dilution,
        w_rem=w_rem,
        z_ref=z_ref,
        f_max=f_max,
        quench_uv=quench_uv,
        z_quench_thresh=z_quench_thresh,
        m_quench_thresh=m_quench_thresh,
        delta_uv_quench=delta_uv_quench,
    )

    if n_w <= 1 or len(frems) <= 2:
        logger.info("[parallel] Usando modo serial (n_workers=%d)", n_w)
        resultados = []
        for fr in frems:
            logger.info("scan f_rem=%.3f%%", fr * 100)
            resultados.append(_scan_worker(fr=fr, **worker_args))
        return resultados

    resultados: list[dict | None] = [None] * len(frems)

    try:
        with ThreadPoolExecutor(max_workers=n_w) as pool:
            futures = {
                pool.submit(_scan_worker, fr=fr, **worker_args): i
                for i, fr in enumerate(frems)
            }
            for fut in as_completed(futures):
                idx = futures[fut]
                try:
                    resultados[idx] = fut.result()
                    logger.info("[parallel] scan f_rem=%.3f%% ✓", frems[idx] * 100)
                except Exception:
                    logger.exception("[parallel] Error en scan f_rem=%.3f%%", frems[idx] * 100)
                    resultados[idx] = _scan_worker(fr=frems[idx], **worker_args)
    except Exception:
        logger.exception("[parallel] Error general en scan paralelo; usando serial")
        return _scan_serial_fallback(frems=frems, **worker_args)

    return [r for r in resultados if r is not None]


def _scan_serial_fallback(
    frems,
    catalogo,
    pop_base,
    t_mu,
    z_cut,
    metric_dilution,
    w_rem,
    z_ref,
    f_max,
    quench_uv=False,
    z_quench_thresh=cfg.Z_QUENCH_THRESH,
    m_quench_thresh=cfg.M_QUENCH_THRESH,
    delta_uv_quench=cfg.DELTA_UV_QUENCH,
) -> list:
    resultados = []
    for fr in frems:
        resultados.append(
            _scan_worker(
                fr,
                catalogo,
                pop_base,
                t_mu,
                z_cut,
                metric_dilution,
                w_rem,
                z_ref,
                f_max,
                quench_uv,
                z_quench_thresh,
                m_quench_thresh,
                delta_uv_quench,
            )
        )
    return resultados


# ── heatmap paralelo ──────────────────────────────────────────────────────────

def _heatmap_row_worker(
    i: int,
    tp: float,
    frems: np.ndarray,
    n: int,
    z_cut: float,
    quench_uv: bool = False,
    z_quench_thresh: float = cfg.Z_QUENCH_THRESH,
    m_quench_thresh: float = cfg.M_QUENCH_THRESH,
    delta_uv_quench: float = cfg.DELTA_UV_QUENCH,
) -> tuple[int, np.ndarray]:
    """Worker para una fila del heatmap, correspondiente a un valor de t_prev."""
    rng_row = np.random.default_rng(cfg.SEED + 10_000 + i)
    cat_row = inicializar_catalogo(n, rng_row)

    qkwargs = _quench_kwargs(
        quench_uv=quench_uv,
        z_quench_thresh=z_quench_thresh,
        m_quench_thresh=m_quench_thresh,
        delta_uv_quench=delta_uv_quench,
    )

    pop_base_row = construir_poblacion(cat_row, f_rem=0.0, t_mu=tp, **qkwargs)
    p0_row = p_cola(pop_base_row, z_cut)

    fila = np.zeros(len(frems))
    for j, fr in enumerate(frems):
        pop = construir_poblacion(cat_row, f_rem=fr, t_mu=tp, **qkwargs)
        fila[j] = p_cola(pop, z_cut) / (p0_row + 1e-12)

    return i, fila


def heatmap_parallel(
    z_cut: float = cfg.Z_CUT,
    frems: np.ndarray | None = None,
    tprevs: np.ndarray | None = None,
    n: int = cfg.N_HEATMAP,
    max_workers: int | None = None,
    quench_uv: bool = False,
    z_quench_thresh: float = cfg.Z_QUENCH_THRESH,
    m_quench_thresh: float = cfg.M_QUENCH_THRESH,
    delta_uv_quench: float = cfg.DELTA_UV_QUENCH,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Versión paralela de heatmap_grid.

    Retorna (frems, tprevs, ratio_grid) igual que heatmap_grid serial,
    respetando --quench-uv cuando se solicita.
    """
    frems = frems if frems is not None else HEATMAP_FREMS
    tprevs = tprevs if tprevs is not None else HEATMAP_TPREVS
    n_w = _n_workers(max_workers)
    grid = np.zeros((len(tprevs), len(frems)))
    total = len(tprevs)

    logger.info(
        "[parallel] heatmap %d×%d con %d workers | quench_uv=%s",
        total,
        len(frems),
        n_w,
        "ON" if quench_uv else "off",
    )

    worker_kwargs = dict(
        frems=frems,
        n=n,
        z_cut=z_cut,
        quench_uv=quench_uv,
        z_quench_thresh=z_quench_thresh,
        m_quench_thresh=m_quench_thresh,
        delta_uv_quench=delta_uv_quench,
    )

    if n_w <= 1 or total <= 2:
        for i, tp in enumerate(tprevs):
            _, fila = _heatmap_row_worker(i=i, tp=tp, **worker_kwargs)
            grid[i] = fila
            logger.info("[parallel] heatmap fila %d/%d ✓", i + 1, total)
        return frems, tprevs, grid

    try:
        with ThreadPoolExecutor(max_workers=n_w) as pool:
            futures = {
                pool.submit(_heatmap_row_worker, i=i, tp=tp, **worker_kwargs): i
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
                    _, fila = _heatmap_row_worker(i=i, tp=tprevs[i], **worker_kwargs)
                    grid[i] = fila
    except Exception:
        logger.exception("[parallel] Error general en heatmap paralelo; usando serial")
        for i, tp in enumerate(tprevs):
            _, fila = _heatmap_row_worker(i=i, tp=tp, **worker_kwargs)
            grid[i] = fila

    return frems, tprevs, grid
