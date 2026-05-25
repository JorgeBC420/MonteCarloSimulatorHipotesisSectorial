"""
main.py — Punto de entrada principal
Simulador Monte Carlo de Hipótesis Sectorial (SMCHS) v0.5.3
Hipótesis de Transición Sectorial Cosmológica v3.1

Uso:
    python main.py                    # corrida completa
    python main.py --quick            # N reducido, sin heatmap
    python main.py --no-heatmap       # sin heatmap
    python main.py --frem 0.02        # f_rem específico
    python main.py --zcut 10          # umbral de redshift diferente
    python main.py --seed 99          # semilla alternativa reproducible
"""

from __future__ import annotations

import argparse
import logging
import os
from pathlib import Path
import sys
import time
from typing import Callable

import numpy as np
import matplotlib
matplotlib.use("Agg")

sys.path.insert(0, os.path.dirname(__file__))

import config as cfg
from core.poblacion import inicializar_catalogo, construir_poblacion
from analysis.estadistica import resumen_consola, scan_frems, heatmap_grid
from analysis.exportar import (
    exportar_metricas_scan, exportar_muestra_poblacion, exportar_heatmap
)
from figures.graficas import (
    fig1_distribucion_masa, fig2_exceso_por_z, fig3_ks_colas,
    fig4_correlacion_zm, fig5_delta_t, fig6_scan_frems,
    fig7_heatmap, fig8_objetos_jwst,
    fig9_signal_vs_observed, fig10_distribucion_dt_signal, fig11_snr_scan,
)
from figures.observed_overlay import fig_observed_overlay
from baselines.external_loader import load_external_catalog
from baselines.metrics import visible_smchs_df, compare_tail_to_baseline, tail_summary

logger = logging.getLogger("smchs")


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description=(
            f"SMCHS / MCSSH v{cfg.SIMULADOR_VERSION} — "
            f"Hipótesis Sectorial v{cfg.HIPOTESIS_VERSION}"
        )
    )
    p.add_argument("--quick", action="store_true", help="Corrida rápida: N=30k, sin heatmap")
    p.add_argument("--no-heatmap", action="store_true", help="Omitir heatmap 2D")
    p.add_argument("--frem", type=float, default=cfg.F_REM_DEFAULT,
                   help=f"Fracción de remanentes (default: {cfg.F_REM_DEFAULT})")
    p.add_argument("--tprev", type=float, default=cfg.T_PREV_MU,
                   help=f"Madurez heredada promedio en Gyr (default: {cfg.T_PREV_MU})")
    p.add_argument("--zcut", type=float, default=cfg.Z_CUT,
                   help=f"Redshift de corte para análisis (default: {cfg.Z_CUT})")
    p.add_argument("--n", type=int, default=cfg.N,
                   help=f"Número de objetos (default: {cfg.N})")
    p.add_argument("--seed", type=int, default=cfg.SEED,
                   help=f"Semilla global (default: {cfg.SEED})")
    p.add_argument("--out", type=str, default=cfg.OUT_DIR,
                   help="Directorio de salida")
    p.add_argument("--fail-fast", action="store_true",
                   help="Detener ejecución al primer fallo en figura/exportación")
    p.add_argument("--metric-dilution", action="store_true",
                   help="Activar f_rem_eff(z) con dilución métrica opcional")
    p.add_argument("--w-rem", type=float, default=0.0,
                   help="w efectivo para f_rem_eff(z); 0=materia, 1/3=radiación, -1=constante")
    p.add_argument("--z-ref", type=float, default=12.0,
                   help="redshift de referencia para f_rem_eff(z)")
    p.add_argument("--fmax", type=float, default=0.08,
                   help="límite superior de f_rem_eff(z)")
    p.add_argument("--external-baseline", type=str, default=None,
                   help="CSV/FITS externo JADES/TNG/SIMBA para superposición y D_tail")
    return p.parse_args()


def setup_logging(out_dir: str) -> None:
    Path(out_dir).mkdir(parents=True, exist_ok=True)
    Path(cfg.LOG_DIR).mkdir(parents=True, exist_ok=True)
    log_path = Path(out_dir) / "smchs_run.log"
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(log_path, mode="w", encoding="utf-8"),
        ],
        force=True,
    )
    logger.info("Log inicializado: %s", log_path)


def banner(args: argparse.Namespace) -> None:
    logger.info("SMCHS / MCSSH v%s — Hipótesis v%s", cfg.SIMULADOR_VERSION, cfg.HIPOTESIS_VERSION)
    logger.info("N=%s | f_rem=%.4f | tprev=%.3f Gyr | z_cut=%.2f | seed=%s | out=%s",
                f"{args.n:,}", args.frem, args.tprev, args.zcut, args.seed, args.out)
    if args.metric_dilution:
        logger.info("Dilución métrica activa: w_rem=%.3f | z_ref=%.2f | fmax=%.3f", args.w_rem, args.z_ref, args.fmax)


def safe_step(label: str, func: Callable, *args, fail_fast: bool = False, **kwargs):
    """Ejecuta un paso con logging y conserva outputs parciales si algo falla."""
    try:
        logger.info("Ejecutando: %s", label)
        result = func(*args, **kwargs)
        logger.info("OK: %s", label)
        return result
    except Exception:
        logger.exception("FALLÓ: %s", label)
        if fail_fast:
            raise
        return None


def main() -> int:
    args = parse_args()
    if args.quick:
        args.n = min(args.n, 30_000)
        args.no_heatmap = True

    # Actualiza cfg.SEED para semillas estables derivadas dentro de construir_poblacion().
    cfg.SEED = args.seed

    setup_logging(args.out)
    banner(args)
    t0 = time.time()

    try:
        logger.info("[1/6] Inicializando catálogo base")
        rng = np.random.default_rng(args.seed)
        catalogo = inicializar_catalogo(args.n, rng)
        logger.info("z ∈ [%.2f, %.2f] | t_ΛCDM ∈ [%.3f, %.3f] Gyr",
                    float(catalogo["z"].min()), float(catalogo["z"].max()),
                    float(catalogo["t_lcdm"].min()), float(catalogo["t_lcdm"].max()))

        logger.info("[2/6] Construyendo poblaciones pareadas")
        pop_lcdm  = construir_poblacion(catalogo, f_rem=0.0,         t_mu=args.tprev)
        pop_sect  = construir_poblacion(catalogo, f_rem=args.frem,   t_mu=args.tprev, metric_dilution=args.metric_dilution, w_rem=args.w_rem, z_ref=args.z_ref, f_max=args.fmax)
        pop_half  = construir_poblacion(catalogo, f_rem=args.frem/2, t_mu=args.tprev, metric_dilution=args.metric_dilution, w_rem=args.w_rem, z_ref=args.z_ref, f_max=args.fmax)
        pop_doble = construir_poblacion(catalogo, f_rem=args.frem*2, t_mu=args.tprev, metric_dilution=args.metric_dilution, w_rem=args.w_rem, z_ref=args.z_ref, f_max=args.fmax)

        n_vis = int(pop_lcdm["visible"].sum())
        n_alt = int((pop_lcdm["visible"] & (pop_lcdm["z"] > args.zcut)).sum())
        logger.info("Detectables totales=%s | detectables z>%.0f=%s", f"{n_vis:,}", args.zcut, f"{n_alt:,}")

        logger.info("[3/6] Análisis estadístico")
        resumen_consola(pop_lcdm, pop_sect, z_cut=args.zcut)

        logger.info("[4/6] Escaneando sensibilidad en f_rem")
        resultados_scan = scan_frems(catalogo, t_mu=args.tprev, z_cut=args.zcut, metric_dilution=args.metric_dilution, w_rem=args.w_rem, z_ref=args.z_ref, f_max=args.fmax)

        logger.info("[5/6] Generando figuras")
        pops_multi   = [pop_lcdm, pop_half, pop_sect, pop_doble]
        labels_multi = [
            "ΛCDM base",
            f"f={args.frem*50:.2f}%",
            f"f={args.frem*100:.2f}%",
            f"f={args.frem*200:.2f}%",
        ]
        frems_multi = [0.0, args.frem/2, args.frem, args.frem*2]

        figure_steps = [
            ("fig1_distribucion_masa", fig1_distribucion_masa, (pops_multi, labels_multi, frems_multi, args.out)),
            ("fig2_exceso_por_z", fig2_exceso_por_z, (pops_multi, labels_multi, frems_multi, args.out)),
            ("fig3_ks_colas", fig3_ks_colas, (pop_lcdm, pop_sect, args.out)),
            ("fig4_correlacion_zm", fig4_correlacion_zm, (pop_lcdm, pop_sect, args.out)),
            ("fig5_delta_t", fig5_delta_t, (pop_lcdm, pop_sect, args.out)),
            ("fig6_scan_frems", fig6_scan_frems, (resultados_scan, args.out)),
            ("fig8_objetos_jwst", fig8_objetos_jwst, (pop_lcdm, pop_sect, args.out)),
        ]
        for label, func, fargs in figure_steps:
            safe_step(label, func, *fargs, fail_fast=args.fail_fast)

        if not args.no_heatmap:
            hm = safe_step("heatmap_grid", heatmap_grid, z_cut=args.zcut, fail_fast=args.fail_fast)
            if hm is not None:
                frems_hm, tprevs_hm, ratio_grid = hm
                safe_step("fig7_heatmap", fig7_heatmap, frems_hm, tprevs_hm, ratio_grid, args.out, fail_fast=args.fail_fast)
                safe_step("exportar_heatmap", exportar_heatmap, frems_hm, tprevs_hm, ratio_grid, args.out, fail_fast=args.fail_fast)
        else:
            logger.info("Heatmap omitido")

        frems_snr = [0.005, args.frem, args.frem * 2]
        pops_snr = [construir_poblacion(catalogo, f_rem=fr, t_mu=args.tprev, metric_dilution=args.metric_dilution, w_rem=args.w_rem, z_ref=args.z_ref, f_max=args.fmax) for fr in frems_snr]
        safe_step("fig9_signal_vs_observed", fig9_signal_vs_observed, pop_lcdm, pop_sect, args.out, fail_fast=args.fail_fast)
        safe_step("fig10_distribucion_dt_signal", fig10_distribucion_dt_signal, pop_lcdm, pops_snr, frems_snr, args.out, fail_fast=args.fail_fast)
        safe_step("fig11_snr_scan", fig11_snr_scan, resultados_scan, args.out, fail_fast=args.fail_fast)

        if args.external_baseline:
            logger.info("Cargando baseline externo: %s", args.external_baseline)
            try:
                ext_df = load_external_catalog(args.external_baseline)
                safe_step("fig12_observed_overlay", fig_observed_overlay, pop_lcdm, pop_sect, ext_df, args.out, fail_fast=args.fail_fast)
                import pandas as pd
                base_df = visible_smchs_df(pop_lcdm, "SMCHS_LCDM_proxy")
                sect_df = visible_smchs_df(pop_sect, "SMCHS_sectorial")
                rows = []
                rows.append({"model": "external", **tail_summary(ext_df, z_cut=args.zcut, mass_cut=cfg.LOG_M_THRESH)})
                rows.append({"model": "SMCHS_LCDM_proxy", **tail_summary(base_df, z_cut=args.zcut, mass_cut=cfg.LOG_M_THRESH)})
                rows.append({"model": "SMCHS_sectorial", **tail_summary(sect_df, z_cut=args.zcut, mass_cut=cfg.LOG_M_THRESH)})
                rows.append({"model": "D_tail_external_vs_LCDM", **compare_tail_to_baseline(ext_df, base_df, z_cut=args.zcut, mass_cut=cfg.LOG_M_THRESH)})
                rows.append({"model": "D_tail_sectorial_vs_LCDM", **compare_tail_to_baseline(sect_df, base_df, z_cut=args.zcut, mass_cut=cfg.LOG_M_THRESH)})
                pd.DataFrame(rows).to_csv(Path(args.out) / "external_baseline_tail_metrics.csv", index=False)
                logger.info("CSV guardado: external_baseline_tail_metrics.csv")
            except Exception:
                logger.exception("FALLÓ baseline externo")
                if args.fail_fast:
                    raise

        logger.info("[6/6] Exportando CSV")
        safe_step("exportar_metricas_scan", exportar_metricas_scan, resultados_scan, args.out, fail_fast=args.fail_fast)
        safe_step("exportar_muestra_poblacion", exportar_muestra_poblacion, pop_lcdm, pop_sect, args.out, fail_fast=args.fail_fast)

        elapsed = time.time() - t0
        logger.info("Completado en %.1fs | salida=%s", elapsed, Path(args.out).resolve())
        return 0
    except Exception:
        logger.exception("Ejecución abortada")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
