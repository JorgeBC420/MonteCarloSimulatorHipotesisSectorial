# Módulos auxiliares: Apéndice C y λ-Hubble

**Estado:** base arquitectónica independiente.  
**Conexión con core SMCHS:** ninguna por ahora.  
**Propósito:** preparar la futura integración del Apéndice C de la HTSC v3.2.1 sin contaminar el toy model principal de galaxias tempranas.

---

## 1. Qué se agregó

```text
extensions/
  __init__.py
  smbh_kinematics.py   # Sondas dinámicas extremas / SMBH fugitivos
  hubble_tension.py    # Modelo fenomenológico λ-Hubble
  run_lambda_demo.py   # Demo CLI con datos mock

tests/
  test_extensions_smbh_kinematics.py
  test_extensions_hubble_lambda.py
```

Estos módulos implementan bases de cálculo, no una afirmación física demostrada.

---

## 2. Módulo SMBH: `extensions/smbh_kinematics.py`

### Pregunta

Si un agujero negro supermasivo fugitivo tiene velocidad de eyección, trayectoria y masa acotables, ¿cuánta masa dinámica total requiere su movimiento?

### Fórmula base

```text
M_no_visible = M_dinamica - M_barionica
```

con:

```text
M_barionica = M_* + M_gas + M_BH
```

La fracción efectiva de masa no visible queda:

```text
f_DM_eff = (M_dinamica - M_barionica) / M_dinamica
```

### Implementación actual

La clase principal es:

```python
from extensions.smbh_kinematics import FugitiveSMBHProbe

probe = FugitiveSMBHProbe(v_ejec_kms=1600.0, radius_kpc=60.0)
f_dm = probe.f_dm_eff(baryonic_mass_msun=1.0e12)
```

Modelos de halo disponibles como base:

- `point_mass`
- `singular_isothermal`
- `nfw` simplificado

### Advertencia

La implementación actual es de orden de magnitud. No reemplaza una reconstrucción orbital 3D ni un ajuste NFW real.

---

## 3. Módulo λ-Hubble: `extensions/hubble_tension.py`

### Pregunta

Si parte de la diferencia entre `H0_local` y `H0_CMB` estuviera asociada a masa no visible local, ¿qué acoplamiento fenomenológico `λ` sería necesario?

### Fórmula central

```text
H0_local = H0_CMB * (1 + λ f_DM_eff)
```

Por tanto:

```text
λ = (H0_local / H0_CMB - 1) / f_DM_eff
```

### Uso mínimo

```python
from extensions.hubble_tension import lambda_from_f_dm

estimate = lambda_from_f_dm(f_dm_eff=0.8)
print(estimate.lambda_param)
```

### Criterio de estabilidad

El módulo se vuelve interesante solo si distintas sondas producen valores compatibles:

```text
λ_i ≈ λ_0
```

El módulo se debilita si `λ` varía caóticamente entre sistemas o requiere valores físicamente absurdos.

---

## 4. Demo CLI

Desde la raíz del repo:

```bash
python -m extensions.run_lambda_demo
```

La demo usa datos mock. No debe citarse como resultado observacional.

---

## 5. Tests

Ejecutar:

```bash
python scripts/verify.py
python -m pytest -q tests
```

Los tests verifican:

- cálculo de `f_DM_eff` en casos básicos;
- rechazo de entradas inválidas;
- roundtrip entre `λ` y `H0_local`;
- criterio de estabilidad de `λ` con datos mock;
- inestabilidad esperada cuando los valores de `f_DM_eff` divergen.

---

## 6. Cómo conectarlos en el futuro

### Etapa A — Mantenerlos separados

Por ahora no conectar a `main.py`, `core/poblacion.py` ni `analysis/estadistica.py`.

Razón: SMCHS mide colas de madurez temprana. El módulo SMBH/λ-Hubble estudia otra pregunta: masa no visible y posible sesgo de inferencia local. Mezclarlos demasiado pronto puede debilitar la claridad del proyecto.

### Etapa B — Crear CSV observacional externo

Formato sugerido:

```csv
system_name,v_ejec_kms,radius_kpc,m_baryonic_msun,halo_model,nfw_scale_radius_kpc,H0_local,H0_CMB
runaway_A,1600,60,1.0e12,point_mass,,73.0,67.4
```

### Etapa C — Crear runner independiente

Archivo futuro sugerido:

```text
extensions/run_smbh_hubble_from_csv.py
```

Responsabilidades:

1. leer CSV de sistemas dinámicos;
2. calcular `M_dinamica`, `M_no_visible`, `f_DM_eff`;
3. calcular `λ`;
4. exportar `outputs/extensions_lambda_report.csv`;
5. generar una figura de `λ_i` por sistema.

### Etapa D — Dashboard opcional

Agregar pestaña en `app.py`:

```text
Apéndice C / λ-Hubble
```

Controles:

- cargar CSV;
- elegir modelo de halo;
- editar `H0_CMB` y `H0_local`;
- mostrar tabla de `f_DM_eff`, `λ`, estabilidad.

### Etapa E — Integración científica

Solo después de tener datos observacionales reales:

- trayectorias 3D o restricciones de proyección;
- velocidad radial;
- masa bariónica con error;
- perfil de halo asumido;
- intervalos de confianza.

En ese punto se puede comparar si `λ_i` converge entre:

- agujeros negros fugitivos;
- curvas de rotación;
- lentes gravitacionales;
- cúmulos;
- dispersión de velocidades.

---

## 7. Qué NO afirma este módulo

No afirma que la materia oscura resuelva la Tensión de Hubble.

No afirma que los agujeros negros fugitivos prueben la HTSC.

No afirma que `λ` sea una constante física.

Solo implementa una pregunta falsable:

> Si la masa no visible local contribuyera a un sesgo en la inferencia de `H0`, ¿qué valor de `λ` exigiría cada sistema dinámico, y esos valores convergen o no?
