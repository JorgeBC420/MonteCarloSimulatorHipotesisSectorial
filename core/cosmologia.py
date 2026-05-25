"""
core/cosmologia.py — Cálculo de edades y volúmenes comóviles (Planck18)

Precalcula tablas interpoladas para velocidad en corridas masivas.
"""

import numpy as np
from astropy.cosmology import Planck18 as cosmo
from config import Z_MIN, Z_MAX, SEED

_RNG = np.random.default_rng(SEED)

# ── Tablas interpoladas (calculadas una sola vez al importar) ────────────────
print("  [cosmo] Precalculando tabla Planck18...", flush=True)
_z_table  = np.linspace(Z_MIN - 0.2, Z_MAX + 0.2, 800)
_t_table  = cosmo.age(_z_table).value                          # Gyr
_dv_table = cosmo.differential_comoving_volume(_z_table).value # Mpc³/sr
_dv_table /= _dv_table.sum()


def edad_lcdm(z: np.ndarray) -> np.ndarray:
    """
    Edad del universo en el modelo ΛCDM (Planck18) para un array de redshift.
    Usa interpolación sobre tabla precalculada → ~100× más rápido que cosmo.age().
    """
    return np.interp(z, _z_table, _t_table)


def samplear_redshift(n: int, rng: np.random.Generator = None) -> np.ndarray:
    """
    Muestrea redshift ponderado por volumen comóvil diferencial dV/dz·dΩ.
    Agrega pequeño jitter uniforme para suavizar la grilla.
    """
    rng = rng or _RNG
    idx = rng.choice(len(_z_table), size=n, p=_dv_table)
    z = _z_table[idx] + rng.uniform(-0.025, 0.025, n)
    return np.clip(z, Z_MIN, Z_MAX)


def schechter_sample(n: int, mstar_z: np.ndarray,
                     alpha: float, rng: np.random.Generator = None) -> np.ndarray:
    """
    Muestrea log10(M*) de una función de masa Schechter por rechazo.

    Parámetros
    ----------
    n       : número de objetos
    mstar_z : array (n,) con M* característica en log10 para cada objeto
              (puede variar con z)
    alpha   : pendiente faint end
    rng     : generador aleatorio

    Retorna
    -------
    log_m_seed : array (n,) de masas iniciales en log10(M☉)
    """
    rng = rng or _RNG
    log_m_grid = np.linspace(7.0, 12.5, 1200)
    out = np.empty(n)
    filled = 0

    # Procesamos en batches para aprovechar vectorización
    batch = n * 4
    while filled < n:
        cands = rng.uniform(7.0, 12.5, batch)
        # Usamos mstar_z promedio del batch como proxy (buena aprox.)
        mstar_ref = np.median(mstar_z[filled:filled + batch]) if filled < n else mstar_z.mean()
        x = 10 ** (cands - mstar_ref)
        phi = x ** (alpha + 1) * np.exp(-x)
        phi /= phi.max()
        accept = rng.random(batch) < phi
        accepted = cands[accept]
        take = min(len(accepted), n - filled)
        out[filled:filled + take] = accepted[:take]
        filled += take

    return out
