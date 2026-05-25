from pathlib import Path

import config as cfg


def test_versions_are_current():
    assert cfg.SIMULADOR_VERSION == "0.5.3"
    assert cfg.HIPOTESIS_VERSION == "3.1"


def test_output_dir_is_project_relative():
    out = Path(cfg.OUT_DIR)
    assert out.is_absolute()
    assert out.parent == cfg.PROJECT_ROOT


def test_noise_units_are_documented_in_config():
    assert isinstance(cfg.SIGMA_Z, float)
    assert isinstance(cfg.SIGMA_M, float)
    assert cfg.KL_N_BINS > 0
