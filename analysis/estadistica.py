"""
analysis/estadistica.py — Fase E: análisis estadístico
SMCHS v0.5.3 / Hipótesis Sectorial v3.1

CHANGELOG v0.5.3:
    Nuevas métricas de señal/ruido en metricas_completas():
        median_dt_signal    mediana de dt_signal a z > z_cut
        median_dt_observed  mediana de dt_observed a z > z_cut
        std_dt_noise        dispersión del ruido eps_Z propagado a Δt
        snr_dt              SNR = (μ_sect − μ_base) / σ_pooled sobre dt_signal
    Estas columnas también aparecen en el CSV de salida.

v0.4.0: heatmap con control ΛCDM por fila; scan con catálogo pareado.
v0.3.0: Δt_i correcto.

Funciones exportadas:
    p_cola, n_visible_z, n_masivas_z
    ks_test, kl_divergencia, correlacion_zm
    metricas_dt_signal      ← nueva v0.5.3
    metricas_completas
    scan_frems, heatmap_grid
    resumen_consola
"""

import logging
import numpy as np
from scipy import stats
from scipy.special import rel_entr
import config as cfg
from config import (
    Z_CUT, LOG_M_THRESH, DT_TAIL_TAU, KL_N_BINS,
    FREMS_SCAN, HEATMAP_FREMS, HEATMAP_TPREVS, N_HEATMAP,
    T_PREV_MU,
)
from core.poblacion import inicializar_catalogo, construir_poblacion

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# Utilidades
# ─────────────────────────────────────────────────────────────────────────────

def _mask_alto(pop: dict, z_cut: float = Z_CUT) -> np.ndarray:
    return pop["visible"] & (pop["z"] > z_cut)


# ─────────────────────────────────────────────────────────────────────────────
# Métricas individuales
# ─────────────────────────────────────────────────────────────────────────────

def p_cola(pop: dict, z_cut: float = Z_CUT,
           log_m_thresh: float = LOG_M_THRESH) -> float:
    """P(log M★ > umbral | z > z_cut, visible)."""
    m = _mask_alto(pop, z_cut)
    return float((pop["log_m"][m] > log_m_thresh).mean()) if m.sum() > 0 else 0.0


def n_visible_z(pop: dict, z_cut: float = Z_CUT) -> int:
    return int(_mask_alto(pop, z_cut).sum())


def n_masivas_z(pop: dict, z_cut: float = Z_CUT,
                log_m_thresh: float = LOG_M_THRESH) -> int:
    m = _mask_alto(pop, z_cut)
    return int((pop["log_m"][m] > log_m_thresh).sum())


def ks_test(pop_a: dict, pop_b: dict, z_cut: float = Z_CUT) -> tuple:
    xa = pop_a["log_m"][_mask_alto(pop_a, z_cut)]
    xb = pop_b["log_m"][_mask_alto(pop_b, z_cut)]
    return stats.ks_2samp(xa, xb) if (len(xa) >= 5 and len(xb) >= 5) else (0.0, 1.0)


def kl_divergencia(pop_a: dict, pop_b: dict,
                   z_cut: float = Z_CUT, n_bins: int = KL_N_BINS) -> float:
    xa = pop_a["log_m"][_mask_alto(pop_a, z_cut)]
    xb = pop_b["log_m"][_mask_alto(pop_b, z_cut)]
    if len(xa) < 5 or len(xb) < 5:
        return 0.0
    bins = np.linspace(8.0, 13.5, n_bins + 1)
    ha, _ = np.histogram(xa, bins=bins, density=True)
    hb, _ = np.histogram(xb, bins=bins, density=True)
    eps = 1e-10
    ha = ha + eps; hb = hb + eps
    ha /= ha.sum(); hb /= hb.sum()
    return float(rel_entr(hb, ha).sum())


def correlacion_zm(pop: dict, z_cut: float = Z_CUT) -> tuple:
    m = _mask_alto(pop, z_cut)
    zm, mm = pop["Z_met"][m], pop["log_m"][m]
    return stats.pearsonr(mm, zm) if len(zm) >= 10 else (0.0, 1.0)


# ─────────────────────────────────────────────────────────────────────────────
# Métricas de señal/ruido — reescritas en v0.5.3
# ─────────────────────────────────────────────────────────────────────────────

# Nota de diseño: dt_signal = t_chem_true − t_ΛCDM = t_eff − t_ΛCDM = Δt_heredada.
# Esto no es circularidad; es un test experimental deliberado: medir cuánta
# de la madurez inyectada sobrevive en la cola observable tras el ruido eps_Z.
# Ver README para la distinción dt_signal / dt_observed / dt_noise.

_TAU_DEFAULT = DT_TAIL_TAU   # Gyr — umbral de "madurez significativa" para P(Δt > τ)


def metricas_cola_dt(pop_base: dict, pop_sect: dict,
                     z_cut: float = Z_CUT,
                     tau: float = _TAU_DEFAULT) -> dict:
    """
    Métricas de COLA de dt_signal — el estimador correcto para señales raras.

    Con f_rem pequeño (1–5%), el 95–99% de los objetos tienen dt_signal = 0
    (no son remanentes), por lo que la mediana es siempre cero y el SNR
    basado en medianas no detecta nada. Las métricas de cola capturan
    exactamente la señal donde la hipótesis predice que aparece.

    Métricas calculadas (a z > z_cut, visible):
        q95_dt_signal_{base,sect}   percentil 95 de dt_signal
        q99_dt_signal_{base,sect}   percentil 99 de dt_signal (cola extrema)
        p_tail_{base,sect}          P(dt_signal > τ)  con τ = tau Gyr
        delta_p_tail                p_tail_sect − p_tail_base (métrica estable)
        tail_ratio                  p_tail_sect / p_tail_base (auxiliar; inestable si base≈0)
        snr_tail_q99                (Q99_sect − Q99_base) / σ(dt_noise_sect)

    Interpretación:
        delta_p_tail > 0 → la hipótesis engrosa la cola positiva
        snr_tail_q99 > 1 → el engrosamiento supera el nivel del ruido
        snr_tail_q99 > 2 → señal robusta
    """
    mb = _mask_alto(pop_base, z_cut)
    ms = _mask_alto(pop_sect, z_cut)

    sig_b  = pop_base["dt_signal"][mb]
    sig_s  = pop_sect["dt_signal"][ms]
    noi_s  = pop_sect["dt_noise"][ms]
    noi_b  = pop_base["dt_noise"][mb]

    def _pct(arr, p):
        return float(np.percentile(arr, p)) if len(arr) > 0 else 0.0

    q95_b = _pct(sig_b, 95);  q95_s = _pct(sig_s, 95)
    q99_b = _pct(sig_b, 99);  q99_s = _pct(sig_s, 99)

    p_tail_b = float(np.mean(sig_b > tau)) if len(sig_b) > 0 else 0.0
    p_tail_s = float(np.mean(sig_s > tau)) if len(sig_s) > 0 else 0.0

    sigma_noise = float(np.std(noi_s)) if len(noi_s) > 1 else 1.0
    sigma_noise_b = float(np.std(noi_b)) if len(noi_b) > 1 else 1.0
    sigma_pooled  = float(np.sqrt(0.5 * (sigma_noise**2 + sigma_noise_b**2)))

    snr_tail = (q99_s - q99_b) / (sigma_pooled + 1e-12)

    return {
        "tau_gyr":               tau,
        "q95_dt_signal_base":    q95_b,
        "q95_dt_signal_sect":    q95_s,
        "q99_dt_signal_base":    q99_b,
        "q99_dt_signal_sect":    q99_s,
        "delta_q95":             q95_s - q95_b,
        "delta_q99":             q99_s - q99_b,
        "p_tail_base":           p_tail_b,
        "p_tail_sect":           p_tail_s,
        "delta_p_tail":          p_tail_s - p_tail_b,
        # Auxiliar: puede explotar si p_tail_base≈0; no usar como métrica principal.
        "tail_ratio":            p_tail_s / (p_tail_b + 1e-12),
        "snr_tail_q99":          snr_tail,
        "sigma_noise_sect":      sigma_noise,
        "sigma_pooled":          sigma_pooled,
    }


def metricas_dt_signal(pop_base: dict, pop_sect: dict,
                       z_cut: float = Z_CUT) -> dict:
    """
    Alias de compatibilidad → delega a metricas_cola_dt.
    Retorna también campos legacy (median, std_pooled, snr_dt) para el CSV.
    """
    cola = metricas_cola_dt(pop_base, pop_sect, z_cut)

    mb = _mask_alto(pop_base, z_cut)
    ms = _mask_alto(pop_sect, z_cut)
    sig_b = pop_base["dt_signal"][mb]
    sig_s = pop_sect["dt_signal"][ms]
    noi_b = pop_base["dt_noise"][mb]
    noi_s = pop_sect["dt_noise"][ms]

    med_b = float(np.median(sig_b)) if len(sig_b) > 0 else 0.0
    med_s = float(np.median(sig_s)) if len(sig_s) > 0 else 0.0
    std_nb = float(np.std(noi_b))   if len(noi_b) > 1 else 1.0
    std_ns = float(np.std(noi_s))   if len(noi_s) > 1 else 1.0
    std_pooled = float(np.sqrt(0.5 * (std_nb**2 + std_ns**2)))

    return {
        # campos legacy
        "median_dt_signal_base": med_b,
        "median_dt_signal_sect": med_s,
        "std_dt_noise_base":     std_nb,
        "std_dt_noise_sect":     std_ns,
        "std_pooled":            std_pooled,
        "snr_dt":                (med_s - med_b) / (std_pooled + 1e-12),
        "delta_median_signal":   med_s - med_b,
        # campos de cola (principales v0.5.3)
        **cola,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Métricas completas
# ─────────────────────────────────────────────────────────────────────────────

def metricas_completas(pop_base: dict, pop_sect: dict,
                       z_cut: float = Z_CUT) -> dict:
    p_b        = p_cola(pop_base, z_cut)
    p_s        = p_cola(pop_sect, z_cut)
    ks_d, ks_p = ks_test(pop_base, pop_sect, z_cut)
    kl         = kl_divergencia(pop_base, pop_sect, z_cut)
    r_b, _     = correlacion_zm(pop_base, z_cut)
    r_s, _     = correlacion_zm(pop_sect, z_cut)

    m_s       = _mask_alto(pop_sect, z_cut)
    anom_mask = m_s & (pop_sect["log_m"] > LOG_M_THRESH)
    n_anom    = int(anom_mask.sum())
    n_rem_a   = int(pop_sect["es_rem"][anom_mask].sum()) if n_anom > 0 else 0

    # Métricas de señal/ruido (v0.5.3)
    snr_m = metricas_dt_signal(pop_base, pop_sect, z_cut)

    # Medianas de dt_observed para el CSV
    mb_obs = _mask_alto(pop_base, z_cut)
    ms_obs = _mask_alto(pop_sect, z_cut)
    med_obs_b = float(np.median(pop_base["dt_observed"][mb_obs])) if mb_obs.sum() > 0 else 0.0
    med_obs_s = float(np.median(pop_sect["dt_observed"][ms_obs])) if ms_obs.sum() > 0 else 0.0

    return {
        # identificación
        "f_rem":                  pop_sect["f_rem"],
        "t_prev_mu":              pop_sect.get("t_mu", T_PREV_MU),
        "z_cut":                  z_cut,
        # probabilidad de anomalía
        "p_base":                 p_b,
        "p_sect":                 p_s,
        "ratio_R":                p_s / (p_b + 1e-12),
        "exceso_pct":             (p_s / (p_b + 1e-12) - 1) * 100,
        # pruebas estadísticas
        "ks_D":                   ks_d,
        "ks_p":                   ks_p,
        "ks_sig":                 bool(ks_p < 0.05),
        "kl_div":                 kl,
        # correlación Z–M★
        "pearson_base":           r_b,
        "pearson_sect":           r_s,
        # conteos
        "N_visible_z_base":       n_visible_z(pop_base, z_cut),
        "N_visible_z_sect":       n_visible_z(pop_sect, z_cut),
        "N_massive_z_base":       n_masivas_z(pop_base, z_cut),
        "N_massive_z_sect":       n_masivas_z(pop_sect, z_cut),
        "n_anom":                 n_anom,
        "n_rem_anom":             n_rem_a,
        "pct_rem_anom":           n_rem_a / (n_anom + 1e-9) * 100,
        # señal / ruido v0.5.3 — métricas de COLA (estimador correcto)
        "q95_dt_signal_sect":     snr_m["q95_dt_signal_sect"],
        "q99_dt_signal_sect":     snr_m["q99_dt_signal_sect"],
        "p_tail_base":            snr_m["p_tail_base"],
        "p_tail_sect":            snr_m["p_tail_sect"],
        "delta_p_tail":           snr_m["delta_p_tail"],
        "tail_ratio":             snr_m["tail_ratio"],  # auxiliar; no métrica central
        "snr_tail_q99":           snr_m["snr_tail_q99"],
        "delta_q99":              snr_m["delta_q99"],
        # campos legacy (mediana — informativo pero no central)
        "median_dt_signal":       snr_m["median_dt_signal_sect"],
        "median_dt_observed":     med_obs_s,
        "std_dt_noise":           snr_m["std_dt_noise_sect"],
        "snr_dt":                 snr_m["snr_dt"],
        "delta_median_signal":    snr_m["delta_median_signal"],
    }


# ─────────────────────────────────────────────────────────────────────────────
# Sensibilidad — scan con catálogo pareado
# ─────────────────────────────────────────────────────────────────────────────

def scan_frems(catalogo: dict,
               frems: list = None,
               t_mu: float = None,
               z_cut: float = Z_CUT) -> list:
    """
    Escanea métricas para múltiples f_rem sobre el MISMO catálogo base.

    La población ΛCDM (f_rem=0) se construye una sola vez sobre ese catálogo
    y actúa como control para todos los f_rem del scan.
    """
    frems = frems if frems is not None else FREMS_SCAN
    t_mu  = t_mu  if t_mu  is not None else T_PREV_MU

    pop_base   = construir_poblacion(catalogo, f_rem=0.0, t_mu=t_mu)
    resultados = []

    for fr in frems:
        logger.info("scan f_rem=%.2f%%", fr * 100)
        pop = construir_poblacion(catalogo, f_rem=fr, t_mu=t_mu)
        resultados.append(metricas_completas(pop_base, pop, z_cut))

    return resultados


def heatmap_grid(z_cut: float = Z_CUT,
                 frems: np.ndarray = None,
                 tprevs: np.ndarray = None,
                 n: int = N_HEATMAP) -> tuple:
    """
    Grilla 2D ratio R(f_rem, t_previo).

    Cada fila (t_previo) genera su propio catálogo base y su propia
    referencia ΛCDM. El ratio se calcula dentro de esa fila, eliminando
    la variación entre catálogos de filas distintas.

    Retorna (frems, tprevs, ratio_grid)  donde ratio_grid[i,j] = R(fr_j, tp_i).
    """
    frems  = frems  if frems  is not None else HEATMAP_FREMS
    tprevs = tprevs if tprevs is not None else HEATMAP_TPREVS

    grid  = np.zeros((len(tprevs), len(frems)))
    total = len(tprevs) * len(frems)
    cnt   = 0

    for i, tp in enumerate(tprevs):
        # Catálogo fresco por fila; control ΛCDM construido sobre el mismo
        rng_row      = np.random.default_rng(cfg.SEED + 10_000 + i)
        cat_row      = inicializar_catalogo(n, rng_row)
        pop_base_row = construir_poblacion(cat_row, f_rem=0.0, t_mu=tp)
        p0_row       = p_cola(pop_base_row, z_cut)

        for j, fr in enumerate(frems):
            pop         = construir_poblacion(cat_row, f_rem=fr, t_mu=tp)
            grid[i, j]  = p_cola(pop, z_cut) / (p0_row + 1e-12)
            cnt += 1
            logger.info("heatmap %s/%s", cnt, total)

    return frems, tprevs, grid          # ya es ratio (dividido por p0_row)


# ─────────────────────────────────────────────────────────────────────────────
# Resumen de consola
# ─────────────────────────────────────────────────────────────────────────────

def resumen_consola(pop_base: dict, pop_sect: dict,
                    z_cut: float = Z_CUT) -> None:
    """Imprime resumen en consola mediante logging estructurado."""
    m = metricas_completas(pop_base, pop_sect, z_cut)
    sep = "─" * 58
    snr_t = m["snr_tail_q99"]
    label = "★ robusto" if snr_t > 2 else ("marginal" if snr_t > 1 else "< σ_ruido")
    lines = [
        sep,
        f"Análisis | f_rem={m['f_rem']*100:.2f}% | t_mu={m['t_prev_mu']:.2f} Gyr | z>{z_cut:.0f}",
        sep,
        f"P(anomalía) ΛCDM base      : {m['p_base']:.5f}",
        f"P(anomalía) sectorial      : {m['p_sect']:.5f}",
        f"Ratio R                    : {m['ratio_R']:.3f}×",
        f"Exceso relativo            : {m['exceso_pct']:+.1f}%",
        sep,
        f"KS statistic D             : {m['ks_D']:.5f}",
        f"KS p-value                 : {m['ks_p']:.4e} {'★ sig.' if m['ks_sig'] else '(no sig.)'}",
        f"KL divergencia             : {m['kl_div']:.5f}",
        sep,
        f"Pearson r (base)           : {m['pearson_base']:.4f}",
        f"Pearson r (sectorial)      : {m['pearson_sect']:.4f}",
        sep,
        f"N detectables z>{z_cut:.0f} (base): {m['N_visible_z_base']:,}",
        f"N detectables z>{z_cut:.0f} (sect): {m['N_visible_z_sect']:,}",
        f"N masivas    z>{z_cut:.0f} (base): {m['N_massive_z_base']:,}",
        f"N masivas    z>{z_cut:.0f} (sect): {m['N_massive_z_sect']:,}",
        sep,
        f"Anómalas (sectorial)       : {m['n_anom']:,}",
        f"Anómalas que son rem.      : {m['n_rem_anom']:,} ({m['pct_rem_anom']:.1f}%)",
        sep,
        "── Señal / Cola (v0.5.3) ───────────────────────────────",
        f"Q99 dt_signal base         : {m['q99_dt_signal_sect'] - m['delta_q99']:+.4f} Gyr",
        f"Q99 dt_signal sect         : {m['q99_dt_signal_sect']:+.4f} Gyr",
        f"ΔQ99 (sect − base)         : {m['delta_q99']:+.4f} Gyr",
        f"P(Δt_signal > 0.5 Gyr) base: {m['p_tail_base']:.5f}",
        f"P(Δt_signal > 0.5 Gyr) sect: {m['p_tail_sect']:.5f}",
        f"ΔP_tail (sect − base)      : {m['delta_p_tail']:+.5f}",
        f"tail_ratio (auxiliar)      : {m['tail_ratio']:.3f}× [inestable si base≈0]",
        f"SNR_tail (Q99/σ_ruido)     : {snr_t:+.3f} [{label}]",
        sep,
    ]
    for line in lines:
        logger.info(line)
