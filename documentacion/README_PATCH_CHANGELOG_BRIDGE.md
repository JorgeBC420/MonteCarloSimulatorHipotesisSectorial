# README / CHANGELOG bridge fix — SMCHS v0.5.3 → v0.5.7

Este parche corrige el salto documental entre el README antiguo `v0.5.3` y los cambios ya documentados de `v0.5.6` / `v0.5.7`.

## Qué corrige

El README previo podía dar la impresión de que el proyecto saltó directamente de:

```text
SMCHS v0.5.3
```

a:

```text
SMCHS v0.5.6
```

sin transición. Este parche agrega una sección explícita de historial:

```text
v0.5.3 — baseline público anterior
v0.5.4–v0.5.5 — versiones puente / consolidación interna
v0.5.6 — archivado, remnant-mode, geometric, paralelismo, pre-registro
v0.5.7 — quench UV
v0.5.7-hotfix1 — cableado quench_uv al scan/heatmap
v3.2.2/P4 — conexión externa JADES + permutation test
```

## Principio usado

No se inventan cambios específicos de `v0.5.4` o `v0.5.5` si no están claramente trazados en README, commits o documentos internos. Se documentan como **versiones puente** hasta reconstruir su changelog exacto.

## Cómo aplicar

Copiar o fusionar:

```text
CHANGELOG.md
README_CHANGELOG_INSERT.md
```

Luego editar `README.md` e insertar el bloque de `README_CHANGELOG_INSERT.md` después de la sección de versiones o antes de "Cambios principales en SMCHS v0.5.6".

Recomendado:

```powershell
git add README.md CHANGELOG.md README_CHANGELOG_INSERT.md
git commit -m "Document SMCHS changelog bridge from v0.5.3 to v0.5.7"
git push
```
