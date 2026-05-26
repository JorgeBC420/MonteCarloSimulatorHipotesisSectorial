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
SIMULADOR_VERSION   = "0.5.7"
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

# ── Supresión UV por quenching (v0.5.7) ──────────────────────────────────────
# Corrige el sesgo de sobredetectabilidad de galaxias masivas quiescentes.
# Las galaxias con Z_obs > Z_QUENCH_THRESH Y log_m > M_QUENCH_THRESH reciben
# un desplazamiento positivo en M_UV (más débiles en UV → menos detectables).
#
# VALORES PRE-REGISTRADOS: no ajustar para mejorar fit.
# Ver documentacion/PRE_REGISTRO_PARAMETROS_SMCHS.md.
#
# Calibración contra distribución interna del simulador (N=50k, f_rem=5%, t_mu=1.5):
#   Z_met en escala proxy del simulador: p90≈0.19, p95≈0.22, p99≈0.29, max≈0.48
#   NOTA: esta escala NO es idéntica a Z/Z☉ absoluta. Es un proxy normalizado.
#
#   Umbral elegido (Z>0.18 & logM>9.5):
#   - Captura ~2.4% de la población total (no invasivo para ΛCDM base)
#   - Captura ~26% de remanentes con f_rem=5% (discriminativo para cola sectorial)
#   - Conservador: deja fuera ~74% de remanentes → no suprime toda la señal sectorial
#
# DELTA_UV_QUENCH = 2.5 mag: desplazamiento máximo UV. Valor conservador;
#   galaxias con SFR≈0 pueden ser 3-5 mag más débiles en NUV que star-forming
#   de igual masa (Salim et al. 2007). La sigmoide lo aplica de forma gradual.
#
# Estado: desactivado por defecto (quench_uv=False). Activar con --quench-uv.
QUENCH_UV_DEFAULT  = False
Z_QUENCH_THRESH    = 0.18    # proxy Z simulador; umbral de madurez química calibrado
M_QUENCH_THRESH    = 9.5     # log10(M★/M☉); umbral de masa para quenching
DELTA_UV_QUENCH    = 2.5     # mag; desplazamiento UV máximo (sigmoide → parcial)

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
    # ── Serie JADES clásica ──────────────────────────────────────────────────
    {"name": "JADES-GS-z14-0", "z": 14.18, "log_m": 8.7,  "Z_met": 0.55,
     "evidencia": "oxígeno (ALMA)", "nota": "M★ y Z son aproximados/ilustrativos"},
    {"name": "JADES-GS-z13-0", "z": 13.20, "log_m": 8.3,  "Z_met": 0.30,
     "evidencia": "espectroscopía NIRSpec", "nota": "récord previo JADES; 325 Myr post-BB"},
    {"name": "MoM-z14",        "z": 14.44, "log_m": 8.5,  "Z_met": 0.45,
     "evidencia": "C/N ratio",     "nota": "candidato/valor aproximado"},
    {"name": "JADES-GS-z7-QU", "z":  7.3,  "log_m": 9.5,  "Z_met": 0.60,
     "evidencia": "apagada (QU)",  "nota": "cadáver más antiguo conocido; ~700 Myr post-BB"},
    {"name": "GS-9209",        "z":  4.66, "log_m": 11.0, "Z_met": 0.70,
     "evidencia": "masiva-apagada","nota": "referencia tardía comparativa"},

    # ── Red Monsters (galaxias ultramasivas con polvo, RUBIES survey) ────────
    {"name": "RUBIES-EGS-49318", "z": 4.9, "log_m": 11.2, "Z_met": 0.65,
     "evidencia": "fotometría JWST NIRCam+MIRI", "nota": "Red Monster; masa ~Vía Láctea actual; muy enriquecida en polvo"},
    {"name": "RUBIES-EGS-55604", "z": 4.7, "log_m": 11.1, "Z_met": 0.62,
     "evidencia": "fotometría JWST", "nota": "Red Monster; formación estelar extremadamente eficiente"},
    {"name": "RUBIES-UDS-48139", "z": 4.6, "log_m": 11.0, "Z_met": 0.60,
     "evidencia": "fotometría JWST", "nota": "Red Monster; tercer miembro de la triada"},

    # ── Galaxias masivas apagadas (quiescent) extremas ────────────────────────
    {"name": "RUBIES-UDS-QG-z7", "z": 7.3,  "log_m": 10.2, "Z_met": 0.55,
     "evidencia": "espectroscopía NIRSpec", "nota": "galaxia masiva apagada más distante conocida; 15k M☉ a 700 Myr post-BB"},
    {"name": "ZF-UDS-7329",      "z": 3.2,  "log_m": 11.3, "Z_met": 0.72,
     "evidencia": "espectroscopía JWST", "nota": "estrellas ~11.5 Gyr antiguas; más masiva que Vía Láctea; conflicto con ΛCDM"},

    # ── Fusiones e hipermasivas tempranas ─────────────────────────────────────
    {"name": "Gz9p3",           "z": 9.3,  "log_m": 10.0, "Z_met": 0.40,
     "evidencia": "JWST NIRSpec merger", "nota": "fusión masiva; ~510 Myr post-BB; miles de millones de estrellas"},
    {"name": "Maisie Galaxy",   "z": 11.4, "log_m": 9.0,  "Z_met": 0.35,
     "evidencia": "espectroscopía confirmada", "nota": "~390 Myr post-BB; masiva y brillante para su época"},

    # ── Cosmic Vine (estructura filamentosa) ──────────────────────────────────
    {"name": "Cosmic Vine (nodo A)", "z": 7.7, "log_m": 10.8, "Z_met": 0.58,
     "evidencia": "JWST filamento 20 gal.", "nota": "Cosmic Vine; filamento de 13 Mly; masa total sistema ~260k M☉; nodo quiescent"},
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
