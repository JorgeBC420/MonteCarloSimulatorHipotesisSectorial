"""
core/metric_dilution.py — Dilución métrica opcional de f_rem
SMCHS v0.5.5 / Hipótesis Sectorial v3.1+

Este módulo NO reemplaza el modelo base. Implementa una extensión opcional:

    f_rem_eff(z) = min[f_max, f_rem_0 * ((1+z)/(1+z_ref))**gamma]
    gamma = 3(1+w)

Interpretación:
    - w=0     → remanentes tipo materia no relativista, gamma=3
    - w=1/3   → componente relativista, gamma=4
    - w=-1    → componente constante, gamma=0

La función devuelve probabilidades clippeadas en [0, f_max]. Al estar separada
del core y desactivada por defecto, conserva la reproducibilidad histórica de SMCHS.
"""
from __future__ import annotations

import numpy as np


def gamma_from_w(w_rem: float) -> float:
    """Convierte el parámetro de ecuación de estado w en gamma=3(1+w)."""
    return 3.0 * (1.0 + float(w_rem))


def f_rem_eff_z(
    z: np.ndarray,
    f_rem0: float,
    z_ref: float = 12.0,
    w_rem: float = 0.0,
    f_max: float = 0.08,
) -> np.ndarray:
    """
    Fracción efectiva de remanencia con dilución métrica opcional.

    Parámetros
    ----------
    z:
        Redshift de cada objeto.
    f_rem0:
        Fracción base de remanentes definida por el usuario.
    z_ref:
        Redshift de referencia donde f_rem_eff≈f_rem0.
    w_rem:
        Parámetro de ecuación de estado efectivo.
    f_max:
        Límite superior de seguridad para evitar probabilidades absurdas.

    Retorna
    -------
    np.ndarray
        Probabilidad efectiva por objeto, acotada en [0, f_max].
    """
    z = np.asarray(z, dtype=float)
    if f_rem0 <= 0:
        return np.zeros_like(z, dtype=float)
    if z_ref <= -1:
        raise ValueError("z_ref debe ser mayor que -1")
    if f_max <= 0:
        return np.zeros_like(z, dtype=float)

    gamma = gamma_from_w(w_rem)
    scale = ((1.0 + z) / (1.0 + float(z_ref))) ** gamma
    p = float(f_rem0) * scale
    return np.clip(p, 0.0, float(f_max))
