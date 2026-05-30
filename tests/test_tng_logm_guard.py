import math
import numpy as np
import pandas as pd
from baselines.tng_loader import normalize_tng_dataframe

def test_tng_api_mass_stars_conversion():
    df = pd.DataFrame({
        "id": [0], "z": [14.989], "mass_stars": [0.001643],
        "mass_dm": [1.33445], "mass_gas": [0.224688],
        "sfr": [0.817404], "len_stars": [2], "snapshot": [1],
    })
    out = normalize_tng_dataframe(df, h=0.6774)
    expected = math.log10(0.001643 * 1e10 / 0.6774)
    assert abs(out.loc[0, "log_m_star"] - expected) < 1e-6

def test_empty_log_column_falls_back_to_mass_stars():
    df = pd.DataFrame({
        "id": [0], "z": [14.989], "log_m_star": [np.nan],
        "mass_stars": [0.001643], "sfr": [0.817404], "snapshot": [1],
    })
    out = normalize_tng_dataframe(df, h=0.6774)
    expected = math.log10(0.001643 * 1e10 / 0.6774)
    assert abs(out.loc[0, "log_m_star"] - expected) < 1e-6

def test_mass_log_msun_is_not_used_as_stellar_mass():
    df = pd.DataFrame({
        "id": [0], "z": [14.989], "mass_log_msun": [10.36],
        "mass_stars": [0.001643], "sfr": [0.817404], "snapshot": [1],
    })
    out = normalize_tng_dataframe(df, h=0.6774)
    expected = math.log10(0.001643 * 1e10 / 0.6774)
    assert abs(out.loc[0, "log_m_star"] - expected) < 1e-6
