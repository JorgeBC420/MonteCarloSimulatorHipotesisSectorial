#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
smchs_log_analyzer.py — Analizador de corridas SMCHS
SMCHS v0.5.7 / Hipótesis Sectorial v3.2.1

Extrae métricas de:
  - ZIPs archivados (smchs_run_*.zip) en un directorio
  - Archivos .log / .txt sueltos
  - Combinaciones: varios ZIPs, globs, carpetas, logs individuales

Genera:
  - Reporte HTML interactivo (dark mode, filtros JS, auto-open)
  - CSV consolidado

Uso rápido (igual que la versión ZIP):
    python smchs_log_analyzer.py
    python smchs_log_analyzer.py --logs-dir path/to/logs
    python smchs_log_analyzer.py --csv-only
    python smchs_log_analyzer.py --out reporte.html
    python smchs_log_analyzer.py --no-open

Uso extendido (acepta inputs mixtos):
    python smchs_log_analyzer.py --input outputs/archives
    python smchs_log_analyzer.py --input run1.zip run2.zip loose.log --out report.html
    python smchs_log_analyzer.py --input logs/ --copy-logs
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
import webbrowser
import zipfile
from dataclasses import dataclass, asdict, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Optional

# ── Regex helpers ─────────────────────────────────────────────────────────────

FLOAT     = r"[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?"
INT_COMMA = r"[\d,]+"


# ── Modelo de datos ───────────────────────────────────────────────────────────

@dataclass
class RunMetrics:
    source_file: str
    log_file:    str   = ""
    timestamp:   str   = ""

    # Versiones
    simulator_version:  str = ""
    hypothesis_version: str = ""

    # Parámetros de la corrida
    n:            Optional[int]   = None
    seed:         Optional[int]   = None
    f_rem:        Optional[float] = None
    tprev_gyr:    Optional[float] = None
    z_cut:        Optional[float] = None
    remnant_mode: str             = ""
    quench_uv:    str             = ""

    # Rango redshift
    z_min:            Optional[float] = None
    z_max:            Optional[float] = None
    t_lcdm_min_gyr:   Optional[float] = None
    t_lcdm_max_gyr:   Optional[float] = None

    # Conteos de detectables
    detectables_totales:         Optional[int] = None
    detectables_z_gt_cut_initial: Optional[int] = None

    # Métricas estadísticas principales
    p_anom_base:      Optional[float] = None
    p_anom_sectorial: Optional[float] = None
    ratio_r:          Optional[float] = None
    exceso_pct:       Optional[float] = None

    # Tests estadísticos
    ks_d:         Optional[float] = None
    ks_pvalue:    Optional[float] = None
    kl_divergencia: Optional[float] = None

    # Pearson
    pearson_base:      Optional[float] = None
    pearson_sectorial: Optional[float] = None

    # Conteos masivas / detectables z
    n_detectables_z_base:      Optional[int] = None
    n_detectables_z_sectorial: Optional[int] = None
    n_masivas_z_base:          Optional[int] = None
    n_masivas_z_sectorial:     Optional[int] = None

    # Anómalas
    anomalas_sectorial: Optional[int]   = None
    anomalas_rem:       Optional[int]   = None
    anomalas_rem_pct:   Optional[float] = None

    # Tail / SNR
    q99_base:       Optional[float] = None
    q99_sectorial:  Optional[float] = None
    delta_q99:      Optional[float] = None
    p_tail_base:    Optional[float] = None
    p_tail_sectorial: Optional[float] = None
    delta_p_tail:   Optional[float] = None
    snr_tail_q99:   Optional[float] = None

    # Timing
    elapsed_s: Optional[float] = None

    # Escaneo paralelo (scan_frems)
    scan_quench_uv: str = ""

    # Warnings / validación hotfix
    warnings: str = ""


def _to_int(text: str) -> Optional[int]:
    try:
        return int(text.replace(",", ""))
    except Exception:
        return None


def _to_float(text: str) -> Optional[float]:
    try:
        return float(text.replace(",", ""))
    except Exception:
        return None


def _search(pattern: str, text: str, flags=re.MULTILINE) -> Optional[re.Match]:
    return re.search(pattern, text, flags)


# ── Parseo del log de texto ───────────────────────────────────────────────────

def parse_log_text(text: str, source_file: str, log_file: str = "") -> RunMetrics:
    m = RunMetrics(source_file=source_file, log_file=log_file)

    # Primer timestamp
    mt = _search(r"^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}),\d+", text)
    if mt:
        m.timestamp = mt.group(1)

    # Línea de versión
    mv = _search(r"SMCHS\s*/\s*MCSSH\s+([^\s]+)\s+—\s+Hipótesis\s+([^\s]+)", text)
    if mv:
        m.simulator_version  = mv.group(1)
        m.hypothesis_version = mv.group(2)
    else:
        mv2 = _search(r"SMCHS / MCSSH v([\d.]+(?:-hotfix\d+)?)", text)
        if mv2:
            m.simulator_version = f"v{mv2.group(1)}"

    # Línea principal de parámetros
    mr = _search(
        rf"N=({INT_COMMA})\s*\|\s*f_rem=({FLOAT})\s*\|\s*tprev=({FLOAT})\s*Gyr\s*\|\s*z_cut=({FLOAT})\s*\|\s*seed=(\d+)",
        text,
    )
    if mr:
        m.n        = _to_int(mr.group(1))
        m.f_rem    = _to_float(mr.group(2))
        m.tprev_gyr = _to_float(mr.group(3))
        m.z_cut    = _to_float(mr.group(4))
        m.seed     = _to_int(mr.group(5))

    # remnant-mode y quench-uv (línea de run)
    mmode = _search(r"remnant-mode=([a-zA-Z0-9_\-]+).*?quench-uv=([A-Za-z]+)", text)
    if mmode:
        m.remnant_mode = mmode.group(1)
        m.quench_uv    = mmode.group(2)

    # Rango z
    mz = _search(
        rf"z\s*∈\s*\[({FLOAT}),\s*({FLOAT})\]\s*\|\s*t_ΛCDM\s*∈\s*\[({FLOAT}),\s*({FLOAT})\]\s*Gyr",
        text,
    )
    if mz:
        m.z_min           = _to_float(mz.group(1))
        m.z_max           = _to_float(mz.group(2))
        m.t_lcdm_min_gyr  = _to_float(mz.group(3))
        m.t_lcdm_max_gyr  = _to_float(mz.group(4))

    # Detectables totales
    md = _search(rf"Detectables totales=({INT_COMMA})\s*\|\s*detectables z>12=({INT_COMMA})", text)
    if md:
        m.detectables_totales          = _to_int(md.group(1))
        m.detectables_z_gt_cut_initial = _to_int(md.group(2))

    # Métricas con patrones simples
    _scalar_patterns = [
        ("p_anom_base",           rf"P\(anomalía\)\s+ΛCDM base\s*:\s*({FLOAT})"),
        ("p_anom_sectorial",      rf"P\(anomalía\)\s+sectorial\s*:\s*({FLOAT})"),
        ("ratio_r",               rf"Ratio R\s*:\s*({FLOAT})×"),
        ("exceso_pct",            rf"Exceso relativo\s*:\s*([+-]?{FLOAT})%"),
        ("ks_d",                  rf"KS statistic D\s*:\s*({FLOAT})"),
        ("ks_pvalue",             rf"KS p-value\s*:\s*({FLOAT})"),
        ("kl_divergencia",        rf"KL divergencia\s*:\s*({FLOAT})"),
        ("pearson_base",          rf"Pearson r \(base\)\s*:\s*({FLOAT})"),
        ("pearson_sectorial",     rf"Pearson r \(sectorial\)\s*:\s*({FLOAT})"),
        ("n_detectables_z_base",  rf"N detectables z>\d+ \(base\):\s*({INT_COMMA})"),
        ("n_detectables_z_sectorial", rf"N detectables z>\d+ \(sect\):\s*({INT_COMMA})"),
        ("n_masivas_z_base",      rf"N masivas\s+z>\d+ \(base\):\s*({INT_COMMA})"),
        ("n_masivas_z_sectorial", rf"N masivas\s+z>\d+ \(sect\):\s*({INT_COMMA})"),
        ("anomalas_sectorial",    rf"Anómalas \(sectorial\)\s*:\s*({INT_COMMA})"),
        ("q99_base",              rf"Q99 dt_signal base\s*:\s*([+-]?{FLOAT})\s*Gyr"),
        ("q99_sectorial",         rf"Q99 dt_signal sect\s*:\s*([+-]?{FLOAT})\s*Gyr"),
        ("delta_q99",             rf"ΔQ99 \(sect − base\)\s*:\s*([+-]?{FLOAT})\s*Gyr"),
        ("p_tail_base",           rf"P\(Δt_signal > 0\.5 Gyr\) base:\s*({FLOAT})"),
        ("p_tail_sectorial",      rf"P\(Δt_signal > 0\.5 Gyr\) sect:\s*({FLOAT})"),
        ("delta_p_tail",          rf"ΔP_tail \(sect − base\)\s*:\s*([+-]?{FLOAT})"),
        ("snr_tail_q99",          rf"SNR_tail \(Q99/σ_ruido\)\s*:\s*([+-]?{FLOAT})"),
        ("elapsed_s",             rf"Completado en ({FLOAT})s"),
    ]
    _int_fields = {"n_detectables_z_base", "n_detectables_z_sectorial",
                   "n_masivas_z_base", "n_masivas_z_sectorial", "anomalas_sectorial"}
    for attr, pat in _scalar_patterns:
        found = _search(pat, text)
        if found:
            raw = found.group(1)
            setattr(m, attr, _to_int(raw) if attr in _int_fields else _to_float(raw))

    # Anómalas que son rem
    mar = _search(rf"Anómalas que son rem\.\s*:\s*({INT_COMMA})\s*\(({FLOAT})%\)", text)
    if mar:
        m.anomalas_rem     = _to_int(mar.group(1))
        m.anomalas_rem_pct = _to_float(mar.group(2))

    # ── Detección quench_uv del scan paralelo ─────────────────────────────────
    # Busca la línea del scan_frems paralelo para comparar con la corrida principal
    msq = _search(r"\[parallel\]\s+scan_frems.*?\|\s*quench_uv=([A-Za-z]+)", text)
    if msq:
        m.scan_quench_uv = msq.group(1)

    # ── Warnings / validación hotfix ─────────────────────────────────────────
    warnings = []

    if m.quench_uv and m.scan_quench_uv:
        q_run  = m.quench_uv.lower()
        q_scan = m.scan_quench_uv.lower()
        run_on  = q_run  in ("on", "sí", "si", "true")
        scan_on = q_scan in ("on", "sí", "si", "true")
        if run_on != scan_on:
            warnings.append(
                f"⚠ quench_uv: run={m.quench_uv} pero scan={m.scan_quench_uv} "
                f"— posible mismatch hotfix"
            )

    if m.simulator_version and "v0.5.7" in m.simulator_version:
        if m.scan_quench_uv.lower() == "on":
            warnings.append(
                "⚠ scan muestra quench_uv=ON pero versión dice v0.5.7 "
                "— verificar si hotfix está reflejado en metadata"
            )

    m.warnings = "; ".join(warnings)
    return m


# ── Lectura de archivos de entrada ────────────────────────────────────────────

def _iter_input_files(inputs: list[str]) -> Iterable[Path]:
    """Expande globs, directorios y rutas individuales."""
    for raw in inputs:
        p = Path(raw)
        if any(ch in raw for ch in "*?[]"):
            yield from sorted(Path().glob(raw))
        elif p.is_dir():
            # En modo --input, expandir todo el directorio
            yield from sorted(p.rglob("*"))
        elif p.exists():
            yield p
        else:
            print(f"[WARN] No existe: {raw}", file=sys.stderr)


def _read_log_entries(path: Path) -> Iterable[tuple[str, str, str]]:
    """
    Yield tuples: (source_file, internal_log_name, text)
    Soporta .zip y archivos .log/.txt sueltos.
    """
    suffix = path.suffix.lower()

    if suffix == ".zip":
        try:
            with zipfile.ZipFile(path, "r") as z:
                names = [
                    n for n in z.namelist()
                    if n.lower().endswith((".log", ".txt")) and not n.endswith("/")
                ]
                for name in names:
                    try:
                        text = z.read(name).decode("utf-8", errors="replace")
                        if "SMCHS" in text or "MCSSH" in text or "analysis.estadistica" in text:
                            yield str(path), name, text
                    except Exception as exc:
                        print(f"[WARN] No pude leer {name} en {path}: {exc}", file=sys.stderr)
        except Exception as exc:
            print(f"[WARN] ZIP inválido {path}: {exc}", file=sys.stderr)

    elif suffix in {".log", ".txt"}:
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
            if "SMCHS" in text or "MCSSH" in text or "analysis.estadistica" in text:
                yield str(path), path.name, text
        except Exception as exc:
            print(f"[WARN] No pude leer {path}: {exc}", file=sys.stderr)


def leer_corridas_dir(logs_dir: Path) -> list[RunMetrics]:
    """Modo compatible con el ZIP original: lee todos smchs_run_*.zip de un directorio."""
    corridas: list[RunMetrics] = []
    zips = sorted(logs_dir.glob("smchs_run_*.zip"), key=lambda p: p.stat().st_mtime)
    if not zips:
        # Fallback: también acepta logs sueltos en el directorio
        for path in sorted(logs_dir.glob("*.log")) + sorted(logs_dir.glob("*.txt")):
            for source, name, text in _read_log_entries(path):
                m = parse_log_text(text, source_file=source, log_file=name)
                if m.seed is not None or m.ratio_r is not None:
                    corridas.append(m)
        return corridas

    for z in zips:
        for source, name, text in _read_log_entries(z):
            m = parse_log_text(text, source_file=source, log_file=name)
            if m.seed is not None or m.ratio_r is not None:
                corridas.append(m)
    return corridas


def leer_corridas_inputs(inputs: list[str]) -> list[RunMetrics]:
    """Modo extendido: acepta --input con múltiples rutas/globs."""
    rows_text: list[tuple[RunMetrics, str]] = []
    for path in _iter_input_files(inputs):
        if path.is_dir():
            continue
        for source, name, text in _read_log_entries(path):
            m = parse_log_text(text, source_file=source, log_file=name)
            if m.seed is not None or m.ratio_r is not None:
                rows_text.append((m, text))
    return [r for r, _ in rows_text], rows_text


# ── Exportar CSV ──────────────────────────────────────────────────────────────

def exportar_csv(corridas: list[RunMetrics], ruta: Path) -> None:
    ruta.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(asdict(corridas[0]).keys()) if corridas else list(asdict(RunMetrics(source_file="")).keys())
    with ruta.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for r in corridas:
            writer.writerow(asdict(r))
    print(f"CSV exportado: {ruta}")


# ── Helpers HTML ──────────────────────────────────────────────────────────────

def _snr_color_py(snr) -> str:
    try:
        v = float(snr)
        if v >= 3.0: return "#34d399"
        if v >= 2.0: return "#60a5fa"
        if v >= 1.0: return "#f59e0b"
        return "#f87171"
    except Exception:
        return "#888"


def _mode_badge_py(mode: str, quench: str) -> str:
    quench_on = str(quench).upper() in ("ON", "TRUE", "1", "SÍ", "SI")
    q = "+quench" if quench_on else ""
    dark_colors = {
        "flat":      ("#0c2a3f", "#60a5fa"),
        "metric":    ("#3b2800", "#fbbf24"),
        "geometric": ("#2e1065", "#c084fc"),
    }
    bg, fg = dark_colors.get(str(mode), ("#1e293b", "#94a3b8"))
    label = f"{mode}{q}"
    return (f'<span style="background:{bg};color:{fg};border-radius:4px;'
            f'padding:2px 8px;font-size:11px;font-weight:500">{label}</span>')


def _fmt_py(val, decimals=3, suffix="") -> str:
    try:
        return f"{float(val):.{decimals}f}{suffix}"
    except Exception:
        return str(val) if val else "—"


def _ts_local(ts: str) -> str:
    try:
        dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
        return dt.strftime("%Y-%m-%d %H:%M:%S UTC")
    except Exception:
        return ts[:19] if ts else "—"


# ── Generación del HTML (dark mode, filtros JS, auto-open) ───────────────────

def generar_html(corridas: list[RunMetrics], logs_dir: Path, csv_name: str = "") -> str:
    n_total_runs = len(corridas)
    snrs     = [c.snr_tail_q99 for c in corridas if c.snr_tail_q99 is not None]
    snr_min  = min(snrs) if snrs else 0
    snr_max  = max(snrs) if snrs else 0
    snr_ok   = sum(1 for s in snrs if s >= 2.0)
    snr_str3 = sum(1 for s in snrs if s >= 3.0)
    ts_gen   = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    # ── Tabla de resumen por escenario ────────────────────────────────────────
    scenario: dict[tuple, list[RunMetrics]] = {}
    for c in corridas:
        key = (c.remnant_mode or "—", c.quench_uv or "—")
        scenario.setdefault(key, []).append(c)

    summary_rows = ""
    for (mode, q), items in sorted(scenario.items()):
        def _avg(attr):
            vals = [getattr(x, attr) for x in items if getattr(x, attr) is not None]
            return sum(vals) / len(vals) if vals else None
        n_pos   = sum(1 for x in items if x.delta_q99 is not None and x.delta_q99 > 0)
        n_snr2  = sum(1 for x in items if x.snr_tail_q99 is not None and x.snr_tail_q99 >= 2)
        n_snr3  = sum(1 for x in items if x.snr_tail_q99 is not None and x.snr_tail_q99 >= 3)
        n_warn  = sum(1 for x in items if x.warnings)
        warn_cell = (f'<span style="color:#f59e0b">{n_warn} ⚠</span>' if n_warn else
                     f'<span style="color:#34d399">0</span>')
        summary_rows += f"""
        <tr>
          <td style="padding:8px 6px">{_mode_badge_py(mode, q)}</td>
          <td style="padding:8px 6px;text-align:right">{len(items)}</td>
          <td style="padding:8px 6px;text-align:right">{n_pos}/{len(items)}</td>
          <td style="padding:8px 6px;text-align:right">{n_snr2}/{len(items)}</td>
          <td style="padding:8px 6px;text-align:right">{n_snr3}/{len(items)}</td>
          <td style="padding:8px 6px;text-align:right">{_fmt_py(_avg('ratio_r'), 3)}×</td>
          <td style="padding:8px 6px;text-align:right">{_fmt_py(_avg('exceso_pct'), 1)}%</td>
          <td style="padding:8px 6px;text-align:right">{_fmt_py(_avg('delta_q99'), 4)} Gyr</td>
          <td style="padding:8px 6px;text-align:right">{_fmt_py(_avg('snr_tail_q99'), 3)}</td>
          <td style="padding:8px 6px;text-align:right">{warn_cell}</td>
        </tr>"""

    # ── Filas del detalle ─────────────────────────────────────────────────────
    rows_html = ""
    for c in corridas:
        snr_color = _snr_color_py(c.snr_tail_q99)
        snr_str   = (_fmt_py(c.snr_tail_q99) +
                     (" ★" if c.snr_tail_q99 is not None and c.snr_tail_q99 >= 2.0 else ""))

        mode    = c.remnant_mode or "—"
        quench  = c.quench_uv   or "—"
        seed    = str(c.seed) if c.seed is not None else "—"
        n_str   = f"{c.n:,}" if c.n is not None else "—"
        ts      = _ts_local(c.timestamp)
        ver     = c.simulator_version or "—"
        elapsed = _fmt_py(c.elapsed_s, 1, "s") if c.elapsed_s is not None else "—"
        exceso  = _fmt_py(c.exceso_pct, 1, "%") if c.exceso_pct is not None else "—"
        exceso_prefix = "+" if c.exceso_pct is not None and c.exceso_pct > 0 else ""
        scan_q  = c.scan_quench_uv or "—"
        warn_html = (f'<span style="color:#f59e0b;font-size:11px">{c.warnings}</span>'
                     if c.warnings else "")
        zip_name = Path(c.source_file).name

        rows_html += f"""
        <tr>
          <td style="padding:8px 6px;font-size:12px;color:#64748b">{ts}</td>
          <td style="padding:8px 6px;font-weight:500;font-size:13px">{seed}</td>
          <td style="padding:8px 6px">{_mode_badge_py(mode, quench)}</td>
          <td style="padding:8px 6px;text-align:center;font-size:12px">{scan_q}</td>
          <td style="padding:8px 6px;text-align:right;font-size:13px">{n_str}</td>
          <td style="padding:8px 6px;text-align:right;font-size:13px">{_fmt_py(c.ratio_r, 3)}×</td>
          <td style="padding:8px 6px;text-align:right;font-size:13px;color:#34d399">{exceso_prefix}{exceso}</td>
          <td style="padding:8px 6px;text-align:right;font-weight:500;font-size:13px;color:{snr_color}">{snr_str}</td>
          <td style="padding:8px 6px;text-align:right;font-size:13px">{_fmt_py(c.delta_q99, 3)} Gyr</td>
          <td style="padding:8px 6px;text-align:right;font-size:13px">{_fmt_py(c.n_masivas_z_base, 0)} / {_fmt_py(c.n_masivas_z_sectorial, 0)}</td>
          <td style="padding:8px 6px;text-align:right;font-size:12px;color:#64748b">{elapsed}</td>
          <td style="padding:8px 6px;font-size:11px;color:#94a3b8">{ver}</td>
          <td style="padding:8px 6px;font-size:11px;color:#64748b">{zip_name}</td>
          <td style="padding:8px 6px;font-size:11px">{warn_html}</td>
        </tr>"""

    # ── JSON para filtros/sort JS ─────────────────────────────────────────────
    datos_json = json.dumps([
        {
            "ts":      _ts_local(c.timestamp),
            "seed":    str(c.seed) if c.seed is not None else "",
            "mode":    c.remnant_mode or "",
            "quench":  c.quench_uv.upper() in ("ON", "TRUE", "SÍ", "SI"),
            "scan_quench": c.scan_quench_uv or "",
            "n":       c.n,
            "R":       round(c.ratio_r, 4) if c.ratio_r is not None else None,
            "exceso":  round(c.exceso_pct, 2) if c.exceso_pct is not None else None,
            "snr":     round(c.snr_tail_q99, 3) if c.snr_tail_q99 is not None else None,
            "dq99":    round(c.delta_q99, 4) if c.delta_q99 is not None else None,
            "elapsed": round(c.elapsed_s, 1) if c.elapsed_s is not None else None,
            "ver":     c.simulator_version or "",
            "zip":     Path(c.source_file).name,
            "warnings": c.warnings,
            "mas_base": c.n_masivas_z_base,
            "mas_sect": c.n_masivas_z_sectorial,
        }
        for c in corridas
    ], ensure_ascii=False)

    html = f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>SMCHS — Análisis de corridas</title>
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ font-family: 'Segoe UI', system-ui, sans-serif; background: #0f172a; color: #e2e8f0; min-height: 100vh; }}
  .header {{ background: #1e293b; border-bottom: 1px solid #334155; padding: 20px 32px; display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 10px; }}
  .header h1 {{ font-size: 18px; font-weight: 600; color: #f1f5f9; letter-spacing: -0.3px; }}
  .header .sub {{ font-size: 12px; color: #64748b; margin-top: 2px; }}
  .badge-gen {{ background: #1e3a5f; color: #60a5fa; border-radius: 6px; padding: 4px 10px; font-size: 11px; white-space: nowrap; }}
  .main {{ padding: 24px 32px; }}
  .metrics {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(140px, 1fr)); gap: 12px; margin-bottom: 24px; }}
  .metric {{ background: #1e293b; border: 1px solid #334155; border-radius: 8px; padding: 14px 16px; }}
  .metric .label {{ font-size: 11px; color: #64748b; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 6px; }}
  .metric .value {{ font-size: 22px; font-weight: 600; color: #f1f5f9; }}
  .metric .value.green {{ color: #34d399; }}
  .metric .value.blue  {{ color: #60a5fa; }}
  .metric .value.orange {{ color: #f59e0b; }}
  .section-title {{ font-size: 14px; font-weight: 600; color: #94a3b8; text-transform: uppercase; letter-spacing: 0.6px; margin: 0 0 10px 0; }}
  .card {{ background: #1e293b; border: 1px solid #334155; border-radius: 10px; padding: 18px; margin-bottom: 20px; overflow-x: auto; }}
  .controls {{ display: flex; gap: 10px; flex-wrap: wrap; margin-bottom: 16px; align-items: center; }}
  .controls select, .controls input {{ background: #0f172a; border: 1px solid #334155; color: #e2e8f0; border-radius: 6px; padding: 6px 10px; font-size: 13px; }}
  .controls label {{ font-size: 12px; color: #64748b; }}
  .btn {{ background: #1e3a5f; color: #60a5fa; border: 1px solid #1e40af; border-radius: 6px; padding: 6px 14px; font-size: 12px; cursor: pointer; }}
  .btn:hover {{ background: #1e40af; }}
  .table-wrap {{ overflow-x: auto; }}
  table {{ width: 100%; border-collapse: collapse; font-size: 13px; }}
  thead tr {{ background: #0f172a; border-bottom: 1px solid #334155; }}
  th {{ padding: 10px 6px; text-align: left; font-size: 11px; font-weight: 500; color: #64748b; text-transform: uppercase; letter-spacing: 0.4px; white-space: nowrap; }}
  th.r {{ text-align: right; }}
  th.c {{ text-align: center; }}
  tbody tr {{ border-bottom: 1px solid #0f172a; transition: background 0.1s; }}
  tbody tr:hover {{ background: #263447; }}
  tbody tr.warn-row {{ border-left: 3px solid #f59e0b; }}
  .warn-dot {{ display: inline-block; width: 8px; height: 8px; background: #f59e0b; border-radius: 50%; margin-right: 4px; }}
  .note {{ margin-top: 20px; font-size: 11px; color: #475569; border-top: 1px solid #1e293b; padding-top: 14px; }}
  #no-results {{ display: none; color: #475569; text-align: center; padding: 32px; font-size: 13px; }}
</style>
</head>
<body>

<div class="header">
  <div>
    <div class="header h1">SMCHS — Análisis de corridas archivadas</div>
    <div class="sub">Directorio: {logs_dir.resolve()} &nbsp;·&nbsp; Generado: {ts_gen}</div>
  </div>
  <span class="badge-gen">{n_total_runs} corridas</span>
</div>

<div class="main">

  <div class="metrics">
    <div class="metric">
      <div class="label">Corridas</div>
      <div class="value blue">{n_total_runs}</div>
    </div>
    <div class="metric">
      <div class="label">SNR mín</div>
      <div class="value {'green' if snr_min>=2 else 'orange'}">{snr_min:.3f}</div>
    </div>
    <div class="metric">
      <div class="label">SNR máx</div>
      <div class="value green">{snr_max:.3f}</div>
    </div>
    <div class="metric">
      <div class="label">SNR ≥ 2</div>
      <div class="value green">{snr_ok} / {len(snrs)}</div>
    </div>
    <div class="metric">
      <div class="label">SNR ≥ 3</div>
      <div class="value green">{snr_str3} / {len(snrs)}</div>
    </div>
    <div class="metric">
      <div class="label">Con warnings</div>
      <div class="value {'orange' if any(c.warnings for c in corridas) else 'green'}">{sum(1 for c in corridas if c.warnings)}</div>
    </div>
  </div>

  <!-- Resumen por escenario -->
  <div class="card">
    <div class="section-title">Resumen por escenario</div>
    <table>
      <thead>
        <tr>
          <th>Modo + Quench</th>
          <th class="r">Runs</th>
          <th class="r">ΔQ99 &gt; 0</th>
          <th class="r">SNR ≥ 2</th>
          <th class="r">SNR ≥ 3</th>
          <th class="r">R medio</th>
          <th class="r">Exceso medio</th>
          <th class="r">ΔQ99 medio</th>
          <th class="r">SNR medio</th>
          <th class="r">Warnings</th>
        </tr>
      </thead>
      <tbody>{summary_rows}</tbody>
    </table>
  </div>

  <!-- Controles de filtrado -->
  <div class="controls">
    <label>Modo:</label>
    <select id="filter-mode">
      <option value="">todos</option>
      <option value="flat">flat</option>
      <option value="metric">metric</option>
      <option value="geometric">geometric</option>
    </select>
    <label>Quench:</label>
    <select id="filter-quench">
      <option value="">todos</option>
      <option value="true">ON</option>
      <option value="false">off</option>
    </select>
    <label>Warnings:</label>
    <select id="filter-warn">
      <option value="">todos</option>
      <option value="true">solo con ⚠</option>
      <option value="false">sin warnings</option>
    </select>
    <label>Ordenar por:</label>
    <select id="sort-by">
      <option value="ts">fecha</option>
      <option value="snr">SNR ↓</option>
      <option value="R">ratio R ↓</option>
      <option value="seed">seed</option>
    </select>
    <button class="btn" onclick="exportarCSV()">⬇ CSV</button>
    <button class="btn" onclick="resetFiltros()">↺ Reset</button>
  </div>

  <!-- Tabla de detalle -->
  <div class="card">
    <div class="section-title">Detalle de corridas</div>
    <div class="table-wrap">
      <table id="tabla">
        <thead>
          <tr>
            <th>Timestamp</th>
            <th>Seed</th>
            <th>Modo</th>
            <th class="c">Scan Q</th>
            <th class="r">N</th>
            <th class="r">R</th>
            <th class="r">Exceso</th>
            <th class="r">SNR_tail</th>
            <th class="r">ΔQ99</th>
            <th class="r">Masivas B/S</th>
            <th class="r">Tiempo</th>
            <th>Ver.</th>
            <th>Fuente</th>
            <th>Warnings</th>
          </tr>
        </thead>
        <tbody id="tbody">
{rows_html}
        </tbody>
      </table>
      <div id="no-results">No hay corridas que coincidan con los filtros.</div>
    </div>
  </div>

  <div class="note">
    SNR_tail ★ = ≥ 2.0 (robusto) &nbsp;·&nbsp;
    R = ratio P(anomalía) sectorial / base &nbsp;·&nbsp;
    ΔQ99 = diferencia de percentil 99 de dt_signal (Gyr) &nbsp;·&nbsp;
    Scan Q = quench_uv detectado en el scan paralelo (para validar hotfix) &nbsp;·&nbsp;
    ⚠ = mismatch entre run y scan, verificar metadata
  </div>
</div>

<script>
const DATOS = {datos_json};

function snrColor(v) {{
  if (!v) return '#888';
  if (v >= 3.0) return '#34d399';
  if (v >= 2.0) return '#60a5fa';
  if (v >= 1.0) return '#f59e0b';
  return '#f87171';
}}

function modeBadge(mode, quench) {{
  const q = quench ? '+quench' : '';
  const colors = {{
    flat:      ['#0c2a3f','#60a5fa'],
    metric:    ['#3b2800','#fbbf24'],
    geometric: ['#2e1065','#c084fc'],
  }};
  const [bg, fg] = colors[mode] || ['#1e293b','#94a3b8'];
  return `<span style="background:${{bg}};color:${{fg}};border-radius:4px;padding:2px 8px;font-size:11px;font-weight:500">${{mode}}${{q}}</span>`;
}}

function fmt(v, d=3, s='') {{
  return v != null ? Number(v).toFixed(d) + s : '—';
}}

function renderTabla(datos) {{
  const tbody = document.getElementById('tbody');
  const noRes = document.getElementById('no-results');
  if (!datos.length) {{
    tbody.innerHTML = '';
    noRes.style.display = 'block';
    return;
  }}
  noRes.style.display = 'none';
  tbody.innerHTML = datos.map(c => {{
    const warnHtml = c.warnings
      ? `<span style="color:#f59e0b;font-size:11px"><span class="warn-dot"></span>${{c.warnings}}</span>`
      : '';
    const rowClass = c.warnings ? 'warn-row' : '';
    return `
    <tr class="${{rowClass}}">
      <td style="padding:8px 6px;font-size:12px;color:#64748b">${{c.ts}}</td>
      <td style="padding:8px 6px;font-weight:500;font-size:13px">${{c.seed || '—'}}</td>
      <td style="padding:8px 6px">${{modeBadge(c.mode, c.quench)}}</td>
      <td style="padding:8px 6px;text-align:center;font-size:12px;color:#94a3b8">${{c.scan_quench || '—'}}</td>
      <td style="padding:8px 6px;text-align:right;font-size:13px">${{c.n != null ? c.n.toLocaleString() : '—'}}</td>
      <td style="padding:8px 6px;text-align:right;font-size:13px">${{fmt(c.R, 3)}}×</td>
      <td style="padding:8px 6px;text-align:right;font-size:13px;color:#34d399">${{c.exceso != null ? (c.exceso > 0 ? '+' : '') + c.exceso.toFixed(1) + '%' : '—'}}</td>
      <td style="padding:8px 6px;text-align:right;font-weight:500;font-size:13px;color:${{snrColor(c.snr)}}">${{c.snr != null ? c.snr.toFixed(3) + (c.snr >= 2 ? ' ★' : '') : '—'}}</td>
      <td style="padding:8px 6px;text-align:right;font-size:13px">${{fmt(c.dq99, 3)}} Gyr</td>
      <td style="padding:8px 6px;text-align:right;font-size:13px">${{c.mas_base != null ? c.mas_base.toLocaleString() : '—'}} / ${{c.mas_sect != null ? c.mas_sect.toLocaleString() : '—'}}</td>
      <td style="padding:8px 6px;text-align:right;font-size:12px;color:#64748b">${{c.elapsed != null ? c.elapsed + 's' : '—'}}</td>
      <td style="padding:8px 6px;font-size:11px;color:#94a3b8">${{c.ver}}</td>
      <td style="padding:8px 6px;font-size:11px;color:#64748b">${{c.zip}}</td>
      <td style="padding:8px 6px">${{warnHtml}}</td>
    </tr>`;
  }}).join('');
}}

function filtrarYOrdenar() {{
  const mode   = document.getElementById('filter-mode').value;
  const quench = document.getElementById('filter-quench').value;
  const warn   = document.getElementById('filter-warn').value;
  const sortBy = document.getElementById('sort-by').value;

  let datos = [...DATOS];
  if (mode)         datos = datos.filter(c => c.mode === mode);
  if (quench !== '') datos = datos.filter(c => String(c.quench) === quench);
  if (warn === 'true')  datos = datos.filter(c => c.warnings);
  if (warn === 'false') datos = datos.filter(c => !c.warnings);

  datos.sort((a, b) => {{
    if (sortBy === 'snr')  return (b.snr  || 0) - (a.snr  || 0);
    if (sortBy === 'R')    return (b.R    || 0) - (a.R    || 0);
    if (sortBy === 'seed') return (a.seed || '') < (b.seed || '') ? -1 : 1;
    return a.ts < b.ts ? -1 : 1;
  }});
  renderTabla(datos);
}}

['filter-mode','filter-quench','filter-warn','sort-by'].forEach(id =>
  document.getElementById(id).addEventListener('change', filtrarYOrdenar)
);

function resetFiltros() {{
  ['filter-mode','filter-quench','filter-warn'].forEach(id =>
    document.getElementById(id).value = '');
  document.getElementById('sort-by').value = 'ts';
  filtrarYOrdenar();
}}

function exportarCSV() {{
  const campos  = ['ts','seed','mode','quench','scan_quench','n','R','exceso','snr','dq99','mas_base','mas_sect','elapsed','ver','zip','warnings'];
  const headers = 'timestamp,seed,modo,quench_uv,scan_quench_uv,N,R,exceso_pct,SNR_tail,delta_Q99_Gyr,n_masivas_base,n_masivas_sect,elapsed_s,version,zip_name,warnings';
  const filas = DATOS.map(c => campos.map(k => {{
    const v = c[k];
    if (v == null) return '';
    const s = String(v);
    return s.includes(',') ? `"${{s}}"` : s;
  }}).join(','));
  const blob = new Blob([headers + '\\n' + filas.join('\\n')], {{type:'text/csv'}});
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = 'smchs_corridas_' + new Date().toISOString().slice(0,10) + '.csv';
  a.click();
}}
</script>
</body>
</html>"""
    return html


# ── CLI ───────────────────────────────────────────────────────────────────────

def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Analiza corridas SMCHS y genera reporte HTML interactivo + CSV.",
        formatter_class=argparse.RawTextHelpFormatter,
        epilog="""
Ejemplos:
  # Modo simple: analiza logs/ del proyecto (comportamiento original)
  python smchs_log_analyzer.py

  # Directorio específico
  python smchs_log_analyzer.py --logs-dir path/to/logs

  # Inputs mixtos: ZIPs, logs sueltos, globs, carpetas
  python smchs_log_analyzer.py --input run1.zip run2.zip loose.log

  # Solo CSV, sin abrir el navegador
  python smchs_log_analyzer.py --csv-only

  # Sin abrir el navegador
  python smchs_log_analyzer.py --no-open

  # Copiar logs extraídos para inspección manual
  python smchs_log_analyzer.py --input logs/ --copy-logs
"""
    )
    # Modo simple (compatible con versión original)
    p.add_argument("--logs-dir", type=str, default=None,
                   help="Directorio de ZIPs (default: logs/ relativo a este script)")
    p.add_argument("--out", type=str, default=None,
                   help="Ruta del HTML de salida (default: <logs-dir>/smchs_reporte.html)")
    p.add_argument("--csv-only", action="store_true",
                   help="Solo exportar CSV, sin generar HTML ni abrir navegador")
    p.add_argument("--no-open", action="store_true",
                   help="No abrir el navegador automáticamente")
    p.add_argument("--csv-out", type=str, default=None,
                   help="Ruta del CSV de salida (default: <logs-dir>/smchs_corridas.csv)")
    # Modo extendido
    p.add_argument("--input", nargs="+", default=None,
                   help="Archivos .zip/.log/.txt, globs o carpetas (alternativa a --logs-dir)")
    p.add_argument("--name", type=str, default=None,
                   help="Nombre base para los archivos de salida (modo --input)")
    p.add_argument("--copy-logs", action="store_true",
                   help="Copiar logs extraídos a <out>/extracted_logs (solo con --input)")
    return p.parse_args()


def _copy_extracted_logs(rows_text: list, out_dir: Path) -> None:
    logs_dir = out_dir / "extracted_logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    for idx, (metrics, text) in enumerate(rows_text, start=1):
        seed  = metrics.seed if metrics.seed is not None else "unknown"
        mode  = metrics.remnant_mode or "mode"
        qval  = metrics.quench_uv or "quench"
        name  = f"{idx:03d}_seed{seed}_{mode}_q{qval}_{Path(metrics.source_file).stem}.log"
        safe  = re.sub(r"[^A-Za-z0-9_.\-]+", "_", name)
        (logs_dir / safe).write_text(text, encoding="utf-8")
    print(f"Logs copiados en: {logs_dir}")


def main() -> int:
    args = parse_args()

    # ── Resolver modo de lectura ──────────────────────────────────────────────
    if args.input:
        # Modo extendido: --input con múltiples rutas
        corridas, rows_text = leer_corridas_inputs(args.input)
        out_dir  = Path(args.out).parent if args.out else Path("smchs_log_analysis")
        stamp    = datetime.now().strftime("%Y%m%d_%H%M%S")
        base     = args.name or f"smchs_reporte_{stamp}"
        csv_path = Path(args.csv_out) if args.csv_out else out_dir / f"{base}.csv"
        html_path = Path(args.out) if args.out else out_dir / f"{base}.html"
        logs_dir  = Path(args.input[0]) if len(args.input) == 1 else Path(".")
    else:
        # Modo simple (comportamiento original de la versión ZIP)
        script_dir = Path(__file__).parent.parent
        if args.logs_dir:
            logs_dir = Path(args.logs_dir)
        else:
            logs_dir = script_dir / "logs"

        if not logs_dir.exists():
            print(f"Error: directorio de logs no encontrado: {logs_dir}", file=sys.stderr)
            print("Tip: usa --logs-dir o --input para especificar los logs.", file=sys.stderr)
            return 1

        corridas = leer_corridas_dir(logs_dir)
        rows_text = []
        csv_path  = Path(args.csv_out) if args.csv_out else logs_dir / "smchs_corridas.csv"
        html_path = Path(args.out) if args.out else logs_dir / "smchs_reporte.html"

    if not corridas:
        print("[ERROR] No se encontraron corridas SMCHS válidas.", file=sys.stderr)
        return 1

    print(f"Corridas procesadas: {len(corridas)}")

    # Warnings al vuelo
    n_warn = sum(1 for c in corridas if c.warnings)
    if n_warn:
        print(f"[⚠] {n_warn} corrida(s) con warnings de validación:")
        for c in corridas:
            if c.warnings:
                print(f"    {Path(c.source_file).name}: {c.warnings}")

    # CSV
    exportar_csv(corridas, csv_path)

    if args.csv_only:
        return 0

    # Copy logs (solo modo extendido)
    if args.copy_logs and rows_text:
        _copy_extracted_logs(rows_text, html_path.parent)

    # HTML
    html_path.parent.mkdir(parents=True, exist_ok=True)
    html_content = generar_html(corridas, logs_dir, csv_name=csv_path.name)
    html_path.write_text(html_content, encoding="utf-8")
    print(f"Reporte HTML generado: {html_path}")

    if not args.no_open:
        url = html_path.resolve().as_uri()
        print(f"Abriendo en navegador: {url}")
        webbrowser.open(url)

    # Resumen en consola
    print("\nResumen rápido:")
    for c in sorted(corridas, key=lambda x: (x.seed or 10**9, x.remnant_mode, x.quench_uv)):
        warn_tag = " ⚠" if c.warnings else ""
        print(
            f"  seed={c.seed} | mode={c.remnant_mode or '—'} | quench={c.quench_uv or '—'} "
            f"| scan={c.scan_quench_uv or '—'} | R={_fmt_py(c.ratio_r, 3)} "
            f"| exceso={_fmt_py(c.exceso_pct, 1)}% | ΔQ99={_fmt_py(c.delta_q99, 4)} "
            f"| SNR={_fmt_py(c.snr_tail_q99, 3)}{warn_tag}"
        )

    return 0


if __name__ == "__main__":
    sys.exit(main())
