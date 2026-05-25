import tempfile
from pathlib import Path

import pytest


def test_fig11_no_name_error():
    """Regresión: fig11 debe graficar ΔP_tail y no usar tail_ratios inexistente."""
    pytest.importorskip("matplotlib")
    import matplotlib
    matplotlib.use("Agg")
    from figures.graficas import fig11_snr_scan

    scan_results = [
        {
            "f_rem": 0.0,
            "delta_p_tail": 0.0,
            "p_tail_base": 0.0,
            "p_tail_sect": 0.0,
            "snr_tail_q99": 0.0,
            "q99_dt_signal_sect": 0.0,
            "delta_q99": 0.0,
        },
        {
            "f_rem": 0.01,
            "delta_p_tail": 0.05,
            "p_tail_base": 0.0,
            "p_tail_sect": 0.05,
            "snr_tail_q99": 2.5,
            "q99_dt_signal_sect": 1.2,
            "delta_q99": 1.2,
        },
    ]

    with tempfile.TemporaryDirectory() as tmp:
        fig11_snr_scan(scan_results, tmp)
        assert (Path(tmp) / "fig11_snr_detectabilidad.png").exists()


def test_schechter_no_nan_small_bin():
    """Regresión: bins pequeños no deben generar median([]) ni NaN silencioso."""
    np = pytest.importorskip("numpy")
    pytest.importorskip("astropy")
    from core.cosmologia import schechter_sample

    rng = np.random.default_rng(0)
    mstar_z = np.full(5, 10.0)
    result = schechter_sample(5, mstar_z, -1.35, rng)

    assert len(result) == 5
    assert not np.any(np.isnan(result))
