# SMCHS Streamlit Cloud hotfix

Archivos incluidos:

- `runtime.txt`: fija Python 3.11 en Streamlit Cloud.
- `requirements.txt`: versiones compatibles con ruedas precompiladas para evitar builds pesados de SciPy/Astropy.
- `.streamlit/config.toml`: configuración mínima del servidor.
- `app.py`: variante robusta del dashboard con `st.stop()` si fallan imports y `N` máximo 120k.

## Aplicación

Copiar estos archivos en la raíz del repo y hacer commit:

```bash
git add runtime.txt requirements.txt .streamlit/config.toml app.py
git commit -m "Fix Streamlit Cloud deployment runtime and dependencies"
git push
```

En Streamlit Cloud:
- Main file path: `app.py`
- Branch: `main`
