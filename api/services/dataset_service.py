from typing import Optional

import pandas as pd
import requests

from api.services.catalogue_service import get_catalogue
from patentes.hrhc_visualizador_utils import fetch_hrhc_convocatoria_21
from patentes.patentes_visualizador_utils import fetch_patentes_global


DATASET_ALIASES = {
    "w8hf-jz4a": {"kind": "patentes", "fetch": fetch_patentes_global},
    "hrhc-c4wu": {"kind": "hrhc", "fetch": fetch_hrhc_convocatoria_21},
}


def get_dataset_info(dataset_id: str) -> Optional[dict]:
    catalogue_df = get_catalogue()
    if catalogue_df.empty:
        return None

    matches = catalogue_df[catalogue_df["id"].astype(str) == str(dataset_id)]
    if matches.empty:
        return None

    return matches.iloc[0].to_dict()


def _fetch_remote_records(api_url: str, limit: int = 100, offset: int = 0) -> pd.DataFrame:
    params = {"$limit": limit, "$offset": offset}
    response = requests.get(api_url, params=params, timeout=30)
    response.raise_for_status()
    data = response.json()
    return pd.DataFrame(data)


def get_dataset_records(dataset_id: str, limit: int = 200, offset: int = 0) -> pd.DataFrame:
    dataset_id = str(dataset_id)
    alias = DATASET_ALIASES.get(dataset_id)
    if alias is not None:
        dataframe = alias["fetch"]()
        if dataframe.empty:
            return dataframe
        return dataframe.iloc[offset : offset + limit].copy()

    dataset_info = get_dataset_info(dataset_id)
    if dataset_info is None:
        return pd.DataFrame()

    api_url = dataset_info.get("api_url")
    if not api_url:
        return pd.DataFrame()

    return _fetch_remote_records(api_url=api_url, limit=limit, offset=offset)


def get_dataset_preview(dataset_id: str, limit: int = 50) -> pd.DataFrame:
    return get_dataset_records(dataset_id=dataset_id, limit=limit, offset=0)
