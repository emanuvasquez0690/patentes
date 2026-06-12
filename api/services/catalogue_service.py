import json
from functools import lru_cache
from pathlib import Path

import pandas as pd


CATALOGUE_PATH = Path(__file__).resolve().parents[2] / "datasets.json"


@lru_cache(maxsize=1)
def get_catalogue() -> pd.DataFrame:
    if not CATALOGUE_PATH.exists():
        return pd.DataFrame()

    with open(CATALOGUE_PATH, "r", encoding="utf-8") as file:
        data = json.load(file)

    return pd.DataFrame(data)


def search_catalogue(catalogue_df: pd.DataFrame, query: str, selected_tags: list[str]) -> pd.DataFrame:
    if catalogue_df.empty:
        return catalogue_df

    filtered_df = catalogue_df.copy()

    if query:
        query_lower = query.lower()
        filtered_df = filtered_df[
            filtered_df["nombre"].str.lower().str.contains(query_lower, na=False)
            | filtered_df["descripcion"].str.lower().str.contains(query_lower, na=False)
        ]

    if selected_tags:
        filtered_df = filtered_df[
            filtered_df["tags"].apply(
                lambda value: any(tag in value for tag in selected_tags) if isinstance(value, list) else False
            )
        ]

    return filtered_df
