# Portal de datos abiertos - Patentes y HRHC

Portal Streamlit listo para desplegar en Streamlit Cloud.

## Estructura final

- `streamlit_app.py`: punto de entrada principal para Streamlit Cloud.
- `patentes/visualizador_unificado.py`: app unificada con navegación y vistas.
- `patentes/patentes_visualizador_utils.py`: descarga, limpieza y filtros para patentes.
- `patentes/hrhc_visualizador_utils.py`: descarga, limpieza y filtros para HRHC.
- `requirements.txt`: dependencias mínimas.

## Ejecucion local

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m streamlit run streamlit_app.py
```

> Importante: no ejecutes `streamlit_app.py` con `python`; usa siempre `streamlit run streamlit_app.py`.

## Despliegue en Streamlit Cloud

- Sube este repositorio a GitHub.
- En Streamlit Cloud usa como archivo principal: `streamlit_app.py`.
- Si necesitas token de Socrata, agrega la variable de entorno `SOCRATA_APP_TOKEN` en el panel de secretos/variables.

## Dependencias

Solo se conservan las necesarias para ejecutar la app:

- `pandas`
- `requests`
- `streamlit`
- `plotly`
