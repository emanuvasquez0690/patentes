import logging
import tempfile
from pathlib import Path
from typing import Dict, List

import pandas as pd
import requests

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

DATASET_URL = "https://www.datos.gov.co/resource/w8hf-jz4a.json"
TEMP_CACHE_FILE = Path(tempfile.gettempdir()) / "patentes_cache_co.pkl"


def _fetch_paginated_records(base_url: str, where_clause: str, page_size: int = 1000, timeout: int = 20) -> List[Dict]:
    """Descarga todos los registros de Socrata con paginacion."""
    all_records: List[Dict] = []
    offset = 0

    while True:
        params = {
            "$where": where_clause,
            "$limit": page_size,
            "$offset": offset,
        }

        response = requests.get(base_url, params=params, timeout=timeout)
        response.raise_for_status()
        chunk = response.json()

        if not chunk:
            break

        all_records.extend(chunk)

        if len(chunk) < page_size:
            break

        offset += page_size

    return all_records


def _clean_patentes_dataframe(df: pd.DataFrame, only_co: bool = True) -> pd.DataFrame:
    """Normaliza columnas clave para filtros y graficas."""
    if df.empty:
        return df

    columns_to_fill = ["pais", "region", "ciudad", "naturaleza", "solicitante", "a_o_concesi_n"]
    for column in columns_to_fill:
        if column not in df.columns:
            df[column] = ""

    for col in ["pais", "region", "ciudad", "naturaleza", "solicitante"]:
        df[col] = df[col].fillna("").astype(str).str.strip()

    if only_co:
        df = df[df["pais"].str.upper() == "CO"].copy()
    else:
        df = df[df["pais"] != ""].copy()

    df["region"] = df["region"].replace("", "SIN_REGION")
    df["ciudad"] = df["ciudad"].replace("", "SIN_CIUDAD")
    df["anio_concesion"] = pd.to_numeric(df["a_o_concesi_n"], errors="coerce")

    return df


def fetch_patentes_co() -> pd.DataFrame:
    """Trae datos frescos desde Socrata y filtra pais CO."""
    where_clause = "pais = 'CO'"
    records = _fetch_paginated_records(DATASET_URL, where_clause=where_clause)

    if not records:
        return pd.DataFrame()

    return _clean_patentes_dataframe(pd.DataFrame(records), only_co=True)


def fetch_patentes_global() -> pd.DataFrame:
    """Trae datos frescos de patentes con pais informado (CO e internacional)."""
    where_clause = "pais IS NOT NULL"
    records = _fetch_paginated_records(DATASET_URL, where_clause=where_clause)

    if not records:
        return pd.DataFrame()

    return _clean_patentes_dataframe(pd.DataFrame(records), only_co=False)


def save_temp_cache(df: pd.DataFrame) -> Path:
    """Guarda un cache temporal para evitar reprocesar durante la sesion."""
    df.to_pickle(TEMP_CACHE_FILE)
    return TEMP_CACHE_FILE


def apply_filters(df: pd.DataFrame, selected_regions: List[str], selected_cities: List[str]) -> pd.DataFrame:
    """Aplica filtros de region y ciudad en cascada."""
    filtered_df = df.copy()

    if selected_regions:
        filtered_df = filtered_df[filtered_df["region"].isin(selected_regions)]

    if selected_cities:
        filtered_df = filtered_df[filtered_df["ciudad"].isin(selected_cities)]

    return filtered_df


def get_available_cities(df: pd.DataFrame, selected_regions: List[str]) -> List[str]:
    """Obtiene ciudades segun region seleccionada."""
    source_df = df
    if selected_regions:
        source_df = source_df[source_df["region"].isin(selected_regions)]

    return sorted(source_df["ciudad"].dropna().unique().tolist())


