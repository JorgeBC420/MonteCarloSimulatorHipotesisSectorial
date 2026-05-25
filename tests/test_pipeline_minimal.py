import pytest

np = pytest.importorskip("numpy")
pytest.importorskip("astropy")

from core.poblacion import inicializar_catalogo, construir_poblacion
from analysis.estadistica import metricas_completas


def test_minimal_pipeline_runs():
    rng = np.random.default_rng(123)
    cat = inicializar_catalogo(300, rng)
    base = construir_poblacion(cat, f_rem=0.0, t_mu=0.7)
    sect = construir_poblacion(cat, f_rem=0.02, t_mu=0.7)
    m = metricas_completas(base, sect, z_cut=10)
    assert "delta_p_tail" in m
    assert "snr_tail_q99" in m
    assert base["z"].shape == sect["z"].shape
