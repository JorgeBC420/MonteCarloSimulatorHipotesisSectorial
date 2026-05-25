import numpy as np
import pandas as pd

from baselines.external_loader import normalize_external_catalog
from baselines.metrics import tail_summary, compare_tail_to_baseline, observed_percentiles
from core.metric_dilution import f_rem_eff_z, gamma_from_w


def test_metric_dilution_monotonic_high_z_and_clipped():
    z = np.array([8.0, 12.0, 16.0])
    p = f_rem_eff_z(z, f_rem0=0.01, z_ref=12.0, w_rem=0.0, f_max=0.08)
    assert np.all(p >= 0)
    assert np.all(p <= 0.08)
    assert p[2] > p[1] > p[0]
    assert gamma_from_w(0.0) == 3.0


def test_construir_poblacion_metric_dilution_does_not_break_shape():
    import pytest
    pytest.importorskip("astropy")
    from core.poblacion import inicializar_catalogo, construir_poblacion
    cat = inicializar_catalogo(2000, np.random.default_rng(123))
    pop = construir_poblacion(cat, f_rem=0.01, metric_dilution=True, w_rem=0.0, z_ref=12.0, f_max=0.08)
    assert len(pop["z"]) == 2000
    assert pop["metric_dilution"] is True
    assert "dt_signal" in pop


def test_normalize_external_catalog_aliases():
    raw = pd.DataFrame({
        "redshift": [11.5, 12.2, 14.1],
        "logMstar": [9.1, 10.7, 11.0],
        "Muv": [-19.5, -20.2, -21.0],
    })
    df = normalize_external_catalog(raw, source_name="mock")
    assert {"z", "log_m_star", "MUV", "source"}.issubset(df.columns)
    assert len(df) == 3


def test_tail_summary_and_d_tail():
    base = pd.DataFrame({"z": [13, 13, 13], "log_m_star": [9.0, 9.5, 10.0], "MUV": [-18, -19, -20]})
    model = pd.DataFrame({"z": [13, 13, 13], "log_m_star": [10.0, 10.5, 11.0], "MUV": [-19, -20, -21]})
    s = tail_summary(model, z_cut=12, mass_cut=10.5)
    c = compare_tail_to_baseline(model, base, z_cut=12, mass_cut=10.5)
    assert s["n_z"] == 3
    assert c["D_tail_log_m"] > 0
    assert c["delta_P_massive"] >= 0


def test_observed_percentiles():
    obs = pd.DataFrame({"name": ["x"], "z": [13.0], "log_m_star": [10.5]})
    model = pd.DataFrame({"z": [13, 13, 13], "log_m_star": [9.0, 10.0, 11.0]})
    out = observed_percentiles(obs, model, z_cut=12)
    assert len(out) == 1
    assert 0 <= out["percentile_log_m_star"].iloc[0] <= 1
