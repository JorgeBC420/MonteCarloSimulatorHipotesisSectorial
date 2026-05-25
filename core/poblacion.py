"""
core/poblacion.py — Pipeline de 5 fases
SMCHS v0.5.3 / Hipótesis Sectorial v3.1

CHANGELOG v0.5.3:
    Separación explícita señal / observado / ruido en Fase C:
        dt_signal   = t_chem_true − t_ΛCDM   [componente física pura]
        dt_observed = t_chem_obs  − t_ΛCDM   [componente medible con ruido]
        dt_noise    = dt_observed − dt_signal [contaminación por eps_Z]
    Permite evaluar si el exceso de madurez química persiste
    más allá de fluctuaciones estocásticas de metalicidad.

v0.4.0: ruido eps_Z/eps_M en catálogo, hashlib.sha256, Schechter por bins.
v0.3.0: Δt_i correcto (invertir Z_met con ruido, no Z_det sin ruido).
v0.2.0: catálogo base compartido entre modelos.

Diseño de catálogo pareado completo:
    catalogo = inicializar_catalogo(N)
    # Catálogo contiene: z, t_lcdm, log_m_seed, eps_Z, eps_M
    pop_a = construir_poblacion(catalogo, f_rem=0.0)
    pop_b = construir_poblacion(catalogo, f_rem=0.01)
    # Mismos objetos, mismo ruido, solo varía la inyección → diferencia limpia.
"""

import hashlib
import logging
from typing import Any
import numpy as np
import config as cfg
from config import (
    N, MSTAR_LOG10_0, MSTAR_EVO_LAMB, SCHECHTER_A, SCHECHTER_Z_BINS,
    Z_INICIAL, ALPHA_Z, SIGMA_Z, BETA_M, SIGMA_M, MUV_OFFSET, 
    MUV_SLOPE, MUV_LIM_BASE, MUV_LIM_SLOPE, F_REM_DEFAULT, T_PREV_MU, T_PREV_SIG
)
from core.cosmologia import edad_lcdm, samplear_redshift, schechter_sample
from core.metric_dilution import f_rem_eff_z

logger = logging.getLogger(__name__)


def _rng_or_default(rng: np.random.Generator | None = None) -> np.random.Generator:
    return rng if rng is not None else np.random.default_rng(cfg.SEED)


def _semilla_estable(f_rem: float, t_mu: float) -> int:
    """
    Deriva una semilla entera reproducible entre sesiones usando SHA-256.

    hash() de Python no es estable: PYTHONHASHSEED varía entre ejecuciones,
    lo que rompe reproducibilidad. hashlib.sha256 siempre produce el mismo
    resultado para el mismo input.
    """
    key = f"{f_rem:.6f}_{t_mu:.4f}".encode()
    digest = hashlib.sha256(key).hexdigest()[:8]
    return cfg.SEED + int(digest, 16) % (2**31)


# ─────────────────────────────────────────────────────────────────────────────
# FASE A — Catálogo base (compartido y ruidoso)
# ─────────────────────────────────────────────────────────────────────────────

def _schechter_por_bins(z: np.ndarray[Any, Any], rng: np.random.Generator) -> np.ndarray[Any, Any]:
    """
    Muestrea log10(M★) con Schechter aplicado por bins de redshift.

    Evita la aproximación de usar la mediana global de mstar_z.
    Cada bin usa su propio M* característico, haciendo que galaxias a z=14
    tengan distribuciones de masa más restrictivas que las de z=5.
    """
    log_m_seed = np.full(len(z), np.nan)
    bins = SCHECHTER_Z_BINS
    
    # Optimización i7: Clasificación en bins en una sola pasada (O(N) en lugar de O(N*bins))
    bin_indices = np.digitize(z, bins) - 1
    
    # Iterar solo sobre bins que contienen datos
    for i in np.unique(bin_indices):
        if 0 <= i < len(bins) - 1:
            mask = (bin_indices == i)
            n_bin = np.count_nonzero(mask)
            z_mid = 0.5 * (bins[i] + bins[i + 1])
            mstar_bin = np.full(n_bin, MSTAR_LOG10_0 - MSTAR_EVO_LAMB * max(z_mid - 8.0, 0.0))
            log_m_seed[mask] = schechter_sample(n_bin, mstar_bin, SCHECHTER_A, rng)

    # Validación de seguridad: asegurar que todo objeto tenga masa asignada
    if np.any(np.isnan(log_m_seed)):
        # Si hay valores en el borde superior o fuera de rango (z >= 17.0)
        nan_mask = np.isnan(log_m_seed)
        n_nan = np.count_nonzero(nan_mask)
        i_last = len(bins) - 2
        # Usar el borde del último bin para la evolución de M*
        z_ref = bins[i_last + 1] 
        mstar_bin = np.full(n_nan, MSTAR_LOG10_0 - MSTAR_EVO_LAMB * max(z_ref - 8.0, 0.0))
        log_m_seed[nan_mask] = schechter_sample(n_nan, mstar_bin, SCHECHTER_A, rng)

    return log_m_seed


def inicializar_catalogo(n: int | None = None, rng: np.random.Generator | None = None) -> dict[str, Any]:
    """
    Fase A: genera el catálogo base compartido.

    Almacena también los ruidos eps_Z y eps_M para que TODOS los modelos
    que se construyan sobre este catálogo usen exactamente el mismo ruido.
    Así las diferencias entre ΛCDM y sectorial provienen exclusivamente
    de la inyección f_rem, no de fluctuaciones del ruido observacional.

    Retorna dict con:
        z, t_lcdm, log_m_seed, mstar_z_char, eps_Z, eps_M, n
    """
    if n is None:
        n = N
    rng = _rng_or_default(rng)

    z          = samplear_redshift(n, rng)
    t_lcdm     = edad_lcdm(z)
    mstar_z_char = MSTAR_LOG10_0 - MSTAR_EVO_LAMB * np.maximum(z - 8.0, 0.0)

    # Schechter por bins de redshift (más preciso que aprox. mediana)
    log_m_seed = _schechter_por_bins(z, rng)

    # Ruidos almacenados en el catálogo → compartidos entre modelos
    eps_Z = rng.normal(0.0, SIGMA_Z, n)
    eps_M = rng.normal(0.0, SIGMA_M, n)

    return {
        "z":            z,
        "t_lcdm":       t_lcdm,
        "log_m_seed":   log_m_seed,
        "mstar_z_char": mstar_z_char,
        "eps_Z":        eps_Z,
        "eps_M":        eps_M,
        "n":            n,
    }


# ─────────────────────────────────────────────────────────────────────────────
# FASE B — Inyección estocástica
# ─────────────────────────────────────────────────────────────────────────────

def inyectar_madurez(catalogo: dict[str, Any],
                     f_rem: float = F_REM_DEFAULT,
                     t_mu:  float = T_PREV_MU,
                     t_sig: float = T_PREV_SIG,
                     rng: np.random.Generator | None = None,
                     metric_dilution: bool = False,
                     w_rem: float = 0.0,
                     z_ref: float = 12.0,
                     f_max: float = 0.08) -> tuple[np.ndarray[Any, Any], np.ndarray[Any, Any], np.ndarray[Any, Any]]:
    """
    Fase B: desplazamiento temporal Δt_heredada para fracción f_rem de objetos.

        t_eff = t_ΛCDM + Δt_heredada
        Δt_heredada ~ LogNormal(log(t_mu), t_sig)  [solo remanentes]

    Si metric_dilution=True, f_rem deja de ser probabilidad plana y se evalúa
    objeto por objeto con:

        f_rem_eff(z)=min[f_max, f_rem*((1+z)/(1+z_ref))**(3(1+w_rem))]

    Esto implementa la dilución métrica opcional de la HTSC sin alterar el
    comportamiento histórico por defecto.

    Retorna (t_eff, es_rem, delta_t).
    """
    rng    = _rng_or_default(rng)
    n      = catalogo["n"]
    t_lcdm = catalogo["t_lcdm"]

    if metric_dilution:
        p_rem = f_rem_eff_z(catalogo["z"], f_rem, z_ref=z_ref, w_rem=w_rem, f_max=f_max)
        es_rem = rng.random(n) < p_rem
    else:
        es_rem = rng.random(n) < f_rem
    delta_t = np.zeros(n)
    n_rem   = int(es_rem.sum())

    if n_rem > 0 and t_mu > 0:
        delta_t[es_rem] = rng.lognormal(np.log(t_mu), t_sig, n_rem)

    return t_lcdm + delta_t, es_rem, delta_t


# ─────────────────────────────────────────────────────────────────────────────
# FASE C — Observables proxy con ruido pareado
# ─────────────────────────────────────────────────────────────────────────────

def calcular_observables(catalogo: dict[str, Any],
                         t_eff: np.ndarray[Any, Any]) -> dict[str, Any]:
    """
    Fase C: t_eff → observables con separación señal/ruido (v0.5.3).

    Usa eps_Z y eps_M del catálogo base (compartidos entre modelos).
    Separa explícitamente la componente física de la observacional:

    ── Metalicidad ──────────────────────────────────────────────────────
        Z_true = Z_inicial + α·log(1 + t_eff)          [señal pura]
        Z_obs  = clip(Z_true + eps_Z, 0, 1.8)           [observable]

    ── Masa estelar ─────────────────────────────────────────────────────
        log M* = clip(log M_seed + β·t_eff + eps_M, 6, 13.5)

    ── Magnitud UV proxy ────────────────────────────────────────────────
        M_UV = MUV_OFFSET + MUV_SLOPE·(log M* − 9)

    ── Separación Δt_i señal / observado / ruido (Predicción P2 v3.1) ──

        t_chem_true = expm1((Z_true − Z_ini) / α)   ← solo física
        t_chem_obs  = expm1((Z_obs  − Z_ini) / α)   ← con ruido

        dt_signal   = t_chem_true − t_ΛCDM   → desacople FÍSICO
        dt_observed = t_chem_obs  − t_ΛCDM   → desacople MEDIBLE
        dt_noise    = dt_observed − dt_signal → contaminación por eps_Z

    dt_signal > 0 con f_rem > 0 → la hipótesis produce madurez real.
    Si dt_signal ≈ 0 pero dt_observed > 0, el exceso es solo ruido.
    La detectabilidad se estima con métricas de cola (Q99/SNR_tail), no con la mediana.
    """
    t_lcdm  = catalogo["t_lcdm"]
    log_m_s = catalogo["log_m_seed"]
    eps_Z   = catalogo["eps_Z"]
    eps_M   = catalogo["eps_M"]

    # ── Metalicidad: verdadera y observada ───────────────────────────────────
    Z_true = Z_INICIAL + ALPHA_Z * np.log1p(t_eff)
    Z_obs  = np.clip(Z_true + eps_Z, 0.001, 1.8)

    # ── Masa estelar (observable) ─────────────────────────────────────────────
    log_m = np.clip(log_m_s + BETA_M * t_eff + eps_M, 6.0, 13.5)

    # ── Magnitud UV proxy ────────────────────────────────────────────────────
    lum_proxy = 10 ** (0.4 * log_m)
    M_UV = MUV_OFFSET + MUV_SLOPE * (log_m - 9.0)

    # ── Δt_i: señal, observado, ruido ────────────────────────────────────────
    def _t_chem(Z: np.ndarray[Any, Any]) -> np.ndarray[Any, Any]:
        return np.expm1(np.maximum((Z - Z_INICIAL) / ALPHA_Z, 0.0))

    t_chem_true = _t_chem(Z_true)
    t_chem_obs  = _t_chem(Z_obs)

    dt_signal   = t_chem_true - t_lcdm   # desacople físico puro
    dt_observed = t_chem_obs  - t_lcdm   # desacople medible (con ruido)
    dt_noise    = dt_observed - dt_signal # contribución del ruido eps_Z

    return {
        # metalicidad
        "Z_true":       Z_true,
        "Z_met":        Z_obs,         # alias observado (compatibilidad)
        # masa / luminosidad
        "log_m":        log_m,
        "lum_proxy":    lum_proxy,
        "M_UV":         M_UV,
        # t_chem
        "t_chem_true":  t_chem_true,
        "t_chem_obs":   t_chem_obs,
        "t_chem":       t_chem_obs,    # alias (compatibilidad)
        # Δt_i tripartito
        "dt_signal":    dt_signal,
        "dt_observed":  dt_observed,
        "dt_noise":     dt_noise,
        "delta_t_obs":  dt_observed,   # alias (compatibilidad)
    }


# ─────────────────────────────────────────────────────────────────────────────
# FASE D — Filtro proxy de detectabilidad
# ─────────────────────────────────────────────────────────────────────────────

def aplicar_filtro_detectabilidad_proxy(M_UV: np.ndarray[Any, Any],
                                        z: np.ndarray[Any, Any]) -> np.ndarray[Any, Any]:
    """
    Fase D: proxy simplificado de detectabilidad por magnitud UV.

    Este NO es un modelo instrumental de JWST. Captura solo el sesgo
    de luminosidad: a mayor redshift, el umbral de detección es más estricto.

        M_UV_lim(z) = MUV_LIM_BASE − MUV_LIM_SLOPE · (z − 8)
        Visible si M_UV < M_UV_lim(z)

    Retorna array booleano (n,).
    """
    m_uv_lim = MUV_LIM_BASE - MUV_LIM_SLOPE * (z - 8.0)
    return M_UV < m_uv_lim


# Alias de compatibilidad
aplicar_filtro_jwst = aplicar_filtro_detectabilidad_proxy


# ─────────────────────────────────────────────────────────────────────────────
# INTEGRADOR — construir_poblacion()
# ─────────────────────────────────────────────────────────────────────────────

def construir_poblacion(catalogo: dict[str, Any],
                        f_rem: float = F_REM_DEFAULT,
                        t_mu:  float = T_PREV_MU,
                        t_sig: float = T_PREV_SIG,
                        rng: np.random.Generator | None = None,
                        metric_dilution: bool = False,
                        w_rem: float = 0.0,
                        z_ref: float = 12.0,
                        f_max: float = 0.08) -> dict[str, Any]:
    """
    Pipeline completo B→D sobre un catálogo base dado.

    La semilla para la inyección estocástica se deriva con SHA-256 a partir
    de (f_rem, t_mu), lo que garantiza reproducibilidad entre sesiones.

    El ruido eps_Z y eps_M viene del catálogo base → idéntico entre modelos.
    Las únicas diferencias entre construir_poblacion(cat, f_rem=0.0) y
    construir_poblacion(cat, f_rem=0.01) son los objetos marcados como
    remanentes y su Δt_heredada.

    Ejemplo de análisis contrafactual limpio:
        cat   = inicializar_catalogo(N)
        base  = construir_poblacion(cat, f_rem=0.0)   # ΛCDM puro
        sect  = construir_poblacion(cat, f_rem=0.01)  # +1% madurez heredada
        # Mismos objetos, mismo ruido, distinto f_rem → diferencia limpia.
    """
    if rng is None:
        rng = np.random.default_rng(_semilla_estable(f_rem, t_mu))

    t_eff, es_rem, delta_t = inyectar_madurez(catalogo, f_rem, t_mu, t_sig, rng, metric_dilution=metric_dilution, w_rem=w_rem, z_ref=z_ref, f_max=f_max)
    obs     = calcular_observables(catalogo, t_eff)
    visible = aplicar_filtro_detectabilidad_proxy(obs["M_UV"], catalogo["z"])

    return {
        # catálogo base
        "z":          catalogo["z"],
        "t_lcdm":     catalogo["t_lcdm"],
        "log_m_seed": catalogo["log_m_seed"],
        # inyección
        "t_eff":      t_eff,
        "es_rem":     es_rem,
        "delta_t":    delta_t,
        # observables
        **obs,
        # filtro
        "visible":    visible,
        # metadata
        "f_rem":      f_rem,
        "t_mu":       t_mu,
        "metric_dilution": metric_dilution,
        "w_rem":      w_rem,
        "z_ref":      z_ref,
        "f_max":      f_max,
        "n":          catalogo["n"],
    }
