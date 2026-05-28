# -*- coding: utf-8 -*-
"""
analysis/p4_permutation.py

P4-v3.2.2: permutation test externo para comparar colas observacionales
(JADES/ASTRODEEP) contra baselines ΛCDM refinados (TNG/SIMBA).

Resultado positivo = interés fenomenológico frente a ese baseline.
No es confirmación de HTSC.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Dict, Iterable, Literal, Optional, Tuple

import numpy as np

TailDirection = Literal["high", "low"]


@dataclass(frozen=True)
class P4PermutationResult:
    statistic_name: str
    observed_d_tail: float
    p_value: float
    effect_pass: bool
    significance_pass: bool
    htsc_interest: bool
    obs_tail_value: float
    baseline_tail_value: float
    n_obs: int
    n_baseline: int
    n_iter: int
    percentile: float
    direction: str
    effect_threshold: float
    alpha: float
    seed: Optional[int]
    null_mean: float
    null_std: float
    null_q05: float
    null_q50: float
    null_q95: float
    notes: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def _clean_numeric_array(values: Iterable[float], name: str) -> np.ndarray:
    arr = np.asarray(list(values), dtype=float)
    arr = arr[np.isfinite(arr)]
    if arr.size == 0:
        raise ValueError(f"{name} no contiene valores numéricos finitos.")
    return arr


def _tail_value(data: np.ndarray, percentile: float = 99, direction: TailDirection = "high") -> float:
    if not (0 < percentile < 100):
        raise ValueError("percentile debe estar entre 0 y 100.")
    if direction == "high":
        return float(np.percentile(data, percentile))
    if direction == "low":
        return float(np.percentile(data, 100.0 - percentile))
    raise ValueError("direction debe ser 'high' o 'low'.")


def _d_tail(obs: np.ndarray, baseline: np.ndarray, percentile: float, direction: TailDirection) -> Tuple[float, float, float]:
    obs_tail = _tail_value(obs, percentile=percentile, direction=direction)
    base_tail = _tail_value(baseline, percentile=percentile, direction=direction)
    if direction == "high":
        return float(obs_tail - base_tail), obs_tail, base_tail
    return float(base_tail - obs_tail), obs_tail, base_tail


def permutation_test_d_tail(
    obs_data: Iterable[float],
    baseline_data: Iterable[float],
    *,
    effect_threshold: float = 0.15,
    n_iter: int = 10_000,
    percentile: float = 99,
    direction: TailDirection = "high",
    alpha: float = 0.05,
    seed: Optional[int] = 42,
    statistic_name: str = "D_tail",
    min_n: int = 10,
) -> P4PermutationResult:
    obs = _clean_numeric_array(obs_data, "obs_data")
    baseline = _clean_numeric_array(baseline_data, "baseline_data")

    if obs.size < min_n:
        raise ValueError(f"obs_data tiene n={obs.size}; mínimo requerido: {min_n}.")
    if baseline.size < min_n:
        raise ValueError(f"baseline_data tiene n={baseline.size}; mínimo requerido: {min_n}.")
    if n_iter <= 0:
        raise ValueError("n_iter debe ser > 0.")
    if effect_threshold <= 0:
        raise ValueError("effect_threshold debe ser > 0.")
    if not (0 < alpha < 1):
        raise ValueError("alpha debe estar entre 0 y 1.")

    observed_d, obs_tail, base_tail = _d_tail(obs, baseline, percentile=percentile, direction=direction)

    combined = np.concatenate([obs, baseline])
    n_obs = obs.size
    rng = np.random.default_rng(seed)
    null_d_tails = np.empty(n_iter, dtype=float)

    for i in range(n_iter):
        permuted = rng.permutation(combined)
        perm_obs = permuted[:n_obs]
        perm_base = permuted[n_obs:]
        null_d_tails[i], _, _ = _d_tail(perm_obs, perm_base, percentile=percentile, direction=direction)

    p_value = float(np.mean(null_d_tails >= observed_d))
    effect_pass = bool(observed_d > effect_threshold)
    significance_pass = bool(p_value < alpha)

    return P4PermutationResult(
        statistic_name=statistic_name,
        observed_d_tail=float(observed_d),
        p_value=p_value,
        effect_pass=effect_pass,
        significance_pass=significance_pass,
        htsc_interest=bool(effect_pass and significance_pass),
        obs_tail_value=float(obs_tail),
        baseline_tail_value=float(base_tail),
        n_obs=int(obs.size),
        n_baseline=int(baseline.size),
        n_iter=int(n_iter),
        percentile=float(percentile),
        direction=direction,
        effect_threshold=float(effect_threshold),
        alpha=float(alpha),
        seed=seed,
        null_mean=float(np.mean(null_d_tails)),
        null_std=float(np.std(null_d_tails, ddof=1)) if n_iter > 1 else 0.0,
        null_q05=float(np.percentile(null_d_tails, 5)),
        null_q50=float(np.percentile(null_d_tails, 50)),
        null_q95=float(np.percentile(null_d_tails, 95)),
        notes="Interés fenomenológico, no confirmación. Requiere cortes/completeness equivalentes.",
    )


def summarize_p4_result(result: P4PermutationResult) -> str:
    status = "INTERÉS FENOMENOLÓGICO" if result.htsc_interest else "NO SUPERA P4"
    return (
        f"P4-v3.2.2 [{result.statistic_name}] → {status}\n"
        f"  D_tail observado: {result.observed_d_tail:.5f}\n"
        f"  p-value permutación: {result.p_value:.5f}\n"
        f"  efecto pasa: {result.effect_pass} (umbral={result.effect_threshold})\n"
        f"  significancia pasa: {result.significance_pass} (alpha={result.alpha})\n"
        f"  obs_tail={result.obs_tail_value:.5f} | baseline_tail={result.baseline_tail_value:.5f}\n"
        f"  n_obs={result.n_obs} | n_baseline={result.n_baseline} | n_iter={result.n_iter} | direction={result.direction}"
    )
