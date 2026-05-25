"""
core/cosmologia.py — Cálculo de edades y volúmenes comóviles (Planck18)
SMCHS v0.5.3 / Hipótesis Sectorial v3.1

Precalcula tablas interpoladas para velocidad en corridas masivas.
"""

import logging
import numpy as np
from astropy.cosmology import Planck18 as cosmo
import config as cfg

logger = logging.getLogger(__name__)
logger.info("[cosmo] Precalculando tabla Planck18...")

_z_table  = np.linspace(cfg.Z_MIN - 0.2, cfg.Z_MAX + 0.2, 800)
_t_table  = cosmo.age(_z_table).value                          # Gyr
_dv_table = cosmo.differential_comoving_volume(_z_table).value # Mpc³/sr
_dv_table = _dv_table / _dv_table.sum()


def _rng_or_default(rng: np.random.Generator | None = None) -> np.random.Generator:
    """Devuelve el RNG recibido o crea uno determinista con cfg.SEED."""
    return rng if rng is not None else np.random.default_rng(cfg.SEED)


def edad_lcdm(z: np.ndarray) -> np.ndarray:
    """
    Edad del universo en el modelo ΛCDM (Planck18) para un array de redshift.
    Usa interpolación sobre tabla precalculada.
    """
    return np.interp(z, _z_table, _t_table)


def samplear_redshift(n: int, rng: np.random.Generator | None = None) -> np.ndarray:
    """
    Muestrea redshift ponderado por volumen comóvil diferencial dV/dz·dΩ.
    Agrega pequeño jitter uniforme para suavizar la grilla.
    """
    rng = _rng_or_default(rng)
    idx = rng.choice(len(_z_table), size=n, p=_dv_table)
    z = _z_table[idx] + rng.uniform(-0.025, 0.025, n)
    return np.clip(z, cfg.Z_MIN, cfg.Z_MAX)


def schechter_sample(n: int, mstar_z: np.ndarray,
                     alpha: float, rng: np.random.Generator | None = None) -> np.ndarray:
    """
    Muestrea log10(M*) de una función de masa Schechter por rechazo.

    Nota: para eficiencia, cada batch usa la mediana de M*(z) del batch como
    valor de referencia. En el pipeline principal se llama por bins de redshift,
    por lo que la aproximación es local y estable.
    """
    rng = _rng_or_default(rng)
    out = np.empty(n)
    filled = 0
    batch = max(n * 4, 1024)

    while filled < n:
        remaining = n - filled
        current_batch = max(min(batch, remaining * 6), 512)
        cands = rng.uniform(7.0, 12.5, current_batch)
        # Aproximación local: mediana de M*(z) del tramo por llenar.
        mstar_ref = float(np.median(mstar_z[filled:min(filled + remaining, n)]))
        x = 10 ** (cands - mstar_ref)
        phi = x ** (alpha + 1) * np.exp(-x)
        phi /= max(phi.max(), 1e-12)
        accept = rng.random(current_batch) < phi
        accepted = cands[accept]
        take = min(len(accepted), remaining)
        if take == 0:
            continue
        out[filled:filled + take] = accepted[:take]
        filled += take

    return out
