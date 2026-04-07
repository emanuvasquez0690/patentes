# Visualizador de Patentes CO

Este proyecto agrega un visualizador interactivo para explorar patentes de Colombia usando datos de Socrata.

## Que hace

- Consulta datos frescos en cada inicio desde `w8hf-jz4a`.
- Filtra solo registros con `pais = CO`.
- Guarda una cache temporal (`pickle`) en el directorio temporal del sistema para el tratamiento durante la sesion.
- Permite filtrar por `region` y opcionalmente por `ciudad`.
- Muestra graficas de regiones, ciudades, evolucion anual y naturaleza.

## Archivos principales

- `.venv/patentes/visualizador_unificado.py`: app principal unificada con menu para elegir modulo.
- `.venv/patentes/visualizador_patentes.py`: app Streamlit (patentes `w8hf-jz4a`).
- `.venv/patentes/patentes_visualizador_utils.py`: descarga, limpieza, cache y filtros para patentes.
- `.venv/patentes/visualizador_hrhc.py`: app Streamlit para `hrhc-c4wu` (convocatoria 21).
- `.venv/patentes/hrhc_visualizador_utils.py`: descarga, limpieza, cache y filtros por region/ciudad para HRHC.
- `.venv/patentes/verificar_json_api.py`: script para inspeccionar estructura JSON de endpoints.

## Ejecucion rapida (Windows PowerShell)

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m streamlit run .\.venv\patentes\visualizador_unificado.py
```

## Ejecutar visualizador solo Patentes

```powershell
.\.venv\Scripts\python.exe -m streamlit run .\.venv\patentes\visualizador_patentes.py
```

## Ejecutar visualizador solo HRHC

```powershell
.\.venv\Scripts\python.exe -m streamlit run .\.venv\patentes\visualizador_hrhc.py
```

Si quieres usar App Token de Socrata:

```powershell
$env:SOCRATA_APP_TOKEN = "TU_TOKEN"
.\.venv\Scripts\python.exe -m streamlit run .\.venv\patentes\visualizador_unificado.py
```

## Pruebas

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s .\.venv\patentes -p "test_*.py" -v
```

## Verificar JSON crudo de la API

Este endpoint (`query.json`) requiere autenticacion (App Token) en datos.gov.co.

```powershell
$env:SOCRATA_APP_TOKEN = "TU_TOKEN"
.\.venv\Scripts\python.exe .\.venv\patentes\verificar_json_api.py --limit 5 --sample 2
```

Opcional: guardar respuesta completa en archivo local.

```powershell
.\.venv\Scripts\python.exe .\.venv\patentes\verificar_json_api.py --save-raw respuesta_hrhc_c4wu.json
```
