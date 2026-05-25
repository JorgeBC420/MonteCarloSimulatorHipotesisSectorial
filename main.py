"""
main.py — Punto de entrada principal
Simulador Monte Carlo de Hipótesis Sectorial (SMCHS) v0.5.2
Hipótesis de Transición Sectorial Cosmológica v3.1

Uso:
    python main.py                    # corrida completa
    python main.py --quick            # N reducido, sin heatmap
    python main.py --no-heatmap       # sin heatmap
    python main.py --frem 0.02        # f_rem específico
    python main.py --zcut 10          # umbral de redshift diferente
    python main.py --seed 99          # semilla alternativa reproducible
"""

import argparse
import os
import sys
import time
import numpy as np
import matplotlib
matplotlib.use("Agg")

sys.path.insert(0, os.path.dirname(__file__))

import config as cfg
from core.poblacion import inicializar_catalogo, construir_poblacion
from analysis.estadistica import (
    metricas_completas, resumen_consola, scan_frems, heatmap_grid
)
from analysis.exportar import (
    exportar_metricas_scan, exportar_muestra_poblacion, exportar_heatmap
)
from figures.graficas import (
    fig1_distribucion_masa, fig2_exceso_por_z, fig3_ks_colas,
    fig4_correlacion_zm, fig5_delta_t, fig6_scan_frems,
    fig7_heatmap, fig8_objetos_jwst,
    fig9_signal_vs_observed, fig10_distribucion_dt_signal, fig11_snr_scan,
)


def parse_args():
    p = argparse.ArgumentParser(
        description=(
            f"SMCHS / MCSSH v{cfg.SIMULADOR_VERSION} — "
            f"Hipótesis Sectorial v{cfg.HIPOTESIS_VERSION}"
        )
    )
    p.add_argument("--quick",       action="store_true",
                   help="Corrida rápida: N=30k, sin heatmap")
    p.add_argument("--no-heatmap",  action="store_true",
                   help="Omitir heatmap 2D")
    p.add_argument("--frem",        type=float, default=cfg.F_REM_DEFAULT,
                   help=f"Fracción de remanentes (default: {cfg.F_REM_DEFAULT})")
    p.add_argument("--tprev",       type=float, default=cfg.T_PREV_MU,
                   help=f"Madurez heredada promedio en Gyr (default: {cfg.T_PREV_MU})")
    p.add_argument("--zcut",        type=float, default=cfg.Z_CUT,
                   help=f"Redshift de corte para análisis (default: {cfg.Z_CUT})")
    p.add_argument("--n",           type=int,   default=cfg.N,
                   help=f"Número de objetos (default: {cfg.N})")
    p.add_argument("--seed",        type=int,   default=cfg.SEED,
                   help=f"Semilla global (default: {cfg.SEED})")
    p.add_argument("--out",         type=str,   default=cfg.OUT_DIR,
                   help="Directorio de salida")
    return p.parse_args()


def banner(args):
    print()
    print("╔══════════════════════════════════════════════════════════════╗")
    print(f"║  {cfg.SIMULADOR_NOMBRE} / {cfg.SIMULADOR_NOMBRE_EN}  ║")
    print(f"║  Simulador v{cfg.SIMULADOR_VERSION}  |  Hipótesis v{cfg.HIPOTESIS_VERSION}  |  Planck18        ║")
    print("╠══════════════════════════════════════════════════════════════╣")
    print(f"║  N          = {args.n:>10,}                                 ║")
    print(f"║  f_rem      = {args.frem*100:>9.2f} %                                ║")
    print(f"║  t_previo   = {args.tprev:>9.2f} Gyr                              ║")
    print(f"║  z_cut      = {args.zcut:>9.2f}                                  ║")
    print(f"║  seed       = {args.seed:>10}                                 ║")
    print(f"║  salida     = {args.out:<46} ║")
    print("╚══════════════════════════════════════════════════════════════╝")
    print()


def main():
    args = parse_args()
    t0   = time.time()

    # Aplicar semilla CLI
    cfg.SEED = args.seed
    import core.poblacion as _pop
    import core.cosmologia as _cosmo
    _pop._RNG   = np.random.default_rng(args.seed)
    _cosmo._RNG = np.random.default_rng(args.seed)

    if args.quick:
        args.n = min(args.n, 30_000)
        args.no_heatmap = True
        print(f"[modo rápido] N={args.n:,} — heatmap desactivado")

    banner(args)
    os.makedirs(args.out, exist_ok=True)

    # ── [1] Catálogo base ─────────────────────────────────────────────────────
    print(f"[1/6] Inicializando catálogo base (N={args.n:,}, seed={args.seed})...")
    rng      = np.random.default_rng(args.seed)
    catalogo = inicializar_catalogo(args.n, rng)
    print(f"  z    ∈ [{catalogo['z'].min():.2f}, {catalogo['z'].max():.2f}]")
    print(f"  t_ΛCDM ∈ [{catalogo['t_lcdm'].min():.3f}, {catalogo['t_lcdm'].max():.3f}] Gyr")

    # ── [2] Poblaciones pareadas ───────────────────────────────────────────────
    print(f"\n[2/6] Construyendo poblaciones (mismo catálogo, distinto f_rem)...")
    pop_lcdm  = construir_poblacion(catalogo, f_rem=0.0,          t_mu=args.tprev)
    pop_sect  = construir_poblacion(catalogo, f_rem=args.frem,    t_mu=args.tprev)
    pop_half  = construir_poblacion(catalogo, f_rem=args.frem/2,  t_mu=args.tprev)
    pop_doble = construir_poblacion(catalogo, f_rem=args.frem*2,  t_mu=args.tprev)

    n_vis = pop_lcdm["visible"].sum()
    n_alt = (pop_lcdm["visible"] & (pop_lcdm["z"] > args.zcut)).sum()
    print(f"  Detectables totales: {n_vis:,}  |  z > {args.zcut:.0f}: {n_alt:,}")

    # ── [3] Análisis estadístico ──────────────────────────────────────────────
    print(f"\n[3/6] Análisis estadístico...")
    resumen_consola(pop_lcdm, pop_sect, z_cut=args.zcut)

    # ── [4] Scan f_rem ─────────────────────────────────────────────────────────
    print(f"\n[4/6] Escaneando sensibilidad en f_rem...")
    resultados_scan = scan_frems(catalogo, t_mu=args.tprev, z_cut=args.zcut)

    # ── [5] Figuras ───────────────────────────────────────────────────────────
    print(f"\n[5/6] Generando figuras → {args.out}/")

    pops_multi   = [pop_lcdm, pop_half, pop_sect, pop_doble]
    labels_multi = [
        "ΛCDM base",
        f"f={args.frem*50:.2f}%",
        f"f={args.frem*100:.2f}%",
        f"f={args.frem*200:.2f}%",
    ]
    frems_multi = [0.0, args.frem/2, args.frem, args.frem*2]

    # Figuras v0.4 (existentes)
    fig1_distribucion_masa(pops_multi, labels_multi, frems_multi, args.out)
    fig2_exceso_por_z(pops_multi, labels_multi, frems_multi, args.out)
    fig3_ks_colas(pop_lcdm, pop_sect, args.out)
    fig4_correlacion_zm(pop_lcdm, pop_sect, args.out)
    fig5_delta_t(pop_lcdm, pop_sect, args.out)
    fig6_scan_frems(resultados_scan, args.out)
    fig8_objetos_jwst(pop_lcdm, pop_sect, args.out)

    if not args.no_heatmap:
        print("  Generando heatmap 2D (~60s)...")
        frems_hm, tprevs_hm, ratio_grid = heatmap_grid(z_cut=args.zcut)
        fig7_heatmap(frems_hm, tprevs_hm, ratio_grid, args.out)
        exportar_heatmap(frems_hm, tprevs_hm, ratio_grid, args.out)
    else:
        print("  [heatmap omitido]")

    # Figuras v0.5.2 — señal/ruido
    frems_snr = [0.005, args.frem, args.frem * 2]
    pops_snr  = [
        construir_poblacion(catalogo, f_rem=fr, t_mu=args.tprev)
        for fr in frems_snr
    ]
    fig9_signal_vs_observed(pop_lcdm, pop_sect, args.out)
    fig10_distribucion_dt_signal(pop_lcdm, pops_snr, frems_snr, args.out)
    fig11_snr_scan(resultados_scan, args.out)

    # ── [6] CSV ───────────────────────────────────────────────────────────────
    print(f"\n[6/6] Exportando CSV → {args.out}/")
    exportar_metricas_scan(resultados_scan, args.out)
    exportar_muestra_poblacion(pop_lcdm, pop_sect, args.out)

    elapsed = time.time() - t0
    print(f"\n{'═'*60}")
    print(f"  SMCHS v{cfg.SIMULADOR_VERSION} — Hipótesis Sectorial v{cfg.HIPOTESIS_VERSION}")
    print(f"  ✓ Completado en {elapsed:.1f}s  |  seed={args.seed}")
    print(f"  Salida: {os.path.abspath(args.out)}/")
    print(f"{'═'*60}\n")


if __name__ == "__main__":
    main()
