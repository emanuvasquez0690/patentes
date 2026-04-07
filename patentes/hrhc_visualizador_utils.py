import os
import tempfile
from pathlib import Path
from typing import Dict, List

import pandas as pd
import requests

DATASET_URL = "https://www.datos.gov.co/resource/hrhc-c4wu.json"
TEMP_CACHE_FILE = Path(tempfile.gettempdir()) / "hrhc_conv21_cache.pkl"


def _fetch_paginated_records(
    base_url: str,
    where_clause: str,
    page_size: int = 1000,
    timeout: int = 25,
    app_token: str = "",
) -> List[Dict]:
    all_records: List[Dict] = []
    offset = 0
    headers = {"User-Agent": "hrhc-visualizador/1.0"}

    if app_token:
        headers["X-App-Token"] = app_token

    while True:
        params = {
            "$where": where_clause,
            "$limit": page_size,
            "$offset": offset,
        }

        response = requests.get(base_url, params=params, headers=headers, timeout=timeout)
        response.raise_for_status()
        chunk = response.json()

        if not chunk:
            break

        all_records.extend(chunk)

        if len(chunk) < page_size:
            break

        offset += page_size

    return all_records


def _clean_hrhc_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df

    required = [
        "nme_pais_gr",
        "nme_region_gr",
        "nme_departamento_gr",
        "nme_municipio_gr",
        "nme_clasificacion_gr",
        "nme_gran_area_gr",
        "nme_convocatoria",
        "fcreacion_gr",
        "ano_convo",
        "inst_aval",
    ]

    for column in required:
        if column not in df.columns:
            df[column] = ""

    text_cols = [
        "nme_pais_gr",
        "nme_region_gr",
        "nme_departamento_gr",
        "nme_municipio_gr",
        "nme_clasificacion_gr",
        "nme_gran_area_gr",
        "nme_convocatoria",
        "inst_aval",
    ]

    for column in text_cols:
        df[column] = df[column].fillna("").astype(str).str.strip()

    df = df[df["nme_pais_gr"].str.upper() == "COLOMBIA"].copy()

    departamento = df["nme_departamento_gr"].replace("", pd.NA)
    df["region"] = departamento.fillna(df["nme_region_gr"]).fillna("SIN_REGION")
    df["ciudad"] = df["nme_municipio_gr"].replace("", "SIN_CIUDAD")
    df["clasificacion"] = df["nme_clasificacion_gr"].replace("", "SIN_CLASIFICACION")
    df["gran_area"] = df["nme_gran_area_gr"].replace("", "SIN_AREA")

    anio_conv = pd.to_datetime(df["ano_convo"], errors="coerce")
    anio_creacion = pd.to_datetime(df["fcreacion_gr"], errors="coerce")
    df["anio_convocatoria"] = anio_conv.dt.year
    df["anio_creacion_grupo"] = anio_creacion.dt.year

    return df


def fetch_hrhc_convocatoria_21() -> pd.DataFrame:
    where_clause = "id_convocatoria = '21' AND id_convocatoria IS NOT NULL"
    app_token = os.getenv("SOCRATA_APP_TOKEN", "")
    records = _fetch_paginated_records(DATASET_URL, where_clause=where_clause, app_token=app_token)

    if not records:
        return pd.DataFrame()

    return _clean_hrhc_dataframe(pd.DataFrame(records))


def save_temp_cache(df: pd.DataFrame) -> Path:
    df.to_pickle(TEMP_CACHE_FILE)
    return TEMP_CACHE_FILE


def apply_filters(df: pd.DataFrame, selected_regions: List[str], selected_cities: List[str]) -> pd.DataFrame:
    filtered_df: pd.DataFrame = df.copy()

    if selected_regions:
        filtered_df = filtered_df[filtered_df["region"].isin(selected_regions)]

    if selected_cities:
        filtered_df = filtered_df[filtered_df["ciudad"].isin(selected_cities)]

    return filtered_df


def get_available_cities(df: pd.DataFrame, selected_regions: List[str]) -> List[str]:
    source_df: pd.DataFrame = df
    if selected_regions:
        source_df = source_df[source_df["region"].isin(selected_regions)]

    return sorted(source_df["ciudad"].dropna().unique().tolist())

