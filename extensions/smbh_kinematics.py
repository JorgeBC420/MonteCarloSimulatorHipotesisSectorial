"""
extensions/smbh_kinematics.py

Módulo auxiliar independiente para el Apéndice C de la HTSC/SMCHS:
agujeros negros supermasivos fugitivos como sondas dinámicas de masa no visible.

IMPORTANTE
---------
Este módulo NO está conectado al core Monte Carlo del SMCHS. Es una base
fenomenológica ligera para calcular órdenes de magnitud y preparar futuros
contrastes con datos observacionales. No ejecuta N-body, no resuelve
hidrodinámica y no demuestra materia oscura; estima la masa dinámica mínima
requerida bajo modelos de potencial simples.

Unidades usadas
---------------
- velocidad: km/s
- distancia/radio: kpc
- masa: M_sun
- potencial específico: (km/s)^2

Constante:
    G = 4.30091e-6 kpc (km/s)^2 / M_sun
"""

from __future__ import annotations

from dataclasses import dataclass
from math import log
from typing import Literal, Optional

import numpy as np

G_KPC_KMS2_MSUN = 4.30091e-6
HaloModel = Literal["point_mass", "singular_isothermal", "nfw"]


@dataclass(frozen=True)
class BaryonicMassBudget:
    """Presupuesto bariónico visible del sistema.

    Parameters
    ----------
    stellar_mass_msun:
        Masa estelar visible M_* en masas solares.
    gas_mass_msun:
        Masa de gas visible M_gas en masas solares.
    black_hole_mass_msun:
        Masa del agujero negro expulsado M_BH en masas solares.
    """

    stellar_mass_msun: float
    gas_mass_msun: float
    black_hole_mass_msun: float

    @property
    def total_msun(self) -> float:
        total = self.stellar_mass_msun + self.gas_mass_msun + self.black_hole_mass_msun
        if total < 0:
            raise ValueError("La masa bariónica total no puede ser negativa.")
        return float(total)


@dataclass(frozen=True)
class FugitiveSMBHProbe:
    """Sonda dinámica simple basada en un SMBH fugitivo.

    La clase implementa tres niveles de aproximación:

    1. Energía cinética específica: Phi_kin = 0.5 v_ejec^2.
    2. Masa dinámica mínima puntual: M(<r) ~ v^2 r / G.
    3. Perfiles opcionales: isothermal y NFW simplificado.

    Para una publicación o análisis real, la trayectoria 3D, el potencial de la
    galaxia anfitriona y la masa bariónica deben estimarse con observaciones y
    rangos de incertidumbre. Esta clase solo entrega una base reproducible.
    """

    v_ejec_kms: float
    radius_kpc: float
    halo_model: HaloModel = "point_mass"
    nfw_scale_radius_kpc: Optional[float] = None

    def __post_init__(self) -> None:
        if self.v_ejec_kms <= 0:
            raise ValueError("v_ejec_kms debe ser positivo.")
        if self.radius_kpc <= 0:
            raise ValueError("radius_kpc debe ser positivo.")
        if self.halo_model == "nfw":
            if self.nfw_scale_radius_kpc is None or self.nfw_scale_radius_kpc <= 0:
                raise ValueError("nfw_scale_radius_kpc debe ser positivo para halo_model='nfw'.")

    def kinetic_specific_energy(self) -> float:
        """Energía cinética específica 0.5 v^2 en (km/s)^2."""
        return 0.5 * float(self.v_ejec_kms) ** 2

    def infer_dynamic_mass_msun(self) -> float:
        """Infiere una masa dinámica característica en M_sun.

        Notas por modelo:
        - point_mass: M ~ v^2 r / G. Estimador mínimo de orden de magnitud.
        - singular_isothermal: usa v_c ~ v_ejec/sqrt(2), M(<r)=v_c^2 r/G.
        - nfw: invierte una forma acumulada simplificada M(<r) = M200 * F(x)/F(c),
          usando r_s como escala y c_eff = r/r_s. No reemplaza un ajuste NFW real.
        """
        v2 = float(self.v_ejec_kms) ** 2
        r = float(self.radius_kpc)

        if self.halo_model == "point_mass":
            return v2 * r / G_KPC_KMS2_MSUN

        if self.halo_model == "singular_isothermal":
            vc2 = 0.5 * v2
            return vc2 * r / G_KPC_KMS2_MSUN

        if self.halo_model == "nfw":
            rs = float(self.nfw_scale_radius_kpc)
            x = max(r / rs, 1e-9)
            # Factor acumulado NFW: F(x)=ln(1+x)-x/(1+x)
            f_x = log(1.0 + x) - x / (1.0 + x)
            # Estimador de masa dentro de r usando v^2 r/G y corrigiendo por F(x)/x.
            # Es heurístico: útil para sensibilidad, no para publicación sin ajuste.
            correction = max(f_x / max(x, 1e-9), 1e-9)
            return (v2 * r / G_KPC_KMS2_MSUN) / correction

        raise ValueError(f"halo_model no soportado: {self.halo_model}")

    def non_visible_mass_msun(self, baryonic_mass_msun: float) -> float:
        """M_no_visible = max(M_dinamica - M_barionica, 0)."""
        if baryonic_mass_msun < 0:
            raise ValueError("baryonic_mass_msun no puede ser negativa.")
        return max(self.infer_dynamic_mass_msun() - float(baryonic_mass_msun), 0.0)

    def f_dm_eff(self, baryonic_mass_msun: float) -> float:
        """f_DM^eff = (M_dinamica - M_barionica) / M_dinamica.

        Devuelve 0 si M_dinamica <= M_barionica.
        """
        m_dyn = self.infer_dynamic_mass_msun()
        if m_dyn <= 0:
            raise ValueError("Masa dinámica no positiva; revise los parámetros.")
        return self.non_visible_mass_msun(baryonic_mass_msun) / m_dyn

    def summary(self, baryonic_mass_msun: float) -> dict[str, float | str]:
        """Resumen serializable para CSV/dashboard/tests."""
        m_dyn = self.infer_dynamic_mass_msun()
        m_no_visible = max(m_dyn - float(baryonic_mass_msun), 0.0)
        return {
            "halo_model": self.halo_model,
            "v_ejec_kms": float(self.v_ejec_kms),
            "radius_kpc": float(self.radius_kpc),
            "phi_kinetic_kms2": self.kinetic_specific_energy(),
            "m_dynamic_msun": m_dyn,
            "m_baryonic_msun": float(baryonic_mass_msun),
            "m_non_visible_msun": m_no_visible,
            "f_dm_eff": 0.0 if m_dyn <= 0 else m_no_visible / m_dyn,
        }


def infer_f_dm_from_observables(
    v_ejec_kms: float,
    radius_kpc: float,
    baryonic_mass_msun: float,
    halo_model: HaloModel = "point_mass",
    nfw_scale_radius_kpc: Optional[float] = None,
) -> float:
    """Función de conveniencia para estimar f_DM^eff desde observables mínimos."""
    probe = FugitiveSMBHProbe(
        v_ejec_kms=v_ejec_kms,
        radius_kpc=radius_kpc,
        halo_model=halo_model,
        nfw_scale_radius_kpc=nfw_scale_radius_kpc,
    )
    return probe.f_dm_eff(baryonic_mass_msun)


def batch_probe_summaries(rows: list[dict]) -> list[dict]:
    """Procesa una lista de sistemas mock/observacionales.

    Cada fila debe contener al menos:
        v_ejec_kms, radius_kpc, m_baryonic_msun
    Opcionalmente:
        halo_model, nfw_scale_radius_kpc, system_name
    """
    summaries: list[dict] = []
    for row in rows:
        probe = FugitiveSMBHProbe(
            v_ejec_kms=float(row["v_ejec_kms"]),
            radius_kpc=float(row["radius_kpc"]),
            halo_model=row.get("halo_model", "point_mass"),
            nfw_scale_radius_kpc=row.get("nfw_scale_radius_kpc"),
        )
        summary = probe.summary(float(row["m_baryonic_msun"]))
        if "system_name" in row:
            summary["system_name"] = row["system_name"]
        summaries.append(summary)
    return summaries
