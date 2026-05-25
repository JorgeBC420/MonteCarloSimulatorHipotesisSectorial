"""
analysis/exportar.py — Exportación de resultados a CSV
SMCHS v0.5.2 / Hipótesis Sectorial v3.1

Columnas principales de cola en v0.5.2:
    q95_dt_signal_sect, q99_dt_signal_sect, p_tail_base, p_tail_sect,
    delta_p_tail, snr_tail_q99, delta_q99
Columnas legacy informativas:
    median_dt_signal, median_dt_observed, std_dt_noise, snr_dt, delta_median_signal
"""

import csv
import os
import numpy as np
from config import Z_CUT, LOG_M_THRESH


# Columnas exportadas — orden canónico para reproducibilidad
CAMPOS_SCAN = [
    "f_rem_pct", "t_prev_mu", "z_cut",
    "p_base", "p_sect", "ratio_R", "exceso_pct",
    "ks_D", "ks_p", "ks_sig",
    "kl_div",
    "pearson_base", "pearson_sect",
    "N_visible_z_base", "N_visible_z_sect",
    "N_massive_z_base", "N_massive_z_sect",
    "n_anom", "n_rem_anom", "pct_rem_anom",
    # v0.5.2 — métricas de COLA (estimador correcto para señales raras)
    "q95_dt_signal_sect", "q99_dt_signal_sect",
    "p_tail_base", "p_tail_sect", "delta_p_tail", "tail_ratio", "snr_tail_q99", "delta_q99",
    # legacy (mediana — informativo)
    "median_dt_signal", "median_dt_observed", "std_dt_noise",
    "snr_dt", "delta_median_signal",
]


def exportar_metricas_scan(scan_results: list, out_dir: str) -> None:
    """
    Escribe metricas_por_frem.csv.
    Una fila por valor de f_rem con todas las métricas de metricas_completas().
    """
    path = os.path.join(out_dir, "metricas_por_frem.csv")

    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=CAMPOS_SCAN, extrasaction="ignore")
        w.writeheader()
        for r in scan_results:
            fila = dict(r)
            fila["f_rem_pct"] = round(r["f_rem"] * 100, 4)
            fila["ks_sig"]    = int(r["ks_sig"])
            # Redondear floats
            for k in ["p_base", "p_sect", "ratio_R", "exceso_pct",
                      "ks_D", "ks_p", "kl_div",
                      "pearson_base", "pearson_sect", "pct_rem_anom"]:
                if k in fila and fila[k] is not None:
                    fila[k] = round(float(fila[k]), 6)
            w.writerow({k: fila.get(k, "") for k in CAMPOS_SCAN})

    print(f"  ✓ {os.path.basename(path)}")


def exportar_muestra_poblacion(pop_base: dict, pop_sect: dict,
                               out_dir: str,
                               n_muestra: int = 5000) -> None:
    """
    Escribe poblacion_muestra.csv con muestra aleatoria de ambas poblaciones.

    Columnas v0.5.2: incluye dt_signal, dt_observed, dt_noise, Z_true.
    """
    path   = os.path.join(out_dir, "poblacion_muestra.csv")
    campos = [
        "modelo", "z", "t_lcdm", "t_eff", "delta_t",
        "Z_true", "Z_met", "log_m", "M_UV",
        "t_chem_true", "t_chem_obs",
        "dt_signal", "dt_observed", "dt_noise",
        "visible", "es_rem", "anomalia",
    ]
    rng = np.random.default_rng(42)

    def filas(pop: dict, nombre: str):
        n     = pop["n"]
        idx   = rng.choice(n, min(n_muestra, n), replace=False)
        anom  = pop["visible"] & (pop["z"] > Z_CUT) & (pop["log_m"] > LOG_M_THRESH)
        for i in idx:
            yield {
                "modelo":      nombre,
                "z":           round(float(pop["z"][i]),            4),
                "t_lcdm":      round(float(pop["t_lcdm"][i]),       5),
                "t_eff":       round(float(pop["t_eff"][i]),         5),
                "delta_t":     round(float(pop["delta_t"][i]),       5),
                "Z_true":      round(float(pop["Z_true"][i]),        5),
                "Z_met":       round(float(pop["Z_met"][i]),         5),
                "log_m":       round(float(pop["log_m"][i]),         4),
                "M_UV":        round(float(pop["M_UV"][i]),          4),
                "t_chem_true": round(float(pop["t_chem_true"][i]),   5),
                "t_chem_obs":  round(float(pop["t_chem_obs"][i]),    5),
                "dt_signal":   round(float(pop["dt_signal"][i]),     5),
                "dt_observed": round(float(pop["dt_observed"][i]),   5),
                "dt_noise":    round(float(pop["dt_noise"][i]),      5),
                "visible":     int(pop["visible"][i]),
                "es_rem":      int(pop["es_rem"][i]),
                "anomalia":    int(anom[i]),
            }

    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=campos)
        w.writeheader()
        for row in filas(pop_base, "lcdm"):
            w.writerow(row)
        for row in filas(pop_sect, "sectorial"):
            w.writerow(row)

    print(f"  ✓ {os.path.basename(path)}")


def exportar_heatmap(frems: np.ndarray, tprevs: np.ndarray,
                     ratio_grid: np.ndarray, out_dir: str) -> None:
    """
    Escribe heatmap_ratio.csv con columnas: t_previo_gyr, f_rem_pct, ratio_R.
    """
    path = os.path.join(out_dir, "heatmap_ratio.csv")
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["t_previo_gyr", "f_rem_pct", "ratio_R"])
        for i, tp in enumerate(tprevs):
            for j, fr in enumerate(frems):
                w.writerow([
                    round(float(tp), 3),
                    round(float(fr) * 100, 3),
                    round(float(ratio_grid[i, j]), 4),
                ])
    print(f"  ✓ {os.path.basename(path)}")
