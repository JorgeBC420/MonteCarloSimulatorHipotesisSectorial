"""Demo CLI independiente para Apéndice C / lambda-Hubble.

Ejecutar desde la raíz del repo:

    python -m extensions.run_lambda_demo

No modifica outputs del core SMCHS. Solo imprime una demostración con sistemas
mock para validar la ruta futura de integración.
"""

from __future__ import annotations

from extensions.hubble_tension import estimate_lambdas, lambda_stability_report
from extensions.smbh_kinematics import batch_probe_summaries


def main() -> None:
    mock_systems = [
        {
            "system_name": "mock_runaway_smbh_A",
            "v_ejec_kms": 1600.0,
            "radius_kpc": 60.0,
            "m_baryonic_msun": 2.5e13,
            "halo_model": "point_mass",
        },
        {
            "system_name": "mock_runaway_smbh_B",
            "v_ejec_kms": 1400.0,
            "radius_kpc": 45.0,
            "m_baryonic_msun": 1.5e13,
            "halo_model": "point_mass",
        },
        {
            "system_name": "mock_runaway_smbh_C",
            "v_ejec_kms": 1800.0,
            "radius_kpc": 70.0,
            "m_baryonic_msun": 4.0e13,
            "halo_model": "point_mass",
        },
    ]

    summaries = batch_probe_summaries(mock_systems)
    f_values = [float(s["f_dm_eff"]) for s in summaries]
    names = [str(s.get("system_name", f"system_{i}")) for i, s in enumerate(summaries)]
    estimates = estimate_lambdas(f_values, names=names)
    report = lambda_stability_report(estimates, threshold_cv=0.25)

    print("SMCHS extensions demo — Apéndice C / λ-Hubble")
    print("Nota: datos mock, no observacionales.\n")
    for s, e in zip(summaries, estimates):
        print(f"{s.get('system_name')}: f_DM_eff={s['f_dm_eff']:.3f}, lambda={e.lambda_param:.3f}")
    print("\nReporte estabilidad:")
    for key, value in report.as_dict().items():
        print(f"  {key}: {value}")


if __name__ == "__main__":
    main()
