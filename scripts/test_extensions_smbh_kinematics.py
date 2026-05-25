import math

import pytest

from extensions.smbh_kinematics import (
    BaryonicMassBudget,
    FugitiveSMBHProbe,
    batch_probe_summaries,
    infer_f_dm_from_observables,
)


def test_baryonic_mass_budget_total():
    budget = BaryonicMassBudget(1.0e11, 2.0e10, 2.0e7)
    assert math.isclose(budget.total_msun, 1.2002e11)


def test_fugitive_smbh_probe_point_mass_positive():
    probe = FugitiveSMBHProbe(v_ejec_kms=1600.0, radius_kpc=60.0)
    m_dyn = probe.infer_dynamic_mass_msun()
    assert m_dyn > 0
    assert probe.kinetic_specific_energy() == pytest.approx(0.5 * 1600.0**2)


def test_f_dm_eff_bounds():
    f = infer_f_dm_from_observables(
        v_ejec_kms=1600.0,
        radius_kpc=60.0,
        baryonic_mass_msun=1.0e12,
    )
    assert 0.0 <= f <= 1.0


def test_no_invisible_mass_when_baryons_exceed_dynamic():
    probe = FugitiveSMBHProbe(v_ejec_kms=1000.0, radius_kpc=10.0)
    m_dyn = probe.infer_dynamic_mass_msun()
    assert probe.f_dm_eff(m_dyn * 2.0) == 0.0


def test_nfw_requires_scale_radius():
    with pytest.raises(ValueError):
        FugitiveSMBHProbe(v_ejec_kms=1200.0, radius_kpc=50.0, halo_model="nfw")


def test_batch_probe_summaries():
    rows = [
        {"system_name": "x", "v_ejec_kms": 1000, "radius_kpc": 20, "m_baryonic_msun": 1e11},
        {"system_name": "y", "v_ejec_kms": 1500, "radius_kpc": 30, "m_baryonic_msun": 2e11},
    ]
    summaries = batch_probe_summaries(rows)
    assert len(summaries) == 2
    assert summaries[0]["system_name"] == "x"
    assert "f_dm_eff" in summaries[0]
