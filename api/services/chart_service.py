import base64
from io import BytesIO

import matplotlib.pyplot as plt
from matplotlib.figure import Figure
import pandas as pd

from api.schemas.responses import ChartResponse
from api.services.dataset_service import get_dataset_records


def _encode_figure_to_base64(figure: Figure) -> str:
    buffer = BytesIO()
    figure.savefig(buffer, format="png", bbox_inches="tight", dpi=150)
    plt.close(figure)
    buffer.seek(0)
    return base64.b64encode(buffer.read()).decode("utf-8")


def _build_auto_chart(df: pd.DataFrame) -> tuple[Figure, str]:
    numeric_cols = df.select_dtypes(include=["number"]).columns.tolist()
    if numeric_cols:
        column = numeric_cols[0]
        figure, axis = plt.subplots(figsize=(8, 4))
        df[column].dropna().plot(kind="hist", bins=20, ax=axis, color="#2E4EF2", alpha=0.85)
        axis.set_title(f"Distribución de {column}")
        axis.set_xlabel(column)
        axis.set_ylabel("Frecuencia")
        figure.tight_layout()
        return figure, "histogram"

    categorical_cols = df.select_dtypes(include=["object", "category"]).columns.tolist()
    if categorical_cols:
        column = categorical_cols[0]
        counts = df[column].fillna("SIN_VALOR").value_counts().head(15)
        figure, axis = plt.subplots(figsize=(10, 5))
        counts.sort_values().plot(kind="barh", ax=axis, color="#6A7BFF")
        axis.set_title(f"Top categorías de {column}")
        axis.set_xlabel("Frecuencia")
        axis.set_ylabel(column)
        figure.tight_layout()
        return figure, "bar"

    figure, axis = plt.subplots(figsize=(8, 4))
    axis.text(0.5, 0.5, "No hay columnas suficientes para graficar", ha="center", va="center")
    axis.axis("off")
    figure.tight_layout()
    return figure, "empty"


def build_dataset_chart_base64(dataset_id: str, chart_type: str = "auto", limit: int = 500) -> ChartResponse | None:
    dataframe = get_dataset_records(dataset_id=dataset_id, limit=limit, offset=0)
    if dataframe.empty:
        return None

    figure, resolved_chart_type = _build_auto_chart(dataframe)
    encoded_image = _encode_figure_to_base64(figure)
    return ChartResponse(dataset_id=dataset_id, chart_type=resolved_chart_type, image_base64=encoded_image)
