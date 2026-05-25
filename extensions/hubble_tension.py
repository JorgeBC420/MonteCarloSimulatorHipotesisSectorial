"""
extensions/hubble_tension.py

Módulo auxiliar independiente para explorar una parametrización fenomenológica
entre la Tensión de Hubble y una fracción efectiva de masa no visible.

IMPORTANTE
---------
Este módulo NO está conectado al core Monte Carlo del SMCHS y NO afirma que la
materia oscura resuelva la Tensión de Hubble. Solo implementa la pregunta
falsable propuesta en la HTSC v3.2.1:

    H0_local = H0_CMB * (1 + lambda * f_DM_eff)

Si distintos sistemas dinámicos producen lambdas incompatibles o absurdos, el
módulo se debilita/falsa como explicación fenomenológica.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Sequence

import numpy as np


DEFAULT_H0_CMB = 67.4
DEFAULT_H0_LOCAL = 73.0


@dataclass(frozen=True)
class LambdaEstimate:
    """Resultado de estimar lambda para un sistema dinámico."""

    f_dm_eff: float
    lambda_param: float
    epsilon_h: float
    h0_local: float
    h0_cmb: float
    system_name: str = "system"

    @property
    def plausible_unit_interval(self) -> bool:
        """Criterio conservador opcional: 0 <= lambda <= 1."""
        return 0.0 <= self.lambda_param <= 1.0


def epsilon_hubble(h0_local: float = DEFAULT_H0_LOCAL, h0_cmb: float = DEFAULT_H0_CMB) -> float:
    """epsilon_H = H0_local / H0_CMB - 1."""
    if h0_cmb <= 0:
        raise ValueError("h0_cmb debe ser positivo.")
    if h0_local <= 0:
        raise ValueError("h0_local debe ser positivo.")
    return float(h0_local / h0_cmb - 1.0)


def lambda_from_f_dm(
    f_dm_eff: float,
    h0_local: float = DEFAULT_H0_LOCAL,
    h0_cmb: float = DEFAULT_H0_CMB,
    system_name: str = "system",
) -> LambdaEstimate:
    """Calcula lambda = epsilon_H / f_DM^eff.

    Parameters
    ----------
    f_dm_eff:
        Fracción efectiva de masa no visible, 0 < f_dm_eff <= 1.
    h0_local, h0_cmb:
        Valores comparados de H0 en km/s/Mpc. Defaults aproximados.
    system_name:
        Etiqueta del sistema dinámico usado.
    """
    f = float(f_dm_eff)
    if not np.isfinite(f):
        raise ValueError("f_dm_eff debe ser finito.")
    if f <= 0 or f > 1:
        raise ValueError("f_dm_eff debe estar en el intervalo (0, 1].")
    eps = epsilon_hubble(h0_local=h0_local, h0_cmb=h0_cmb)
    return LambdaEstimate(
        f_dm_eff=f,
        lambda_param=eps / f,
        epsilon_h=eps,
        h0_local=float(h0_local),
        h0_cmb=float(h0_cmb),
        system_name=system_name,
    )


def implied_h0_local(
    f_dm_eff: float,
    lambda_param: float,
    h0_cmb: float = DEFAULT_H0_CMB,
) -> float:
    """H0_local predicho por H0_CMB * (1 + lambda f_DM^eff)."""
    f = float(f_dm_eff)
    lam = float(lambda_param)
    if f < 0 or f > 1:
        raise ValueError("f_dm_eff debe estar en [0, 1].")
    if h0_cmb <= 0:
        raise ValueError("h0_cmb debe ser positivo.")
    return float(h0_cmb * (1.0 + lam * f))


def estimate_lambdas(
    f_dm_values: Sequence[float],
    names: Sequence[str] | None = None,
    h0_local: float = DEFAULT_H0_LOCAL,
    h0_cmb: float = DEFAULT_H0_CMB,
) -> list[LambdaEstimate]:
    """Calcula lambda para múltiples sondas dinámicas."""
    if names is not None and len(names) != len(f_dm_values):
        raise ValueError("names y f_dm_values deben tener la misma longitud.")
    estimates = []
    for idx, f in enumerate(f_dm_values):
        name = names[idx] if names is not None else f"system_{idx+1}"
        estimates.append(lambda_from_f_dm(f, h0_local=h0_local, h0_cmb=h0_cmb, system_name=name))
    return estimates


@dataclass(frozen=True)
class LambdaStabilityReport:
    """Resumen de estabilidad empírica del parámetro lambda."""

    n: int
    mean_lambda: float
    std_lambda: float
    cv_lambda: float
    min_lambda: float
    max_lambda: float
    all_unit_interval: bool
    stable: bool
    threshold_cv: float

    def as_dict(self) -> dict[str, float | int | bool]:
        return {
            "n": self.n,
            "mean_lambda": self.mean_lambda,
            "std_lambda": self.std_lambda,
            "cv_lambda": self.cv_lambda,
            "min_lambda": self.min_lambda,
            "max_lambda": self.max_lambda,
            "all_unit_interval": self.all_unit_interval,
            "stable": self.stable,
            "threshold_cv": self.threshold_cv,
        }


def lambda_stability_report(
    estimates: Iterable[LambdaEstimate],
    threshold_cv: float = 0.25,
    require_unit_interval: bool = True,
) -> LambdaStabilityReport:
    """Evalúa si lambda converge entre sondas.

    Criterio base:
        cv(lambda) = std(lambda) / |mean(lambda)| <= threshold_cv

    Opcionalmente exige 0 <= lambda <= 1 para todos los sistemas.
    Ese criterio es conservador y puede relajarse en exploraciones futuras.
    """
    estimates = list(estimates)
    if not estimates:
        raise ValueError("Se requiere al menos una estimación de lambda.")

    lambdas = np.array([e.lambda_param for e in estimates], dtype=float)
    if not np.all(np.isfinite(lambdas)):
        raise ValueError("Todas las lambdas deben ser finitas.")

    mean = float(np.mean(lambdas))
    std = float(np.std(lambdas, ddof=1)) if len(lambdas) > 1 else 0.0
    cv = float(std / abs(mean)) if mean != 0 else float("inf")
    all_unit = all(e.plausible_unit_interval for e in estimates)
    stable = cv <= threshold_cv and (all_unit if require_unit_interval else True)

    return LambdaStabilityReport(
        n=len(lambdas),
        mean_lambda=mean,
        std_lambda=std,
        cv_lambda=cv,
        min_lambda=float(np.min(lambdas)),
        max_lambda=float(np.max(lambdas)),
        all_unit_interval=all_unit,
        stable=bool(stable),
        threshold_cv=float(threshold_cv),
    )
