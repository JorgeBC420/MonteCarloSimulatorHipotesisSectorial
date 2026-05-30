import math
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
    assert out.loc[0, "mass_stars_msun"] > 0
    assert out.loc[0, "mass_dm_msun"] > out.loc[0, "mass_stars_msun"]
