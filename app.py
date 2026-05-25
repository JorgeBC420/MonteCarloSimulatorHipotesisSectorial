import streamlit as st
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from pathlib import Path
import sys
import os

# Configuración de página
st.set_page_config(page_title="SMCHS Dashboard", layout="wide", page_icon="📊")

# Asegurar que los módulos internos sean importables
sys.path.insert(0, os.path.dirname(__file__))

import config as cfg
try:
    from core.poblacion import inicializar_catalogo, construir_poblacion
    from analysis.estadistica import resumen_consola
    from figures.graficas import (
        fig1_distribucion_masa, fig2_exceso_por_z, fig3_ks_colas,
        fig4_correlacion_zm, fig5_delta_t, fig8_objetos_jwst,
        fig9_signal_vs_observed, fig10_distribucion_dt_signal
    )
except ImportError as e:
    st.error(f"Error al cargar módulos internos: {e}. Asegúrate de que la estructura de carpetas es correcta en GitHub.")
    st.stop()

# --- CACHE DE SIMULACIÓN ---
@st.cache_data
def run_simulation(n, seed, f_rem, t_mu):
    rng = np.random.default_rng(seed)
    catalogo = inicializar_catalogo(n, rng)
    
    pop_lcdm = construir_poblacion(catalogo, f_rem=0.0, t_mu=t_mu)
    pop_sect = construir_poblacion(catalogo, f_rem=f_rem, t_mu=t_mu)
    
    return pop_lcdm, pop_sect

# --- SIDEBAR / PARÁMETROS ---
st.sidebar.header("Configuración SMCHS")
n_sim = st.sidebar.slider("Número de objetos (N)", 10000, 120000, 30000, step=10000)
f_rem = st.sidebar.slider("Fracción de remanentes (f_rem)", 0.0, 0.08, 0.01, step=0.005)
t_mu = st.sidebar.slider("Madurez heredada μ (Gyr)", 0.1, 2.5, 0.7, step=0.1)
z_cut = st.sidebar.slider("Redshift de corte (z_cut)", 8.0, 15.0, 12.0, step=0.5)
seed = st.sidebar.number_input("Semilla Global", value=42)

st.title("📊 SMCHS: Monte Carlo Simulator for Hypothesis Sectorial")
st.markdown(f"**Versión Hipótesis:** {cfg.HIPOTESIS_VERSION} | **Versión Simulador:** {cfg.SIMULADOR_VERSION}")

if st.sidebar.button("Ejecutar Simulación"):
    with st.spinner("Simulando poblaciones..."):
        pop_base, pop_sect = run_simulation(int(n_sim), int(seed), float(f_rem), float(t_mu))
        
    # --- MÉTRICAS ---
    st.header("1. Métricas de Cola")
    col1, col2, col3, col4 = st.columns(4)
    
    # Cálculos rápidos para el dashboard
    masivas_base = (pop_base['log_m'] > cfg.LOG_M_THRESH) & (pop_base['z'] > z_cut) & pop_base['visible']
    masivas_sect = (pop_sect['log_m'] > cfg.LOG_M_THRESH) & (pop_sect['z'] > z_cut) & pop_sect['visible']
    
    ratio_r = np.sum(masivas_sect) / np.sum(masivas_base) if np.sum(masivas_base) > 0 else 0
    
    col1.metric("Ratio R (Exceso)", f"{ratio_r:.3f}x")
    col2.metric("Masivas Sect (z > z_cut)", int(np.sum(masivas_sect)))
    col3.metric("Δt_signal Q99", f"{np.percentile(pop_sect['dt_signal'], 99):.3f} Gyr")
    col4.metric("N Total", f"{n_sim:,}")

    # --- PESTAÑAS DE GRÁFICAS ---
    tab1, tab2, tab3, tab4 = st.tabs(["Masa y Redshift", "Análisis Temporal", "JWST / ALMA", "Estadística de Cola"])

    with tab1:
        st.subheader("Distribuciones de Masa y Exceso")
        # Las funciones de graficas.py guardan imágenes en cfg.OUT_DIR
        # Pasamos cfg.OUT_DIR para que sepa dónde guardar antes de que st.image las lea
        Path(cfg.OUT_DIR).mkdir(parents=True, exist_ok=True)
        
        fig1_distribucion_masa([pop_base, pop_sect], ["ΛCDM", "Sectorial"], [0, f_rem], cfg.OUT_DIR)
        st.image(os.path.join(cfg.OUT_DIR, "fig1_distribucion_masa.png"))
        
        fig2_exceso_por_z([pop_base, pop_sect], ["ΛCDM", "Sectorial"], [0, f_rem], cfg.OUT_DIR)
        st.image(os.path.join(cfg.OUT_DIR, "fig2_exceso_redshift.png"))

    with tab2:
        st.subheader("Predicción P2: Desacople Temporal")
        fig5_delta_t(pop_base, pop_sect, cfg.OUT_DIR)
        st.image(os.path.join(cfg.OUT_DIR, "fig5_delta_t.png"))
        
        fig9_signal_vs_observed(pop_base, pop_sect, cfg.OUT_DIR)
        st.image(os.path.join(cfg.OUT_DIR, "fig9_signal_vs_observed.png"))

    with tab3:
        st.subheader("Comparativa con Catálogos Reales")
        fig8_objetos_jwst(pop_base, pop_sect, cfg.OUT_DIR)
        st.image(os.path.join(cfg.OUT_DIR, "fig8_objetos_jwst.png"))
        
        st.info("Los puntos blancos representan objetos como JADES-GS-z14-0 superpuestos en la nube de simulación.")

    with tab4:
        st.subheader("Robustez Estadística")
        fig10_distribucion_dt_signal(pop_base, [pop_sect], [f_rem], cfg.OUT_DIR)
        st.image(os.path.join(cfg.OUT_DIR, "fig10_distribucion_dt_signal.png"))
        
        fig3_ks_colas(pop_base, pop_sect, cfg.OUT_DIR)
        st.image(os.path.join(cfg.OUT_DIR, "fig3_ks_colas.png"))

else:
    st.info("Ajusta los parámetros en la barra lateral y haz clic en 'Ejecutar Simulación'.")
    
    # Mostrar info de carga de datos si existe el CSV procesado
    csv_ready = Path(cfg.PROCESSED_DIR) / "jades_dr5_smchs_ready.csv"
    if csv_ready.exists():
        st.success(f"✅ Catálogo JADES procesado detectado ({csv_ready.name})")
    else:
        st.warning("⚠️ No se detecta catálogo JADES procesado. Ejecuta el loader primero si deseas ver datos reales.")

st.divider()
st.caption("SMCHS Dashboard | Basado en la Hipótesis de Transición Sectorial v3.1 | Jorge Eduardo Bravo Chaves")
