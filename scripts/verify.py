"""Verificación de sintaxis para SMCHS."""
from __future__ import annotations

import py_compile
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
EXCLUDE = {"outputs", "logs", "__pycache__", ".pytest_cache"}

def iter_py_files(root: Path):
    for path in root.rglob("*.py"):
        if any(part in EXCLUDE for part in path.parts):
            continue
        yield path

def main() -> int:
    ok = True
    for path in sorted(iter_py_files(ROOT)):
        try:
            py_compile.compile(str(path), doraise=True)
            print(f"OK  {path.relative_to(ROOT)}")
        except py_compile.PyCompileError as exc:
            ok = False
            print(f"ERR {path.relative_to(ROOT)}\n{exc}")
    return 0 if ok else 1

if __name__ == "__main__":
    raise SystemExit(main())
