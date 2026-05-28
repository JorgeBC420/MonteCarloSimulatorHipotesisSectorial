# Roadmap operativo HTSC/SMCHS v3.2.2 — DAG de dependencias

Este roadmap reemplaza expresiones ambiguas como “siguiente” o “posterior” por
dependencias auditables.

---

## Fase A — Cierre de v0.5.7-hotfix1

**Acción:** sincronizar metadata, documentar matriz limpia `5 seeds × 3 escenarios`
y separar corridas técnicas de corridas científicas.

**Dependencia:** ninguna.  
**Estado:** completado / en cierre.

Bloquea:
- Fase B.

---

## Fase B — Ingesta observacional

**Acción:** conectar JADES DR5 y ASTRODEEP mediante loaders normalizados.

Columnas canónicas mínimas:

```text
name
source
z
log_m_star
MUV
confirmed
volume_Mpc3
```

**Dependencia:** Fase A.  
**Estado:** siguiente.

Bloquea:
- Fase C.

---

## Fase C — Baselines externos

**Acción:** cargar IllustrisTNG y SIMBA con los mismos cortes de redshift,
masa, MUV y volumen.

**Dependencia:** Fase B.  
**Estado:** pendiente.

Bloquea:
- Fase D.

---

## Fase D — Completeness NIRCam/MUV

**Acción:** aplicar una función simplificada de detectabilidad/completeness a:

```text
observación
baseline externo
SMCHS
```

**Dependencia:** Fase C.  
**Estado:** pendiente.

Bloquea:
- Fase E.

**Nota crítica:** esta fase bloquea P4. Sin completeness, un exceso en Q99 puede
ser un sesgo de selección.

---

## Fase E — Prueba P4-v3.2.2

**Acción:** ejecutar `D_tail_mass` y/o `D_tail_MUV` mediante permutation test
unilateral con `n_iter >= 10,000`.

**Dependencias:** Fase C y Fase D.  
**Estado:** pendiente.

Criterio de interés:

```text
D_tail_mass > 0.15 dex y p < 0.05
o
D_tail_MUV > 0.5 mag y p < 0.05
```

---

## Fase F — Extensiones dinámicas

**Acción:** desarrollar SMBH fugitivos, masa no visible y λ-Hubble como módulos
satélite.

**Dependencia:** desacoplada del núcleo galáctico.  
**Estado:** exploratorio continuo.

**Nota:** esta fase no bloquea P4 y no debe presentarse como derivación necesaria
del núcleo HTSC.
