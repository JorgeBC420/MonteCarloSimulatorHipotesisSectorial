import math

import pytest

from extensions.hubble_tension import (
    DEFAULT_H0_CMB,
    DEFAULT_H0_LOCAL,
    epsilon_hubble,
    estimate_lambdas,
    implied_h0_local,
    lambda_from_f_dm,
    lambda_stability_report,
)


def test_epsilon_hubble_default_positive():
    eps = epsilon_hubble()
    assert eps > 0
    assert math.isclose(eps, DEFAULT_H0_LOCAL / DEFAULT_H0_CMB - 1.0)


def test_lambda_from_f_dm_roundtrip():
    estimate = lambda_from_f_dm(0.8)
    h0_back = implied_h0_local(0.8, estimate.lambda_param)
    assert math.isclose(h0_back, DEFAULT_H0_LOCAL, rel_tol=1e-12)
    assert 0 <= estimate.lambda_param <= 1


def test_lambda_rejects_invalid_f_dm():
    with pytest.raises(ValueError):
        lambda_from_f_dm(0.0)
    with pytest.raises(ValueError):
        lambda_from_f_dm(1.2)


def test_lambda_stability_report_stable_mock():
    estimates = estimate_lambdas([0.78, 0.80, 0.82], names=["a", "b", "c"])
    report = lambda_stability_report(estimates, threshold_cv=0.05)
    assert report.n == 3
    assert report.stable
    assert report.cv_lambda < 0.05


def test_lambda_stability_report_unstable_mock():
    estimates = estimate_lambdas([0.2, 0.8, 0.95], names=["a", "b", "c"])
    report = lambda_stability_report(estimates, threshold_cv=0.05, require_unit_interval=False)
    assert not report.stable
