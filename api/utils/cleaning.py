from typing import Any

import pandas as pd


def dataframe_to_records(dataframe: pd.DataFrame) -> list[dict[str, Any]]:
    if dataframe.empty:
        return []
    return dataframe.to_dict(orient="records")


def limit_dataframe(dataframe: pd.DataFrame, limit: int) -> pd.DataFrame:
    if dataframe.empty:
        return dataframe
    return dataframe.head(limit).copy()
