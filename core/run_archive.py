"""
core/run_archive.py — Archivo rotativo de corridas en logs/
SMCHS v0.5.6 / Hipótesis Sectorial v3.2.1

Al terminar cada corrida, empaqueta outputs/ + smchs_run.log en un ZIP
con timestamp y lo guarda en logs/. Mantiene un máximo de MAX_ZIPS archivos;
los más viejos se eliminan automáticamente (FIFO).

Uso desde main.py:
    from core.run_archive import archivar_corrida
    archivar_corrida(out_dir, log_dir, args_dict, elapsed)
"""

from __future__ import annotations

import json
import logging
import os
import zipfile
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)

MAX_ZIPS = 20          # máximo de ZIPs en logs/; el más viejo se elimina al superar este límite
ZIP_PREFIX = "smchs_run_"


def _manifest(args_dict: dict, elapsed: float, n_files: int) -> str:
    """Genera un JSON de metadatos para incluir dentro del ZIP."""
    return json.dumps(
        {
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "elapsed_s": round(elapsed, 2),
            "n_files_archivados": n_files,
            "parametros": args_dict,
        },
        indent=2,
        ensure_ascii=False,
    )


def archivar_corrida(
    out_dir: str | Path,
    log_dir: str | Path,
    args_dict: dict | None = None,
    elapsed: float = 0.0,
) -> Path | None:
    """
    Empaqueta el contenido de out_dir y el log de corrida en un ZIP rotativo
    dentro de log_dir. Elimina el ZIP más antiguo si se supera MAX_ZIPS.

    Parámetros
    ----------
    out_dir:
        Directorio con las figuras y CSV de la corrida (outputs/).
    log_dir:
        Directorio donde se guardarán los ZIPs (logs/).
    args_dict:
        Diccionario de parámetros de la corrida (para el manifiesto interno).
    elapsed:
        Duración de la corrida en segundos.

    Retorna
    -------
    Path del ZIP creado, o None si falló.
    """
    out_dir = Path(out_dir)
    log_dir = Path(log_dir)
    log_dir.mkdir(parents=True, exist_ok=True)

    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    zip_path = log_dir / f"{ZIP_PREFIX}{ts}.zip"

    # ── Recopilar archivos a empaquetar ──────────────────────────────────────
    archivos: list[Path] = []
    if out_dir.exists():
        archivos += [f for f in out_dir.iterdir() if f.is_file()]

    # Log de la corrida (puede estar en out_dir o en log_dir de corridas anteriores)
    log_file = out_dir / "smchs_run.log"
    if log_file.exists() and log_file not in archivos:
        archivos.append(log_file)

    if not archivos:
        logger.warning("[archivo] No se encontraron archivos para comprimir en %s", out_dir)
        return None

    # ── Crear ZIP ─────────────────────────────────────────────────────────────
    try:
        with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as zf:
            for f in archivos:
                zf.write(f, arcname=f.name)

            # Manifiesto interno
            manifest_json = _manifest(args_dict or {}, elapsed, len(archivos))
            zf.writestr("MANIFEST.json", manifest_json)

        size_kb = zip_path.stat().st_size / 1024
        logger.info(
            "[archivo] ZIP creado: %s  (%.1f KB, %d archivos)",
            zip_path.name, size_kb, len(archivos),
        )
    except Exception:
        logger.exception("[archivo] Error al crear ZIP: %s", zip_path)
        return None

    # ── Rotación: eliminar ZIPs más viejos si se supera MAX_ZIPS ─────────────
    _rotar_logs(log_dir)

    return zip_path


def _rotar_logs(log_dir: Path) -> None:
    """Mantiene solo los MAX_ZIPS ZIPs más recientes en log_dir."""
    zips = sorted(
        log_dir.glob(f"{ZIP_PREFIX}*.zip"),
        key=lambda p: p.stat().st_mtime,
    )
    exceso = len(zips) - MAX_ZIPS
    if exceso > 0:
        for viejo in zips[:exceso]:
            try:
                viejo.unlink()
                logger.info("[archivo] ZIP antiguo eliminado: %s", viejo.name)
            except Exception:
                logger.warning("[archivo] No se pudo eliminar: %s", viejo.name)


def listar_corridas(log_dir: str | Path) -> list[dict]:
    """
    Lista los ZIPs de corridas archivadas, ordenados del más reciente al más antiguo.
    Retorna lista de dicts con: nombre, path, size_kb, timestamp_utc.
    """
    log_dir = Path(log_dir)
    if not log_dir.exists():
        return []

    resultado = []
    for z in sorted(log_dir.glob(f"{ZIP_PREFIX}*.zip"), key=lambda p: p.stat().st_mtime, reverse=True):
        # Intentar leer manifiesto
        meta: dict = {}
        try:
            with zipfile.ZipFile(z, "r") as zf:
                if "MANIFEST.json" in zf.namelist():
                    meta = json.loads(zf.read("MANIFEST.json"))
        except Exception:
            pass
        resultado.append({
            "nombre": z.name,
            "path": str(z),
            "size_kb": round(z.stat().st_size / 1024, 1),
            "timestamp_utc": meta.get("timestamp_utc", "desconocido"),
            "elapsed_s": meta.get("elapsed_s", None),
            "parametros": meta.get("parametros", {}),
        })
    return resultado
