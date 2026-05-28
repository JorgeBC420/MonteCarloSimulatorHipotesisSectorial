# P4-v3.2.2 — Criterio cuantitativo de cola externa

**Estado:** pre-registro metodológico para comparación externa.  
**Núcleo asociado:** HTSC v3.2.2.  
**Simulador asociado:** SMCHS v0.5.7-hotfix1 o posterior.

---

## 1. Propósito

P4-v3.2.2 no busca probar HTSC con objetos individuales. Su objetivo es
evaluar si catálogos observacionales como JADES DR5 o ASTRODEEP muestran
un residuo poblacional de cola frente a baselines ΛCDM refinados como
IllustrisTNG o SIMBA.

La interpretación correcta es:

```text
resultado positivo = HTSC gana interés fenomenológico frente a ese baseline
resultado negativo = HTSC pierde necesidad explicativa en esa cola externa
```

No debe escribirse como confirmación de HTSC.

---

## 2. Hipótesis nula

La hipótesis nula H0 establece que:

```text
obs_data y baseline_data provienen de la misma distribución efectiva
después de aplicar cortes equivalentes y completeness observacional.
```

Por tanto, cualquier comparación P4 requiere aplicar antes:

- mismos cortes de redshift;
- mismos cortes de masa o magnitud;
- misma función de detectabilidad/completeness;
- normalización de columnas;
- tratamiento explícito de objetos confirmados vs fotométricos.

---

## 3. Estadísticos

### Masa estelar

```text
D_tail_mass = Q99(log M*)_obs - Q99(log M*)_baseline
```

Criterio inicial pre-registrado:

```text
D_tail_mass > 0.15 dex
```

### Magnitud UV

Para MUV, más brillante significa más negativo. Se usa la cola baja:

```text
D_tail_MUV = Q1(MUV)_baseline - Q1(MUV)_obs
```

Criterio inicial pre-registrado:

```text
D_tail_MUV > 0.5 mag
```

---

## 4. Significancia

La significancia principal se estima con **permutation test unilateral**,
no con bootstrap simple sobre un solo catálogo.

Criterio:

```text
p < 0.05
n_iter >= 10,000
```

El p-value se define como la fracción de permutaciones bajo H0 donde:

```text
D_tail_perm >= D_tail_observado
```

---

## 5. Criterio de interés fenomenológico

HTSC gana interés fenomenológico frente a un baseline externo solo si se cumplen
simultáneamente:

```text
1. D_tail supera el umbral de tamaño de efecto.
2. permutation test unilateral produce p < 0.05.
3. el signo del exceso persiste contra al menos un baseline externo independiente.
4. observación y baseline pasaron por cortes/completeness equivalentes.
```

Si estos criterios no se cumplen, HTSC pierde necesidad explicativa en la cola
galáctica temprana evaluada.

---

## 6. Advertencia de selección

La prueba P4 no debe ejecutarse como resultado científico final hasta completar
el bloque de completeness NIRCam/MUV. Comparar JADES/ASTRODEEP directamente
contra TNG/SIMBA sin función de selección puede generar falsos positivos.
