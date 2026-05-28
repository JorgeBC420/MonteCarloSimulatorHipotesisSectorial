"""
main.py — Punto de entrada principal
Simulador Monte Carlo de Hipótesis Sectorial (SMCHS) v0.5.7-hotfix1
Hipótesis de Transición Sectorial Cosmológica v3.2.1

Uso:
    python main.py
    python main.py --quick
    python main.py --no-heatmap
    python main.py --frem 0.02
    python main.py --zcut 10
    python main.py --seed 99
    python main.py --remnant-mode metric
    python main.py --remnant-mode geometric
    python main.py --quench-uv
    python main.py --no-archive

Hotfix v0.5.7-hotfix1:
- Aplica --quench-uv también a la población base ΛCDM cuando el flag está activo.
- Propaga quench_uv y sus parámetros a scan_frems_parallel().
- Propaga quench_uv y sus parámetros a heatmap_parallel().
- Mantiene la comparación pareada: mismo catálogo, misma semilla, mismo filtro observacional.
"""

from __future__ import annotations

import argparse
import logging
import os
from pathlib import Path
import sys
import time
from typing import Callable

import matplotlib
matplotlib.use("Agg")
import numpy as np

sys.path.insert(0, os.path.dirname(__file__))

import config as cfg
from analysis.estadistica import resumen_consola
from analysis.exportar import (
    exportar_heatmap,
    exportar_metricas_scan,
    exportar_muestra_poblacion,
)
from baselines.external_loader import load_external_catalog
from baselines.metrics import compare_tail_to_baseline, tail_summary, visible_smchs_df
from core.geometric_remnants import construir_poblacion_geometric
from core.parallel import heatmap_parallel, scan_frems_parallel
from core.poblacion import construir_poblacion, inicializar_catalogo
from core.run_archive import archivar_corrida
from figures.graficas import (
    fig1_distribucion_masa,
    fig2_exceso_por_z,
    fig3_ks_colas,
    fig4_correlacion_zm,
    fig5_delta_t,
    fig6_scan_frems,
    fig7_heatmap,
    fig8_objetos_jwst,
    fig9_signal_vs_observed,
    fig10_distribucion_dt_signal,
    fig11_snr_scan,
)
from figures.observed_overlay import fig_observed_overlay

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
    p.add_argument("--frem", type=float, default=cfg.F_REM_DEFAULT, help=f"Fracción de remanentes (default: {cfg.F_REM_DEFAULT})")
    p.add_argument("--tprev", type=float, default=cfg.T_PREV_MU, help=f"Madurez heredada promedio en Gyr (default: {cfg.T_PREV_MU})")
    p.add_argument("--zcut", type=float, default=cfg.Z_CUT, help=f"Redshift de corte para análisis (default: {cfg.Z_CUT})")
    p.add_argument("--n", type=int, default=cfg.N, help=f"Número de objetos (default: {cfg.N})")
    p.add_argument("--seed", type=int, default=cfg.SEED, help=f"Semilla global (default: {cfg.SEED})")
    p.add_argument("--out", type=str, default=cfg.OUT_DIR, help="Directorio de salida")
    p.add_argument("--fail-fast", action="store_true", help="Detener ejecución al primer fallo en figura/exportación")

    p.add_argument("--metric-dilution", action="store_true", help="Activar f_rem_eff(z) con dilución métrica opcional")
    p.add_argument("--w-rem", type=float, default=0.0, help="w efectivo para f_rem_eff(z); 0=materia, 1/3=radiación, -1=constante")
    p.add_argument("--z-ref", type=float, default=12.0, help="redshift de referencia para f_rem_eff(z)")
    p.add_argument("--fmax", type=float, default=0.08, help="límite superior de f_rem_eff(z)")
    p.add_argument("--external-baseline", type=str, default=None, help="CSV/FITS externo JADES/TNG/SIMBA para superposición y D_tail")

    p.add_argument(
        "--remnant-mode",
        type=str,
        default="flat",
        choices=["flat", "metric", "geometric"],
        help=(
            "Modo de remanencia: "
            "flat=f_rem fijo (base, default), "
            "metric=dilución por expansión, "
            "geometric=fluctuación latente (experimental)"
        ),
    )
    p.add_argument("--no-archive", action="store_true", help="No guardar ZIP de outputs en logs/ al terminar")
    p.add_argument("--workers", type=int, default=None, help="Máximo de threads para scan/heatmap (None=automático)")
    p.add_argument("--geo-psi-c", type=float, default=0.5, help="Umbral sigmoide modo geometric (default: 0.5)")
    p.add_argument("--geo-s-psi", type=float, default=0.3, help="Suavidad sigmoide modo geometric (default: 0.3)")

    # ── Quenching UV (v0.5.7) ──────────────────────────────────────────────
    p.add_argument(
        "--quench-uv",
        action="store_true",
        help=(
            "Activar supresión UV por quenching. Galaxias con "
            "Z_obs > Z_QUENCH_THRESH y log_m > M_QUENCH_THRESH "
            "reciben M_UV más débil → menos detectables. "
            "Filtro conservador: puede reducir la señal sectorial. "
            "Desactivado por defecto para retrocompatibilidad."
        ),
    )
    p.add_argument("--z-quench-thresh", type=float, default=cfg.Z_QUENCH_THRESH, help=f"Umbral metalicidad para quenching UV (default: {cfg.Z_QUENCH_THRESH})")
    p.add_argument("--m-quench-thresh", type=float, default=cfg.M_QUENCH_THRESH, help=f"Umbral masa log10 para quenching UV (default: {cfg.M_QUENCH_THRESH})")
    p.add_argument("--delta-uv-quench", type=float, default=cfg.DELTA_UV_QUENCH, help=f"Desplazamiento UV máximo en mag (default: {cfg.DELTA_UV_QUENCH})")

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
    logger.info(
        "N=%s | f_rem=%.4f | tprev=%.3f Gyr | z_cut=%.2f | seed=%s | out=%s",
        f"{args.n:,}",
        args.frem,
        args.tprev,
        args.zcut,
        args.seed,
        args.out,
    )
    logger.info(
        "remnant-mode=%s | workers=%s | archive=%s | quench-uv=%s",
        args.remnant_mode,
        args.workers or "auto",
        "no" if args.no_archive else "sí",
        "ON" if args.quench_uv else "off",
    )
    if args.remnant_mode == "metric" or args.metric_dilution:
        logger.info("Dilución métrica: w_rem=%.3f | z_ref=%.2f | fmax=%.3f", args.w_rem, args.z_ref, args.fmax)
    if args.remnant_mode == "geometric":
        logger.info("Modo geométrico: psi_c=%.2f | s_psi=%.2f", args.geo_psi_c, args.geo_s_psi)
    if args.quench_uv:
        logger.info(
            "Quench UV: Z_thresh=%.2f | M_thresh=%.1f | ΔM_UV_max=%.1f mag",
            args.z_quench_thresh,
            args.m_quench_thresh,
            args.delta_uv_quench,
        )


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


def _quench_kwargs(args: argparse.Namespace) -> dict:
    """Parámetros de quenching comunes a base, sectorial, scan y heatmap."""
    return {
        "quench_uv": args.quench_uv,
        "z_quench_thresh": args.z_quench_thresh,
        "m_quench_thresh": args.m_quench_thresh,
        "delta_uv_quench": args.delta_uv_quench,
    }


def _construir_base(catalogo, args):
    """
    Construye ΛCDM base con los mismos filtros observacionales activos.

    Esto evita comparar ΛCDM sin filtro contra Sectorial con filtro cuando
    se usa --quench-uv.
    """
    return construir_poblacion(
        catalogo,
        f_rem=0.0,
        t_mu=args.tprev,
        **_quench_kwargs(args),
    )


def _construir_sect(catalogo, args, f_rem_override=None):
    """
    Construye una población según --remnant-mode y --quench-uv.

    f_rem_override permite construir con fracciones alternativas (½×, 2×).
    """
    fr = f_rem_override if f_rem_override is not None else args.frem
    mode = args.remnant_mode

    if args.metric_dilution and mode == "flat":
        mode = "metric"

    quench_kwargs = _quench_kwargs(args)

    if mode == "geometric":
        return construir_poblacion_geometric(
            catalogo,
            f0=fr,
            t_mu=args.tprev,
            psi_c=args.geo_psi_c,
            s_psi=args.geo_s_psi,
            z_ref=args.z_ref,
            w_rem=args.w_rem,
            f_max=args.fmax,
            **quench_kwargs,
        )
    if mode == "metric":
        return construir_poblacion(
            catalogo,
            f_rem=fr,
            t_mu=args.tprev,
            metric_dilution=True,
            w_rem=args.w_rem,
            z_ref=args.z_ref,
            f_max=args.fmax,
            **quench_kwargs,
        )

    # flat
    return construir_poblacion(
        catalogo,
        f_rem=fr,
        t_mu=args.tprev,
        **quench_kwargs,
    )


def main() -> int:
    args = parse_args()

    if args.quick:
        args.n = min(args.n, 30_000)
        args.no_heatmap = True

    # Retrocompatibilidad: --metric-dilution sin --remnant-mode.
    if args.metric_dilution and args.remnant_mode == "flat":
        args.remnant_mode = "metric"

    cfg.SEED = args.seed
    setup_logging(args.out)
    banner(args)

    t0 = time.time()

    try:
        logger.info("[1/6] Inicializando catálogo base")
        rng = np.random.default_rng(args.seed)
        catalogo = inicializar_catalogo(args.n, rng)
        logger.info(
            "z ∈ [%.2f, %.2f] | t_ΛCDM ∈ [%.3f, %.3f] Gyr",
            float(catalogo["z"].min()),
            float(catalogo["z"].max()),
            float(catalogo["t_lcdm"].min()),
            float(catalogo["t_lcdm"].max()),
        )

        logger.info("[2/6] Construyendo poblaciones pareadas (mode=%s)", args.remnant_mode)
        pop_lcdm = _construir_base(catalogo, args)
        pop_sect = _construir_sect(catalogo, args)
        pop_half = _construir_sect(catalogo, args, f_rem_override=args.frem / 2)
        pop_doble = _construir_sect(catalogo, args, f_rem_override=args.frem * 2)

        n_vis = int(pop_lcdm["visible"].sum())
        n_alt = int((pop_lcdm["visible"] & (pop_lcdm["z"] > args.zcut)).sum())
        logger.info("Detectables totales=%s | detectables z>%.0f=%s", f"{n_vis:,}", args.zcut, f"{n_alt:,}")

        logger.info("[3/6] Análisis estadístico")
        resumen_consola(pop_lcdm, pop_sect, z_cut=args.zcut)

        logger.info("[4/6] Escaneando sensibilidad en f_rem (paralelo)")
        use_metric = args.remnant_mode == "metric" or args.metric_dilution
        resultados_scan = scan_frems_parallel(
            catalogo,
            t_mu=args.tprev,
            z_cut=args.zcut,
            metric_dilution=use_metric,
            w_rem=args.w_rem,
            z_ref=args.z_ref,
            f_max=args.fmax,
            max_workers=args.workers,
            **_quench_kwargs(args),
        )

        logger.info("[5/6] Generando figuras")
        pops_multi = [pop_lcdm, pop_half, pop_sect, pop_doble]
        labels_multi = [
            "ΛCDM base",
            f"f={args.frem * 50:.2f}%",
            f"f={args.frem * 100:.2f}%",
            f"f={args.frem * 200:.2f}%",
        ]
        frems_multi = [0.0, args.frem / 2, args.frem, args.frem * 2]

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
            hm = safe_step(
                "heatmap_parallel",
                heatmap_parallel,
                z_cut=args.zcut,
                max_workers=args.workers,
                fail_fast=args.fail_fast,
                **_quench_kwargs(args),
            )
            if hm is not None:
                frems_hm, tprevs_hm, ratio_grid = hm
                safe_step("fig7_heatmap", fig7_heatmap, frems_hm, tprevs_hm, ratio_grid, args.out, fail_fast=args.fail_fast)
                safe_step("exportar_heatmap", exportar_heatmap, frems_hm, tprevs_hm, ratio_grid, args.out, fail_fast=args.fail_fast)
        else:
            logger.info("Heatmap omitido")

        frems_snr = [0.005, args.frem, args.frem * 2]
        pops_snr = [_construir_sect(catalogo, args, f_rem_override=fr) for fr in frems_snr]
        safe_step("fig9_signal_vs_observed", fig9_signal_vs_observed, pop_lcdm, pop_sect, args.out, fail_fast=args.fail_fast)
        safe_step("fig10_distribucion_dt_signal", fig10_distribucion_dt_signal, pop_lcdm, pops_snr, frems_snr, args.out, fail_fast=args.fail_fast)
        safe_step("fig11_snr_scan", fig11_snr_scan, resultados_scan, args.out, fail_fast=args.fail_fast)

        if args.external_baseline:
            logger.info("Cargando baseline externo: %s", args.external_baseline)
            try:
                import pandas as pd

                ext_df = load_external_catalog(args.external_baseline)
                safe_step("fig12_observed_overlay", fig_observed_overlay, pop_lcdm, pop_sect, ext_df, args.out, fail_fast=args.fail_fast)

                base_df = visible_smchs_df(pop_lcdm, "SMCHS_LCDM_proxy")
                sect_df = visible_smchs_df(pop_sect, "SMCHS_sectorial")
                rows = [
                    {"model": "external", **tail_summary(ext_df, z_cut=args.zcut, mass_cut=cfg.LOG_M_THRESH)},
                    {"model": "SMCHS_LCDM_proxy", **tail_summary(base_df, z_cut=args.zcut, mass_cut=cfg.LOG_M_THRESH)},
                    {"model": "SMCHS_sectorial", **tail_summary(sect_df, z_cut=args.zcut, mass_cut=cfg.LOG_M_THRESH)},
                    {"model": "D_tail_external_vs_LCDM", **compare_tail_to_baseline(ext_df, base_df, z_cut=args.zcut, mass_cut=cfg.LOG_M_THRESH)},
                    {"model": "D_tail_sectorial_vs_LCDM", **compare_tail_to_baseline(sect_df, base_df, z_cut=args.zcut, mass_cut=cfg.LOG_M_THRESH)},
                ]
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

        if not args.no_archive:
            args_dict = vars(args)
            zip_path = archivar_corrida(
                out_dir=args.out,
                log_dir=cfg.LOG_DIR,
                args_dict={k: v for k, v in args_dict.items() if not callable(v)},
                elapsed=elapsed,
            )
            if zip_path:
                logger.info("Corrida archivada: %s", zip_path.name)

        return 0

    except Exception:
        logger.exception("Ejecución abortada")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
