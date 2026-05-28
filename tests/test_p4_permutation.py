# -*- coding: utf-8 -*-
import numpy as np

from analysis.p4_permutation import permutation_test_d_tail


def test_p4_detects_large_high_tail_shift():
    rng = np.random.default_rng(123)
    baseline = rng.normal(loc=9.0, scale=0.25, size=400)
    obs = rng.normal(loc=9.35, scale=0.25, size=120)
    result = permutation_test_d_tail(obs, baseline, effect_threshold=0.15, n_iter=1000, percentile=95, direction="high", seed=1)
    assert result.observed_d_tail > 0
    assert result.effect_pass is True
    assert result.p_value < 0.05
    assert result.htsc_interest is True


def test_p4_does_not_trigger_for_same_distribution():
    rng = np.random.default_rng(456)
    baseline = rng.normal(loc=9.0, scale=0.25, size=400)
    obs = rng.normal(loc=9.0, scale=0.25, size=120)
    result = permutation_test_d_tail(obs, baseline, effect_threshold=0.15, n_iter=1000, percentile=95, direction="high", seed=2)
    assert result.htsc_interest is False


def test_p4_low_direction_for_muv_bright_tail():
    rng = np.random.default_rng(789)
    baseline = rng.normal(loc=-18.5, scale=0.4, size=400)
    obs = rng.normal(loc=-19.3, scale=0.4, size=120)
    result = permutation_test_d_tail(obs, baseline, effect_threshold=0.5, n_iter=1000, percentile=95, direction="low", seed=3)
    assert result.observed_d_tail > 0
    assert result.effect_pass is True
    assert result.p_value < 0.05
