# Patch — Changelog reconstruido v0.5.4 y v0.5.5

Este paquete reemplaza el parche anterior que marcaba `v0.5.4` y `v0.5.5` como “puente pendiente”.

## Corrección

Sí existía documentación de ambas versiones:

- `v0.5.4+`: anexo metodológico de comparativas redshift/CMB reales.
- `v0.5.5`: roadmap de baselines externos, overlay observacional y dilución métrica.

## Archivos incluidos

```text
CHANGELOG.md
README_CHANGELOG_INSERT.md
README_PATCH_RECONSTRUCTED_V054_V055.md
```

## Aplicación sugerida

1. Copiar `CHANGELOG.md` a la raíz del repo.
2. Insertar el contenido de `README_CHANGELOG_INSERT.md` en el README principal.
3. Commit:

```powershell
git add README.md CHANGELOG.md README_CHANGELOG_INSERT.md README_PATCH_RECONSTRUCTED_V054_V055.md
git commit -m "Reconstruct SMCHS changelog for v0.5.4 and v0.5.5"
git push
```
