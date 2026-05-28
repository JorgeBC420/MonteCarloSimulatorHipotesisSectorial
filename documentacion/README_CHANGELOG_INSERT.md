## Historial de versiones y puente documental

El README público anterior todavía reflejaba principalmente el estado `SMCHS v0.5.3 / HTSC v3.1`. Desde entonces el proyecto avanzó hacia `SMCHS v0.5.7-hotfix1 / HTSC v3.2.2`, pero parte de la documentación técnica quedó distribuida en archivos `.md`, logs, auditorías y notas internas.

Para evitar un salto documental artificial, el historial queda ordenado así:

| Versión | Estado documental | Resumen |
|---|---|---|
| `v0.5.3` | baseline público anterior | Estado previo del simulador documentado en README antiguo. |
| `v0.5.4` | versión puente | Consolidación interna; changelog exacto pendiente de reconstruir desde commits/notas. |
| `v0.5.5` | versión puente | Consolidación interna previa a `v0.5.6`; changelog exacto pendiente de reconstruir. |
| `v0.5.6` | documentado | Archivado automático, `--remnant-mode`, modo `geometric`, paralelismo adaptativo, pre-registro y objetos observacionales ampliados. |
| `v0.5.7` | documentado | Supresión UV por quenching en `core/poblacion.py`. |
| `v0.5.7-hotfix1` | documentado | Corrección del cableado de `--quench-uv` hacia `scan_frems_parallel()` y `heatmap_parallel()`. |
| `P4-v3.2.2` | experimental externo | Prueba externa de cola con permutation test, JADES DR5 conectado y baselines TNG/SIMBA pendientes. |

Las versiones `v0.5.4` y `v0.5.5` no deben presentarse como saltos científicos mayores mientras no exista changelog reconstruido. Funcionan como versiones puente entre el README antiguo `v0.5.3` y la refactorización documentada en `v0.5.6`.

### Nota de trazabilidad

Si se reconstruyen commits o notas de `v0.5.4` y `v0.5.5`, este README debe actualizarse con cambios específicos. Hasta entonces, el proyecto evita atribuirles funciones no verificadas.
