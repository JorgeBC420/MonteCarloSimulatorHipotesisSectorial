"""
core/geometric_remnants.py — Modo experimental: remanencia por fluctuación geométrica
SMCHS v0.5.6 / Hipótesis Sectorial v3.2.1

Implementa --remnant-mode geometric como extensión exploratoria SEPARADA del modelo base.
NO reemplaza core/poblacion.py. Es un módulo alternativo que puede compararse contra
el modo flat y el modo metric para evaluar dependencia de f_rem plano.

Idea central
------------
En lugar de f_rem = constante, la probabilidad de remanencia de cada objeto
depende de una variable latente ψ_i (fluctuación geométrica proxy) y de la
dilución métrica por expansión. La señal "surge" de la distribución de ψ,
no de un número fijo elegido a mano.

    ψ_i ~ N(0, 1)                              (fluctuación geométrica normalizada)
    W_i = ((1+z_i)/(1+z_ref))^gamma            (peso de dilución métrica)
    σ(x) = 1 / (1 + exp(-x))                  (función sigmoide)
    p_i = clip(f0 * W_i * σ((ψ_i - ψ_c) / s_ψ), 0, f_max)

    es_rem_i ~ Bernoulli(p_i)

Parámetros
----------
f0      : escala base (análogo a f_rem en modo flat; debe pre-registrarse)
psi_c   : umbral de la sigmoide (pre-registrado; no ajustar para mejorar fit)
s_psi   : suavidad de la transición (pre-registrado)
z_ref   : redshift de referencia para dilución métrica
w_rem   : parámetro de ecuación de estado (0=materia, 1/3=rad, -1=cte)
f_max   : límite superior de seguridad

ADVERTENCIA METODOLÓGICA
------------------------
Estos parámetros deben fijarse ANTES de comparar contra datos externos (JADES/TNG/SIMBA).
Si se ajustan después de ver los resultados, el sesgo se traslada de f_rem a (f0, psi_c, s_psi).
Ver documentacion/PRE_REGISTRO_PARAMETROS_SMCHS.md para valores congelados.
"""

from __future__ import annotations

import hashlib
import logging
from typing import Any

import numpy as np

from config import (
    F_REM_DEFAULT, T_PREV_MU, T_PREV_SIG, SEED,
    Z_INICIAL, ALPHA_Z, SIGMA_Z, BETA_M, SIGMA_M,
    MUV_OFFSET, MUV_SLOPE, MUV_LIM_BASE, MUV_LIM_SLOPE,
)
from core.cosmologia import edad_lcdm, samplear_redshift, schechter_sample
from core.metric_dilution import gamma_from_w

logger = logging.getLogger(__name__)

# ── Parámetros por defecto del modo geometric ─────────────────────────────────
# CONGELADOS para validación inicial. Consultar PRE_REGISTRO_PARAMETROS_SMCHS.md
GEO_F0_DEFAULT    = F_REM_DEFAULT   # escala base (mismo orden que f_rem flat)
GEO_PSI_C_DEFAULT = 0.5             # umbral sigmoide: solo fluctuaciones > 0.5σ generan remanentes
GEO_S_PSI_DEFAULT = 0.3             # suavidad de transición
GEO_Z_REF_DEFAULT = 12.0
GEO_W_REM_DEFAULT = 0.0
GEO_F_MAX_DEFAULT = 0.08


def _semilla_geo(f0: float, psi_c: float) -> int:
    key = f"geo_{f0:.6f}_{psi_c:.4f}".encode()
    digest = hashlib.sha256(key).hexdigest()[:8]
    return SEED + int(digest, 16) % (2**31)


def p_geometric(
    z: np.ndarray,
    rng: np.random.Generator,
    f0: float = GEO_F0_DEFAULT,
    psi_c: float = GEO_PSI_C_DEFAULT,
    s_psi: float = GEO_S_PSI_DEFAULT,
    z_ref: float = GEO_Z_REF_DEFAULT,
    w_rem: float = GEO_W_REM_DEFAULT,
    f_max: float = GEO_F_MAX_DEFAULT,
) -> np.ndarray:
    """
    Calcula la probabilidad de remanencia p_i para cada objeto.

    ψ_i ~ N(0,1) → W_i (dilución) → σ(ψ_i) → p_i ∈ [0, f_max]
    """
    z = np.asarray(z, dtype=float)
    gamma = gamma_from_w(w_rem)

    # Fluctuación geométrica latente (una por objeto, reproducible via rng del catálogo)
    psi = rng.standard_normal(len(z))

    # Dilución métrica por expansión
    W = ((1.0 + z) / (1.0 + float(z_ref))) ** gamma

    # Sigmoide sobre fluctuación normalizada
    sig = 1.0 / (1.0 + np.exp(-((psi - psi_c) / max(s_psi, 1e-6))))

    p = float(f0) * W * sig
    return np.clip(p, 0.0, float(f_max))


def inyectar_madurez_geometric(
    catalogo: dict[str, Any],
    f0: float = GEO_F0_DEFAULT,
    t_mu: float = T_PREV_MU,
    t_sig: float = T_PREV_SIG,
    psi_c: float = GEO_PSI_C_DEFAULT,
    s_psi: float = GEO_S_PSI_DEFAULT,
    z_ref: float = GEO_Z_REF_DEFAULT,
    w_rem: float = GEO_W_REM_DEFAULT,
    f_max: float = GEO_F_MAX_DEFAULT,
    rng: np.random.Generator | None = None,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Fase B en modo geometric: remanencia basada en fluctuación latente ψ.

    La fracción de remanentes NO es fija; emerge de la distribución de ψ
    y de los pesos de dilución métrica. Retorna (t_eff, es_rem, delta_t).
    """
    if rng is None:
        rng = np.random.default_rng(_semilla_geo(f0, psi_c))

    n      = catalogo["n"]
    t_lcdm = catalogo["t_lcdm"]
    z      = catalogo["z"]

    p_rem  = p_geometric(z, rng, f0=f0, psi_c=psi_c, s_psi=s_psi,
                         z_ref=z_ref, w_rem=w_rem, f_max=f_max)
    es_rem = rng.random(n) < p_rem

    delta_t = np.zeros(n)
    n_rem   = int(es_rem.sum())
    f_rem_efectivo = n_rem / n

    if n_rem > 0 and t_mu > 0:
        delta_t[es_rem] = rng.lognormal(np.log(t_mu), t_sig, n_rem)

    logger.info(
        "[geometric] f_rem efectivo=%.4f%% (%d/%d objetos)",
        f_rem_efectivo * 100, n_rem, n,
    )

    return t_lcdm + delta_t, es_rem, delta_t


def construir_poblacion_geometric(
    catalogo: dict[str, Any],
    f0: float = GEO_F0_DEFAULT,
    t_mu: float = T_PREV_MU,
    t_sig: float = T_PREV_SIG,
    psi_c: float = GEO_PSI_C_DEFAULT,
    s_psi: float = GEO_S_PSI_DEFAULT,
    z_ref: float = GEO_Z_REF_DEFAULT,
    w_rem: float = GEO_W_REM_DEFAULT,
    f_max: float = GEO_F_MAX_DEFAULT,
    rng: np.random.Generator | None = None,
    quench_uv: bool = False,
    z_quench_thresh: float | None = None,
    m_quench_thresh: float | None = None,
    delta_uv_quench: float | None = None,
) -> dict[str, Any]:
    """
    Pipeline completo en modo geometric.

    v0.5.7: acepta quench_uv y sus umbrales para consistencia con el modo flat.
    Usa calcular_observables y aplicar_filtro_detectabilidad_proxy del módulo base.
    """
    import config as cfg_mod
    from core.poblacion import calcular_observables, aplicar_filtro_detectabilidad_proxy

    # Defaults desde config si no se pasan explícitamente
    z_q = z_quench_thresh if z_quench_thresh is not None else cfg_mod.Z_QUENCH_THRESH
    m_q = m_quench_thresh if m_quench_thresh is not None else cfg_mod.M_QUENCH_THRESH
    d_q = delta_uv_quench if delta_uv_quench is not None else cfg_mod.DELTA_UV_QUENCH

    if rng is None:
        rng = np.random.default_rng(_semilla_geo(f0, psi_c))

    t_eff, es_rem, delta_t = inyectar_madurez_geometric(
        catalogo, f0=f0, t_mu=t_mu, t_sig=t_sig,
        psi_c=psi_c, s_psi=s_psi, z_ref=z_ref,
        w_rem=w_rem, f_max=f_max, rng=rng,
    )
    obs     = calcular_observables(
        catalogo, t_eff,
        quench_uv=quench_uv,
        z_quench_thresh=z_q,
        m_quench_thresh=m_q,
        delta_uv_quench=d_q,
    )
    visible = aplicar_filtro_detectabilidad_proxy(obs["M_UV"], catalogo["z"])

    return {
        "z":            catalogo["z"],
        "t_lcdm":       catalogo["t_lcdm"],
        "log_m_seed":   catalogo["log_m_seed"],
        "t_eff":        t_eff,
        "es_rem":       es_rem,
        "delta_t":      delta_t,
        **obs,
        "visible":      visible,
        "f_rem":        float(es_rem.sum()) / catalogo["n"],
        "t_mu":         t_mu,
        "remnant_mode": "geometric",
        "quench_uv":    quench_uv,
        "geo_f0":       f0,
        "geo_psi_c":    psi_c,
        "geo_s_psi":    s_psi,
        "z_ref":        z_ref,
        "w_rem":        w_rem,
        "f_max":        f_max,
        "n":            catalogo["n"],
    }
