# -*- coding: utf-8 -*-
import pandas as pd

from baselines.tng_loader import normalize_tng_dataframe
from baselines.simba_loader import normalize_simba_dataframe


def test_normalize_tng_dataframe_local():
    df = pd.DataFrame({"id": [1], "redshift": [12.0], "stellar_mass": [1e9], "MUV": [-19.0]})
    out = normalize_tng_dataframe(df)
    assert out.loc[0, "source"] == "IllustrisTNG"
    assert out.loc[0, "z"] == 12.0
    assert abs(out.loc[0, "log_m_star"] - 9.0) < 1e-6
    assert out.loc[0, "MUV"] == -19.0


def test_normalize_simba_dataframe_local():
    df = pd.DataFrame({"id": [1], "z": [12.0], "stellar_mass": [1e9], "MUV": [-18.0]})
    out = normalize_simba_dataframe(df)
    assert out.loc[0, "source"] == "SIMBA"
    assert out.loc[0, "z"] == 12.0
    assert abs(out.loc[0, "log_m_star"] - 9.0) < 1e-6
    assert out.loc[0, "MUV"] == -18.0
