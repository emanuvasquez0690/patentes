from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from fastapi.middleware.cors import CORSMiddleware

from api.routers import charts, catalogue, datasets


app = FastAPI(
    title="Portal de Datos Abiertos API",
    version="0.1.0",
    description="API para catálogo, datasets y gráficas base64 del portal de datos abiertos.",
)

# Habilitar CORS para que cualquier visualizador (como Streamlit) pueda consumir la API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Permite peticiones de cualquier dominio
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(catalogue.router)
app.include_router(datasets.router)
app.include_router(charts.router)


@app.get("/", include_in_schema=False)
def root():
    """Redirige la raíz directamente a la documentación de la API."""
    return RedirectResponse(url="/docs")


@app.get("/health")
def health_check() -> dict:
    return {"status": "ok"}


if __name__ == "__main__":
    import os

    import uvicorn

    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("api.main:app", host="0.0.0.0", port=port, reload=True)
