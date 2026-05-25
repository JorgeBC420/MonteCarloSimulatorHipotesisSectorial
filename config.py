"""
config.py — Parámetros globales
Simulador Monte Carlo de Hipótesis Sectorial (SMCHS) v0.5.3
Implementa: Hipótesis de Transición Sectorial Cosmológica v3.1

Distinción de versiones:
    Hipótesis: v3.1   (documento teórico)
    Simulador: v0.5.3 (este código)
"""

from pathlib import Path
import numpy as np

# ── Versión ───────────────────────────────────────────────────────────────────
SIMULADOR_VERSION   = "0.5.3"
HIPOTESIS_VERSION   = "3.1"
SIMULADOR_NOMBRE    = "SMCHS"          # Simulador Monte Carlo de Hipótesis Sectorial
SIMULADOR_NOMBRE_EN = "MCSSH"          # Monte Carlo Simulator for the Sectorial Hypothesis

# ── Paths ─────────────────────────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parent
OUT_DIR = str(PROJECT_ROOT / "outputs")
LOG_DIR = str(PROJECT_ROOT / "logs")
DATA_DIR = PROJECT_ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"
RAW_DIR.mkdir(parents=True, exist_ok=True)

# ── Reproducibilidad ─────────────────────────────────────────────────────────
SEED = 42
# Nota: las semillas derivadas usan hashlib.sha256, no hash() de Python.
# hash() varía entre sesiones por PYTHONHASHSEED. SHA-256 es siempre estable.

# ── Población ────────────────────────────────────────────────────────────────
N            = 120_000       # objetos por corrida principal
Z_MIN        = 5.0
Z_MAX        = 17.0
Z_CUT        = 12.0          # umbral "alto redshift" para análisis de anomalías

# ── Hipótesis sectorial ──────────────────────────────────────────────────────
F_REM_DEFAULT  = 0.01        # fracción de remanentes (default 1%)
T_PREV_MU      = 0.7         # media log-normal de Δt_heredada (Gyr)
T_PREV_SIG     = 0.45        # sigma log-normal de Δt_heredada (adimensional)

# ── Función de masa Schechter ────────────────────────────────────────────────
MSTAR_LOG10_0  = 10.6        # M* característica a z=8, en log10(M★/M☉)
MSTAR_EVO_LAMB = 0.18        # evolución con z: M*(z) = M*0 − λ·(z−8), en dex por z
SCHECHTER_A    = -1.35       # pendiente faint-end
SCHECHTER_Z_BINS = np.array([5, 7, 9, 11, 13, 15, 17], dtype=float)

# ── Observables proxy ────────────────────────────────────────────────────────
Z_INICIAL   = 0.02           # metalicidad inicial, fracción solar lineal (Z/Z☉)
ALPHA_Z     = 0.18           # tasa proxy de enriquecimiento químico, fracción solar por log(1+t/Gyr)
SIGMA_Z     = 0.05           # ruido intrínseco/observacional de metalicidad, fracción solar lineal (Z/Z☉)

BETA_M      = 0.55           # tasa proxy de crecimiento de masa, dex por Gyr efectivo
SIGMA_M     = 0.25           # ruido intrínseco/observacional de masa, dex en log10(M★/M☉)

# Magnitud UV proxy (calibrada: M_UV ≈ −19 para log M★=10)
MUV_SLOPE   = -2.0           # pendiente M_UV vs log10(M★)
MUV_OFFSET  = -17.0          # M_UV en log M★=9

# ── Filtro proxy de detectabilidad ───────────────────────────────────────────
# No es un modelo instrumental de JWST. Es un proxy de sesgo por luminosidad.
MUV_LIM_BASE  = -17.0        # magnitud límite a z=8 (AB mag proxy)
MUV_LIM_SLOPE =  0.25        # umbral sube 0.25 mag por unidad de z

# ── Análisis de sensibilidad ─────────────────────────────────────────────────
FREMS_SCAN     = [0.0, 0.003, 0.005, 0.01, 0.02, 0.03, 0.05, 0.08]
HEATMAP_FREMS  = np.linspace(0.0,  0.08, 10)
HEATMAP_TPREVS = np.linspace(0.1,  2.5,  10)
N_HEATMAP      = 18_000      # objetos por fila del heatmap
KL_N_BINS      = 40          # bins para divergencia KL en log10(M★)

# ── Umbral de anomalía ───────────────────────────────────────────────────────
LOG_M_THRESH  = 10.5         # log10(M★/M☉) umbral para "masiva"
Z_MET_THRESH  = 0.40         # metalicidad mínima para "madura", fracción solar
DT_TAIL_TAU   = 0.5          # Gyr — umbral de madurez significativa para P(Δt_signal > τ)

# ── Objetos observacionales de referencia ────────────────────────────────────
# ADVERTENCIA: valores ILUSTRATIVOS aproximados, no base de datos calibrada.
# Las masas y metalicidades a z>10 tienen grandes incertidumbres.
# No usar como ground truth. Consultar papers originales citados en README.
OBS_OBJECTS = [
    {"name": "JADES-GS-z14-0", "z": 14.18, "log_m": 8.7,  "Z_met": 0.55,
     "evidencia": "oxígeno (ALMA)", "nota": "M★ y Z son aproximados/ilustrativos"},
    {"name": "MoM-z14",        "z": 14.44, "log_m": 8.5,  "Z_met": 0.45,
     "evidencia": "C/N ratio",     "nota": "candidato/valor aproximado"},
    {"name": "JADES-GS-z7-QU", "z":  7.3,  "log_m": 9.5,  "Z_met": 0.60,
     "evidencia": "apagada",       "nota": "apagamiento precoz; valores proxy"},
    {"name": "GS-9209",        "z":  4.66, "log_m": 11.0, "Z_met": 0.70,
     "evidencia": "masiva-apagada","nota": "referencia tardía comparativa"},
]

# ── Estética ─────────────────────────────────────────────────────────────────
PALETTE = {
    "lcdm":  "#378ADD",
    "sect":  "#D85A30",
    "green": "#1D9E75",
    "amber": "#BA7517",
    "gray":  "#888780",
    "pink":  "#D4537E",
}
