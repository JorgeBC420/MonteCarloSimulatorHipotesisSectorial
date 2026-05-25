"""
figures/graficas.py — Generación de figuras

Fig 1: Distribución log M★ (sin/con filtro proxy de detectabilidad)
Fig 2: Fracción de galaxias masivas detectables por bin de z
Fig 3: CDF comparativa + KS-test (dos umbrales de z)
Fig 4: Estructura de correlación Z–M★ a alto z
Fig 5: Δt_i — desacople edades t_chem vs t_ΛCDM (Predicción P2)
Fig 6: Curva de sensibilidad P(anomalía) y KS-stat vs f_rem
Fig 7: Heatmap 2D sensibilidad (f_rem × t_previo)
Fig 8: Objetos observacionales JWST/ALMA en espacio de parámetros
Fig 9: Señal vs observado (dt_signal vs dt_observed)
Fig 10: Distribución completa y cola positiva de dt_signal
Fig 11: ΔP_tail, SNR_tail_Q99 y Q99(dt_signal) vs f_rem
"""

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import logging
from config import (
    Z_CUT, Z_MIN, Z_MAX, LOG_M_THRESH, PALETTE, OBS_OBJECTS,
)

logger = logging.getLogger(__name__)


def _save(fig: plt.Figure, path: str) -> None:
    fig.savefig(path, dpi=130, bbox_inches="tight")
    plt.close(fig)
    logger.info("Figura guardada: %s", path.split("/")[-1])


# ─────────────────────────────────────────────────────────────────────────────

def fig1_distribucion_masa(pops: list, labels: list, frems: list,
                           out: str) -> None:
    """Distribución de log M* con y sin filtro observacional."""
    fig, axes = plt.subplots(1, 2, figsize=(13, 5))
    fig.suptitle(f"Distribución de masa estelar a z > {Z_CUT:.0f}", fontsize=13, fontweight="bold")
    bins   = np.linspace(7.5, 13.5, 45)
    colors = [PALETTE["lcdm"], PALETTE["sect"], PALETTE["green"], PALETTE["amber"]]

    for ax, usar_filtro, titulo in zip(
        axes, [False, True], ["Sin filtro", "Con filtro proxy de detectabilidad"]
    ):
        for pop, lbl, fr, col in zip(pops, labels, frems, colors):
            mask = pop["z"] > Z_CUT
            if usar_filtro:
                mask &= pop["visible"]
            if mask.sum() == 0:
                continue
            ax.hist(pop["log_m"][mask], bins=bins, density=True,
                    alpha=0.55, label=f"{lbl}", color=col,
                    histtype="stepfilled", edgecolor=col, lw=1.2)
        ax.axvline(LOG_M_THRESH, color="k", lw=1.2, ls="--", alpha=0.55,
                   label=f"umbral {LOG_M_THRESH}")
        ax.set(xlabel="log₁₀(M★/M☉)", ylabel="PDF", title=titulo, xlim=(7.5, 13.5))
        ax.legend(fontsize=8, framealpha=0.4)

    plt.tight_layout()
    _save(fig, f"{out}/fig1_distribucion_masa.png")


def fig2_exceso_por_z(pops: list, labels: list, frems: list,
                      out: str) -> None:
    """Fracción de galaxias masivas detectables por bin de redshift."""
    fig, ax = plt.subplots(figsize=(11, 5))
    fig.suptitle("Fracción de galaxias masivas detectables por bin de z",
                 fontsize=12, fontweight="bold")
    zbins = np.arange(Z_MIN, Z_MAX + 1, 1.0)
    zc    = 0.5 * (zbins[:-1] + zbins[1:])
    colors = [PALETTE["lcdm"], PALETTE["sect"], PALETTE["green"], PALETTE["amber"]]

    for pop, lbl, fr, col in zip(pops, labels, frems, colors):
        mv   = pop["visible"] & (pop["log_m"] > LOG_M_THRESH)
        cnt, _ = np.histogram(pop["z"][mv],               bins=zbins)
        tot, _ = np.histogram(pop["z"][pop["visible"]],   bins=zbins)
        with np.errstate(invalid="ignore", divide="ignore"):
            frac = np.where(tot > 0, cnt / tot, np.nan)
        ls   = "-" if fr == 0.0 else "--"
        ax.plot(zc, frac, "o-", lw=2, ms=5, color=col, label=lbl)

    ax.axvline(Z_CUT, color="gray", ls=":", lw=1.2, alpha=0.7, label=f"z_cut={Z_CUT:.0f}")
    # Solo log-scale si hay valores positivos
    ydata = ax.get_lines()
    has_positive = any(
        np.any(np.array(line.get_ydata()) > 0)
        for line in ax.get_lines()
    )
    ax.set(xlabel="Redshift z", ylabel=f"Fracción (log M★>{LOG_M_THRESH}, visible)",
           xlim=(Z_MIN, Z_MAX))
    if has_positive:
        ax.set_yscale("log")
    ax.legend(fontsize=8, framealpha=0.4)
    plt.tight_layout()
    _save(fig, f"{out}/fig2_exceso_redshift.png")


def fig3_ks_colas(pop_base: dict, pop_sect: dict,
                  out: str) -> None:
    """CDF comparativa con KS-test para dos umbrales de redshift."""
    from scipy import stats as st

    fig, axes = plt.subplots(1, 2, figsize=(13, 5))
    fig.suptitle(f"Análisis KS de colas — f_rem={pop_sect['f_rem']*100:.1f}%",
                 fontsize=12, fontweight="bold")

    for ax, z_thr in zip(axes, [Z_CUT, Z_CUT + 2]):
        for pop, lbl, col in [
            (pop_base, "ΛCDM base",   PALETTE["lcdm"]),
            (pop_sect, f"Sectorial",  PALETTE["sect"]),
        ]:
            mask = pop["visible"] & (pop["z"] > z_thr)
            x    = np.sort(pop["log_m"][mask])
            if len(x) == 0:
                continue
            cdf = np.arange(1, len(x) + 1) / len(x)
            ax.plot(x, cdf, lw=2, label=f"{lbl}  (n={len(x):,})", color=col)

        ma = pop_base["visible"] & (pop_base["z"] > z_thr)
        mb = pop_sect["visible"] & (pop_sect["z"] > z_thr)
        xa, xb = pop_base["log_m"][ma], pop_sect["log_m"][mb]
        if len(xa) > 5 and len(xb) > 5:
            d, p = st.ks_2samp(xa, xb)
            ax.set_title(f"z > {z_thr:.0f}  |  KS D={d:.4f}  p={p:.3e}", fontsize=10)
        else:
            ax.set_title(f"z > {z_thr:.0f}  |  n insuficiente", fontsize=10)

        ax.axvline(LOG_M_THRESH, color="k", lw=1, ls="--", alpha=0.4)
        ax.set(xlabel="log₁₀(M★/M☉)", ylabel="CDF")
        ax.legend(fontsize=9, framealpha=0.4)

    plt.tight_layout()
    _save(fig, f"{out}/fig3_ks_colas.png")


def fig4_correlacion_zm(pop_base: dict, pop_sect: dict,
                        out: str) -> None:
    """Estructura de correlación Z–M★ a alto z."""
    from scipy import stats as st
    rng = np.random.default_rng(99)

    fig, axes = plt.subplots(1, 2, figsize=(13, 5))
    fig.suptitle(f"Correlación Z–M★ a z > {Z_CUT:.0f}  |  f_rem={pop_sect['f_rem']*100:.1f}%",
                 fontsize=12, fontweight="bold")

    for ax, pop, lbl in zip(axes,
                             [pop_base, pop_sect],
                             ["ΛCDM base", f"Sectorial f={pop_sect['f_rem']*100:.1f}%"]):
        mask = pop["visible"] & (pop["z"] > Z_CUT)
        zm, mm, zv = pop["Z_met"][mask], pop["log_m"][mask], pop["z"][mask]
        if len(zm) == 0:
            ax.set_title(f"{lbl}\nsin datos")
            continue
        idx = rng.choice(len(zm), min(2500, len(zm)), replace=False)
        sc  = ax.scatter(mm[idx], zm[idx], alpha=0.22, s=8,
                         c=zv[idx], cmap="plasma", vmin=Z_CUT, vmax=Z_MAX)
        plt.colorbar(sc, ax=ax, label="redshift z")
        r, p = st.pearsonr(mm, zm)
        ax.set_title(f"{lbl}\nPearson r={r:.3f}  p={p:.2e}", fontsize=10)
        ax.set(xlabel="log₁₀(M★/M☉)", ylabel="Metalicidad Z (frac. solar)")

    plt.tight_layout()
    _save(fig, f"{out}/fig4_correlacion_zm.png")


def fig5_delta_t(pop_base: dict, pop_sect: dict,
                 out: str) -> None:
    """
    Histograma de Δt_i = t_chem − t_ΛCDM (Predicción P2, v3.1).

    Δt_i > 0 → el objeto parece químicamente más viejo de lo que
    permite su redshift bajo ΛCDM. La cola positiva del modelo sectorial
    debería ser más pronunciada.
    """
    fig, ax = plt.subplots(figsize=(10, 5))

    for pop, lbl, col in [
        (pop_base, "ΛCDM base",   PALETTE["lcdm"]),
        (pop_sect, f"Sectorial f={pop_sect['f_rem']*100:.1f}%", PALETTE["sect"]),
    ]:
        mask = pop["visible"] & (pop["z"] > Z_CUT)
        dt   = pop["delta_t_obs"][mask]
        ax.hist(dt, bins=60, density=True, alpha=0.55,
                label=lbl, color=col, histtype="stepfilled",
                edgecolor=col, lw=1.2)

    ax.axvline(0, color="k", lw=1.2, ls="--", alpha=0.6, label="Δt_i = 0")
    ax.set(xlabel="Δt_i = t_chem − t_ΛCDM  (Gyr)",
           ylabel="PDF")
    ax.set_title(
        f"Desacople de edades a z > {Z_CUT:.0f}  —  Predicción P2 de la hipótesis v3.1\n"
        "Δt_i > 0 indica madurez química superior a la esperada por expansión",
        fontsize=10
    )
    ax.legend(fontsize=10, framealpha=0.4)
    plt.tight_layout()
    _save(fig, f"{out}/fig5_delta_t.png")


def fig6_scan_frems(scan_results: list, out: str) -> None:
    """Curva de sensibilidad: P(anomalía), ratio R y KS-stat vs f_rem."""
    frems_pct = [r["f_rem"] * 100 for r in scan_results]
    probs_b   = [r["p_base"]    for r in scan_results]
    probs_s   = [r["p_sect"]    for r in scan_results]
    ratios    = [r["ratio_R"]   for r in scan_results]
    ks_ds     = [r["ks_D"]      for r in scan_results]
    kls       = [r["kl_div"]    for r in scan_results]

    fig, axes = plt.subplots(1, 3, figsize=(15, 5))
    fig.suptitle("Análisis de sensibilidad: f_rem", fontsize=13, fontweight="bold")

    ax = axes[0]
    ax.plot(frems_pct, probs_b, "o--", color=PALETTE["lcdm"], lw=1.5, ms=5, label="ΛCDM base")
    ax.plot(frems_pct, probs_s, "o-",  color=PALETTE["sect"], lw=2,   ms=7, label="Sectorial")
    ax.fill_between(frems_pct, probs_b, probs_s, alpha=0.15, color=PALETTE["sect"])
    ax.set(xlabel="f_rem (%)", ylabel=f"P(log M★>{LOG_M_THRESH} | z>{Z_CUT:.0f}, visible)")
    ax.set_title("P(anomalía)", fontsize=10)
    ax.legend(fontsize=9)

    ax = axes[1]
    ax.plot(frems_pct, ratios, "s-", color=PALETTE["green"], lw=2, ms=7)
    ax.axhline(1.0, color="gray",  ls=":", lw=1, alpha=0.7, label="R=1 (ΛCDM)")
    ax.axhline(1.5, color="orange",ls="--",lw=1, alpha=0.7, label="R=1.5")
    ax.axhline(2.0, color="red",   ls="--",lw=1, alpha=0.7, label="R=2")
    ax.set(xlabel="f_rem (%)", ylabel="R = P_sect / P_ΛCDM")
    ax.set_title("Ratio R(f_rem)", fontsize=10)
    ax.legend(fontsize=8)

    ax = axes[2]
    ax.plot(frems_pct, ks_ds, "^-", color=PALETTE["lcdm"],  lw=2, ms=6, label="KS D")
    ax2 = ax.twinx()
    ax2.plot(frems_pct, kls,  "v--", color=PALETTE["amber"], lw=2, ms=6, label="KL div.", alpha=0.8)
    ax.axhline(0.1, color="gray", ls=":", lw=1, alpha=0.6)
    ax.set(xlabel="f_rem (%)", ylabel="KS statistic D")
    ax2.set_ylabel("KL divergencia", color=PALETTE["amber"])
    ax.set_title("Divergencia KS y KL vs f_rem", fontsize=10)
    ax.legend(loc="upper left",  fontsize=8)
    ax2.legend(loc="center left",fontsize=8)

    plt.tight_layout()
    _save(fig, f"{out}/fig6_scan_frems.png")


def fig7_heatmap(frems: np.ndarray, tprevs: np.ndarray,
                 ratio_grid: np.ndarray, out: str) -> None:
    """Heatmap 2D: ratio R(f_rem, t_previo)."""
    fig, ax = plt.subplots(figsize=(10, 7))
    im = ax.imshow(
        ratio_grid, origin="lower", aspect="auto",
        extent=[frems[0]*100, frems[-1]*100, tprevs[0], tprevs[-1]],
        cmap="hot", vmin=1.0, vmax=min(ratio_grid.max(), 8.0)
    )
    plt.colorbar(im, ax=ax, label="Ratio R = P_sect / P_ΛCDM")

    cs = ax.contour(
        frems * 100, tprevs, ratio_grid,
        levels=[1.5, 2.0, 3.0],
        colors=["white", "cyan", "lime"], linewidths=1.4
    )
    ax.clabel(cs, fmt="R=%.1f", fontsize=9, inline=True)

    ax.set(xlabel="f_rem (%)", ylabel="t_previo promedio (Gyr)")
    ax.set_title(
        f"Heatmap de sensibilidad: exceso log M★ > {LOG_M_THRESH}, z > {Z_CUT:.0f}\n"
        "Zona de interés: R ≈ 1.5–3 con f_rem pequeño (físicamente plausible)",
        fontsize=10
    )
    plt.tight_layout()
    _save(fig, f"{out}/fig7_heatmap.png")


def fig8_objetos_jwst(pop_base: dict, pop_sect: dict,
                      out: str) -> None:
    """
    Superpone objetos observacionales JWST/ALMA sobre la nube simulada.
    Permite ver en qué región del espacio de parámetros caen.
    """
    rng = np.random.default_rng(77)
    fig, ax = plt.subplots(figsize=(10, 6))

    for pop, lbl, col, al in [
        (pop_base, "ΛCDM base",   PALETTE["lcdm"],  0.12),
        (pop_sect, f"Sectorial f={pop_sect['f_rem']*100:.1f}%", PALETTE["sect"], 0.12),
    ]:
        mask = pop["visible"] & (pop["z"] > Z_CUT)
        zm, mm = pop["Z_met"][mask], pop["log_m"][mask]
        if len(zm) == 0:
            continue
        idx = rng.choice(len(zm), min(2000, len(zm)), replace=False)
        ax.scatter(pop["z"][mask][idx], mm[idx], alpha=al, s=7, color=col, label=lbl)

    # Objetos observacionales
    for obj in OBS_OBJECTS:
        ax.scatter(obj["z"], obj["log_m"], s=120, marker="*", zorder=5,
                   color="yellow", edgecolors="black", lw=0.8)
        ax.annotate(obj["name"], (obj["z"], obj["log_m"]),
                    textcoords="offset points", xytext=(5, 4),
                    fontsize=7.5, color="white",
                    bbox=dict(boxstyle="round,pad=0.15", fc="black", alpha=0.6))

    ax.axvline(Z_CUT, color="gray", ls=":", lw=1.2, alpha=0.6, label=f"z_cut={Z_CUT:.0f}")
    ax.axhline(LOG_M_THRESH, color="gray", ls="--", lw=1, alpha=0.5,
               label=f"log M★={LOG_M_THRESH}")
    ax.set(xlabel="Redshift z", ylabel="log₁₀(M★/M☉)", xlim=(Z_CUT-1, Z_MAX))
    ax.set_title(
        "Objetos JWST/ALMA (★) en el espacio z – log M★\n"
        "¿En qué región del parámetro espacio caen respecto a las poblaciones simuladas?",
        fontsize=10
    )
    ax.legend(fontsize=9, framealpha=0.5)
    plt.tight_layout()
    _save(fig, f"{out}/fig8_objetos_jwst.png")


# ─────────────────────────────────────────────────────────────────────────────
# FIGURAS NUEVAS v0.5.3 — Separación señal / ruido
# ─────────────────────────────────────────────────────────────────────────────

def fig9_signal_vs_observed(pop_base: dict, pop_sect: dict,
                             out: str) -> None:
    """
    Fig 9 (v0.5.3): scatter dt_signal vs dt_observed a z > Z_CUT.

    Si hay señal real, los puntos se alinean sobre la diagonal y=x.
    Si el exceso es solo ruido, la nube es caótica sin correlación.
    Los remanentes del modelo sectorial se marcan en color distinto.
    """
    rng = np.random.default_rng(55)
    fig, axes = plt.subplots(1, 2, figsize=(13, 5))
    fig.suptitle(
        f"Señal vs Observado — Δt_signal vs Δt_observed  (z > {Z_CUT:.0f})\n"
        "Alineación sobre y=x indica señal física real; dispersión horizontal es ruido",
        fontsize=11, fontweight="bold"
    )

    for ax, pop, lbl, col in zip(
        axes,
        [pop_base, pop_sect],
        ["ΛCDM base", f"Sectorial f={pop_sect['f_rem']*100:.1f}%"],
        [PALETTE["lcdm"], PALETTE["sect"]],
    ):
        mask = pop["visible"] & (pop["z"] > Z_CUT)
        sig  = pop["dt_signal"][mask]
        obs  = pop["dt_observed"][mask]
        rem  = pop["es_rem"][mask]

        if len(sig) == 0:
            ax.set_title(f"{lbl}\nsin datos")
            continue

        idx = rng.choice(len(sig), min(2000, len(sig)), replace=False)

        # No-remanentes
        nr = ~rem[idx]
        ax.scatter(sig[idx][nr], obs[idx][nr],
                   alpha=0.25, s=8, color=col, label="normal")

        # Remanentes (solo en modelo sectorial)
        if rem[idx].sum() > 0:
            ax.scatter(sig[idx][rem[idx]], obs[idx][rem[idx]],
                       alpha=0.7, s=25, color="yellow", edgecolors="black",
                       lw=0.5, label="remanente", zorder=5)

        # Diagonal de referencia
        lim = max(abs(sig[idx]).max(), abs(obs[idx]).max()) * 1.05
        ax.plot([-lim, lim], [-lim, lim], "k--", lw=1, alpha=0.5, label="y=x (sin ruido)")
        ax.axhline(0, color="gray", lw=0.7, alpha=0.4)
        ax.axvline(0, color="gray", lw=0.7, alpha=0.4)
        ax.set(xlabel="Δt_signal  (Gyr)", ylabel="Δt_observed  (Gyr)",
               title=lbl, xlim=(-lim, lim), ylim=(-lim, lim), aspect="equal")
        ax.legend(fontsize=8, framealpha=0.4)

    plt.tight_layout()
    _save(fig, f"{out}/fig9_signal_vs_observed.png")


def fig10_distribucion_dt_signal(pop_base: dict, pops_sect: list,
                                  frems: list, out: str) -> None:
    """
    Fig 10 (v0.5.3): distribución de dt_signal — SOLO cola positiva.

    Filtra dt_signal > 0 para mostrar únicamente objetos con madurez
    heredada real. Evita el pico dominante en cero (objetos no-remanentes)
    que oscurece la señal de interés.

    Panel izquierdo : toda la población (referencia)
    Panel derecho   : solo dt_signal > 0.05 Gyr (cola de interés)
    """
    fig, axes = plt.subplots(1, 2, figsize=(13, 5))
    fig.suptitle(
        f"Distribución de Δt_signal = t_chem_true − t_ΛCDM  (z > {Z_CUT:.0f})\n"
        "Señal física pura — izquierda: población completa  |  derecha: solo cola positiva (>0.05 Gyr)",
        fontsize=10, fontweight="bold"
    )
    colors = [PALETTE["lcdm"], PALETTE["green"], PALETTE["sect"], PALETTE["amber"], PALETTE["pink"]]

    for ax, filtrar, titulo in zip(
        axes,
        [False, True],
        ["Población completa (incl. no-remanentes)", "Cola positiva: Δt_signal > 0.05 Gyr"]
    ):
        # ΛCDM base
        mask_b = pop_base["visible"] & (pop_base["z"] > Z_CUT)
        sig_b  = pop_base["dt_signal"][mask_b]
        if filtrar: sig_b = sig_b[sig_b > 0.05]
        if len(sig_b) > 1:
            ax.hist(sig_b, bins=50, density=True, alpha=0.55,
                    label="ΛCDM base", color=colors[0],
                    histtype="stepfilled", edgecolor=colors[0], lw=1.2)

        # Sectoriales
        for pop, fr, col in zip(pops_sect, frems, colors[1:]):
            if fr == 0.0: continue
            mask = pop["visible"] & (pop["z"] > Z_CUT)
            sig  = pop["dt_signal"][mask]
            if filtrar: sig = sig[sig > 0.05]
            if len(sig) > 1:
                ax.hist(sig, bins=50, density=True, alpha=0.50,
                        label=f"f={fr*100:.1f}%", color=col,
                        histtype="step", linewidth=2)

        ax.axvline(0.5, color="gray", lw=1, ls="--", alpha=0.6, label="τ=0.5 Gyr")
        ax.set(xlabel="Δt_signal  (Gyr)", ylabel="PDF", title=titulo)
        ax.legend(fontsize=8, framealpha=0.4)

    plt.tight_layout()
    _save(fig, f"{out}/fig10_distribucion_dt_signal.png")


def fig11_snr_scan(scan_results: list, out: str) -> None:
    """
    Fig 11 (v0.5.3): métricas de COLA vs f_rem.

    Panel 1: ΔP_tail = P(Δt>τ)_sect − P(Δt>τ)_base
             Métrica estable incluso cuando P_base≈0.
    Panel 2: SNR_tail_Q99 = ΔQ99 / σ_ruido
             Cuántas sigmas de ruido supera el engrosamiento de la cola.
    Panel 3: Q99(dt_signal) base vs sectorial
             Muestra el desplazamiento absoluto de la cola extrema.
    """
    frems_pct   = [r["f_rem"] * 100      for r in scan_results]
    delta_p     = [r.get("delta_p_tail", r["p_tail_sect"] - r["p_tail_base"]) for r in scan_results]
    snr_tails   = [r["snr_tail_q99"]     for r in scan_results]
    q99_base    = [r["q99_dt_signal_sect"] - r["delta_q99"] for r in scan_results]
    q99_sect    = [r["q99_dt_signal_sect"] for r in scan_results]
    p_tail_b    = [r["p_tail_base"]       for r in scan_results]
    p_tail_s    = [r["p_tail_sect"]       for r in scan_results]

    fig, axes = plt.subplots(1, 3, figsize=(15, 5))
    fig.suptitle(
        "Métricas de cola Δt_signal vs f_rem  (v0.5.3)\n"
        "Estimador correcto para señales raras: no mediana, sino cola estadística",
        fontsize=10, fontweight="bold"
    )

    # Panel 1: tail_ratio
    ax = axes[0]
    ax.plot(frems_pct, tail_ratios, "o-", color=PALETTE["sect"], lw=2, ms=7)
    ax.axhline(1.0, color="gray",  ls=":", lw=1,   label="ratio=1 (sin efecto)")
    ax.axhline(1.5, color="orange",ls="--",lw=1.2, label="ratio=1.5")
    ax.axhline(2.0, color="red",   ls="--",lw=1.2, label="ratio=2")
    ax.fill_between(frems_pct, 1.0, tail_ratios,
                    where=[r > 1 for r in tail_ratios],
                    alpha=0.15, color=PALETTE["sect"])
    ax.set(xlabel="f_rem (%)", ylabel="tail_ratio")
    ax.set_title("P(Δt>τ) sectorial / P(Δt>τ) base\n(τ = 0.5 Gyr)", fontsize=9)
    ax.legend(fontsize=8)

    # Panel 2: SNR_tail
    ax = axes[1]
    ax.plot(frems_pct, snr_tails, "s-", color=PALETTE["green"], lw=2, ms=7)
    ax.axhline(0,   color="gray",   ls=":", lw=0.8)
    ax.axhline(1.0, color="orange", ls="--",lw=1.2, label="SNR=1")
    ax.axhline(2.0, color="red",    ls="--",lw=1.2, label="SNR=2 (robusto)")
    ax.fill_between(frems_pct, 1.0, snr_tails,
                    where=[s > 1 for s in snr_tails],
                    alpha=0.15, color=PALETTE["green"])
    ax.set(xlabel="f_rem (%)", ylabel="SNR_tail_Q99")
    ax.set_title("SNR_tail = ΔQ99 / σ_ruido\n> 1 → señal supera ruido de metalicidad", fontsize=9)
    ax.legend(fontsize=8)

    # Panel 3: Q99 base vs sectorial
    ax = axes[2]
    ax.plot(frems_pct, q99_base, "o--", color=PALETTE["lcdm"],  lw=1.5, ms=5,
            label="Q99 base (ΛCDM)")
    ax.plot(frems_pct, q99_sect, "o-",  color=PALETTE["sect"],  lw=2,   ms=7,
            label="Q99 sect")
    ax.fill_between(frems_pct, q99_base, q99_sect, alpha=0.15, color=PALETTE["sect"])
    ax.set(xlabel="f_rem (%)", ylabel="Q99(dt_signal) Gyr")
    ax.set_title("Desplazamiento de cola extrema\nΔQ99 = Q99_sect − Q99_base", fontsize=9)
    ax.legend(fontsize=8)

    plt.tight_layout()
    _save(fig, f"{out}/fig11_snr_detectabilidad.png")
